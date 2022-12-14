import sys
from enum import IntEnum

class BitFieldsValue:
    def __init__(self, val):
        self._val = val
        l = []
        self._fieldnames = l
        self._fieldmask = 0
        for cls in self.__class__.mro():
            l += [k for k in cls.__dict__.keys() \
                  if not k.startswith("_")]
        for field in l:
            top, bot = getattr(self.__class__, field)
            self._fieldmask |= (-1 << (top + 1)) ^ (-1 << bot)

    def __getattribute__(self, attrname):
        if attrname.startswith("_"):
            return object.__getattribute__(self, attrname)
        top, bot = getattr(self.__class__, attrname)
        mask = (1 << (top - bot + 1)) - 1
        return (self._val >> bot) & mask

    def __str__(self):
        undecoded = self._val & ~self._fieldmask
        return ", ".join([f"{n}={getattr(self, n):x}" for n \
                          in self._fieldnames]) + f" (undecoded {undecoded:x})"

class GeneralInstr(BitFieldsValue):
    OUTADDR = 31, 19

    OPCODE2 = 18, 17
    OUTBANK = 15, 14
    OP3BANK = 13, 12
    OP2BANK = 11, 10
    OP1BANK = 9,   8
    OPCODE1 = 7,   0

class Opcode(IntEnum):
    FRACMULT = 0x00

    ADD  = 0x80
    ADD_DIV2 = 0x81
    SUB  = 0x82
    SUB_DIV2 = 0x83
    ADD_UNS  = 0x84
    ABS  = 0x85
    MAX  = 0x86
    MIN  = 0x87
    MUX  = 0x88
    AND  = 0x89
    OR   = 0x8a
    XOR  = 0x8b
    CLR  = 0x8c
    ZERO = 0x8d
    ADD2 = 0x8e
    ADD3 = 0x8f
    ZERO2 = 0x90
    ZERO3 = 0x91
    ZERO4 = 0x92
    CLAMP = 0x93
    ROT  = 0x94
    PDM1 = 0x95 # one-in-4 decimation
    PDM2 = 0x96
    PDM3 = 0x97 # one-in-3 decimation
    PDM4 = 0x98
    PDM5 = 0x99 # one-in-5 decimation
    PDM6 = 0x9a
    CMP  = 0x9b
    CMP2 = 0x9c
    EQ   = 0x9d
    ADD4 = 0x9e
    SUB2 = 0x9f


    # ----
    # Opcodes 0xa0...0xbf have side effects and as such are not
    # modeled in Python, instead a textual description is given:

    '''
    Read value from I/O port (w/ signaling)

    The port is selected by index in top 8 bits of operand #3. Once the read
    is done, the port is signaled empty and ready to accept another value.

    In the latter (TAKEC) version of the opcode the operation is conditioned
    on top bit of operand #2 being set.
    '''
    TAKE   = 0xa0
    TAKEC  = 0xa1

    '''
    Read value from I/O port (w/o signaling)

    The port is selected by index in top 8 bits of operand #3. The read does
    not affect the port's adjacent full/empty signaling.
    '''
    PEEK   = 0xa2

    '''
    Write value to I/O port (w/ signaling)

    The operand #1 will be written to I/O port selected by index in top 8 bits
    of operand #3. Once the write is done, the port is signaled full and
    ready to pass on its value to a peripheral or another LEAP routine.

    In the latter (PUTC) version of the opcode the operation is conditioned
    on top bit of operand #2 being set.
    '''
    PUT    = 0xa4
    PUTC   = 0xa5

    '''
    Write value to I/O port (w/o signaling)

    The operand #1 will be written to I/O port selected by index in top 8 bits
    of operand #3. The write does not affect the port's adjacent full/empty
    signaling.
    '''
    UPDATE = 0xa6

    # These were the side effect opcodes. Pardon the interruption and enjoy
    # more of the pure opcodes that follow below.
    # ---

    FCMP    = 0xe0
    FCMP2   = 0xe1
    FMUX    = 0xe5
    F32_FMT = 0xed

    # sample bad input: fff287df + 45108c24
    FADD      = 0x1c0
    FADD_ABS  = 0x1c1
    FADD_DIV2 = 0x1c2
    FSUB      = 0x1c3
    FSUB_ABS  = 0x1c4
    FSUB_DIV2 = 0x1c5

    # TODO: join into opcodes with flags
    FMULT        = 0x1c6
    FMULTACC     = 0x1c7
    FMULT_NEG    = 0x1d6
    FMULTACC_NEG = 0x1d7
    FMULTSUB     = 0x1d8

    MULT31 = 0x2e0 # <- appears equivalent to FRACMULT
    # ...
    MULT0  = 0x2ff

class Float:
    def __init__(self, exp, prec):
        self.exp, self.prec = exp, prec

    @classmethod
    def decode(self, val):
        sign = -1 if (val >> 31) else 1
        exp = ((val >> 23) & 0xff) - 127
        prec = (1 << 23) | (val & ~(-1 << 23))
        if exp == -127:
            prec &= ~1 << 23
            exp = -126
        return Float(
            exp, prec * sign
        )

    @classmethod
    def inf(self, sign):
        return Float(
            127, ~(-1 << 24) * sign
        )

    def __mul__(self, other):
        #if self.is_inf or other.is_inf:
        #    return Float.inf(self.sign * other.sign)
        return Float(
            self.exp + other.exp - 23,
            self.prec * other.prec
        )

    @property
    def is_inf(self):
        return (self.exp >= 127) \
            or (self.exp == 127 and self.prec * self.sign == ~(-1 << 24))

    @property
    def sign(self):
        return +1 if self.prec >= 0 else -1

    def with_exp(self, texp):
        if texp > self.exp:
            return Float(texp, self.prec >> (texp - self.exp))
        else:
            return Float(texp, self.prec << (self.exp - texp))

    @classmethod
    def with_common_exp(self, a, b):
        common = min(a.exp, b.exp)
        return a.with_exp(common), b.with_exp(common)

    def __sub__(self, other):
        a, b = Float.with_common_exp(self, other)
        return Float(a.exp, a.prec - b.prec)

    def __add__(self, other):
        a, b = Float.with_common_exp(self, other)
        return Float(a.exp, a.prec + b.prec)

    def __gt__(self, other):
        a, b = Float.with_common_exp(self, other)
        return a.prec > b.prec

    def normalize(self):
        shiftdown = ((self.prec >> 24) ^ (self.prec >> 25)).bit_length()
        self.prec = self.prec + (1 << shiftdown >> 1) >> shiftdown
        self.exp += shiftdown

        if self.exp > 127:
            self.exp = 127
            self.prec = self.sign * ~(-1 << 24)

        while self.prec * self.sign >> 23 == 0 \
                and self.exp > -126:
            self.exp -= 1
            self.prec <<= 1

        while self.exp < -126:
            self.exp += 1
            self.prec >>= 1

        if self.prec * self.sign < (1 << 23):
            assert self.exp == -126
            self.prec = 0

    def normalized(self):
        ret = Float(self.exp, self.prec)
        ret.normalize()
        return ret

    def abs(self):
        return Float(self.exp, self.prec * self.sign)

    def encode(self):
        abs_prec = self.prec * self.sign
        exp = self.exp
        if abs_prec == 0:
            exp = -127
        signbit = self.sign == -1
        return signbit << 31 | exp + 127 << 23 | (abs_prec & ~(-1 << 23))

def s32(val):
    return val - (0x1_0000_0000 if (val & 0x8000_0000) else 0)

def fmt_s32(val):
    return val & 0xffff_ffff

def s32_clamp(val):
    return min(max(val, -0x8000_0000), 0x7fff_ffff)

def exec_1inst(ctx, inst):
    i0, i1, i2, i3 = inst
    banks = [ctx.bank0, ctx.bank1, ctx.bank2, ctx.bank3]

    i0_fields = GeneralInstr(i0)

    print(i0_fields)

    # fetch operands
    b1 = ctx.bank1[i1] if i1 < len(ctx.bank1) else 0
    b2 = ctx.bank2[i2] if i2 < len(ctx.bank2) else 0
    b3 = ctx.bank3[i3] if i3 < len(ctx.bank3) else 0
    bank_ops = [0, b1, b2, b3]
    op1 = bank_ops[i0_fields.OP1BANK]
    op2 = bank_ops[i0_fields.OP2BANK]
    op3 = bank_ops[i0_fields.OP3BANK]

    # get opcode
    opcode = i0_fields.OPCODE2 << 8 | i0_fields.OPCODE1
    out = None

    if opcode == Opcode.FRACMULT:
        out = fmt_s32(s32(op2) * s32(op3) >> 31)
    if opcode == Opcode.ADD:
        out = fmt_s32(s32_clamp(s32(op2) + s32(op1)))
    elif opcode == Opcode.ADD_DIV2:
        inm = (s32(op2) + s32(op1)) // 2
        out = fmt_s32(inm)
    elif opcode == Opcode.SUB:
        out = fmt_s32(s32_clamp(s32(op2) - s32(op1)))
    elif opcode == Opcode.SUB_DIV2:
        out = fmt_s32((s32(op2) - s32(op1)) // 2)
    elif opcode == Opcode.ADD_UNS:
        out = (op1 + op2) & ~(-1 << 32)
    elif opcode == Opcode.ABS:
        inm = s32(op1)
        if inm < 0:
            inm = min(-inm, 0x7fff_ffff)
        out = fmt_s32(inm)
    elif opcode == Opcode.MAX:
        out = fmt_s32(max(s32(op1), s32(op2)))
    elif opcode == Opcode.MIN:
        out = fmt_s32(min(s32(op1), s32(op2)))
    elif opcode == Opcode.AND:
        out = op1 & op2
    elif opcode == Opcode.OR:
        out = op1 | op2
    elif opcode == Opcode.XOR:
        out = op1 ^ op2
    elif opcode == Opcode.CLR:
        out = ~op1 & op2
    elif opcode in [Opcode.ZERO, Opcode.ZERO2, Opcode.ZERO3, Opcode.ZERO4]:
        out = 0
    elif opcode in [Opcode.ADD2, Opcode.ADD3, Opcode.ADD4]:
        out = (op1 + op2) & 0x7fff_ffff
    elif opcode == Opcode.MUX:
        if op3 & 0x8000_0000:
            out = op2
        else:
            out = op1
    elif opcode == Opcode.CLAMP:
        points = [s32(op1), s32(op2), s32(op3)]
        points.sort()
        out = fmt_s32(points[1])
    elif opcode == Opcode.ROT:
        out = ~(-1 << 32) & (op1 << 1 | op1 >> 31)
    elif opcode >= Opcode.PDM1 and opcode <= Opcode.PDM6:
        FILTER_COEFFS = [
            [64, 256, 640, 1280, 1984, 2560, 2816, 2560, 1984, 1280, 640, 256, 64],
            [16, 80, 240, 560, 1040, 1616, 2160, 2480, 2480, 2160, 1616, 1040, 560, 240,
             80, 16],
            [256, 1024, 2560, 4096, 4864, 4096, 2560, 1024, 256],
            [128, 640, 1920, 3840, 5760, 6528, 5760, 3840, 1920, 640, 128],
            [32, 128, 320, 640, 1120, 1664, 2176, 2560, 2720, 2560, 2176, 1664, 1120, 640,
             320, 128, 32],
            [8, 40, 120, 280, 560, 968, 1480, 2040, 2560, 2920, 3048, 2920, 2560, 2040,
             1480, 968, 560, 280, 120, 40, 8]
        ]
        kind = opcode - Opcode.PDM1
        coeffs = FILTER_COEFFS[kind]
        ratio = [ 4, 4, 3, 3, 5, 5 ][kind]
        op1_shiftbits = [ 2, 2, 3, 3, 2, 2][kind]
        shift = (op1 << op1_shiftbits >> 32) * ratio
        out = fmt_s32(sum([
            coeff * (1 if ((op2 << shift << i >> 31) & 1) else -1)
            for i, coeff in enumerate(coeffs)
        ]) << 16)
    elif opcode == Opcode.CMP:
        out = (s32(op1) > s32(op2)) << 31
    elif opcode == Opcode.CMP2:
        out = (s32(op1) >= s32(op2)) << 31
    elif opcode == Opcode.EQ:
        out = (op1 == op2) << 31
    elif opcode == Opcode.SUB2:
        out = (-op1 + op2) & 0x7fff_ffff
    elif opcode in [Opcode.FCMP, Opcode.FCMP2]:
        if Float.decode(op2) > Float.decode(op1):
            res = Float(23, 1)
        else:
            res = Float(23, -1)
        out = res.normalized().encode()
    elif opcode == Opcode.FMUX:
        if op3 & 0x8000_0000:
            out = Float.decode(op2).normalized().encode()
        else:
            out = Float.decode(op1).normalized().encode()
    elif opcode == Opcode.F32_FMT:
        exp = (s32(op2) >> 24) - 8
        sign = -1 if op3 >> 31 else 1
        prec = s32(op3) * sign
        # crop extra bits, normalize() might erroneously round them up
        shiftdown = max(prec.bit_length() - 24, 0)
        prec >>= shiftdown
        exp += shiftdown
        out = Float(exp, prec * sign).normalized().encode()
    elif opcode == Opcode.FADD:
        out = (Float.decode(op1) + Float.decode(op2)).normalized().encode()
    elif opcode == Opcode.FADD_ABS:
        out = (Float.decode(op1) + Float.decode(op2)).abs().normalized().encode()
    elif opcode == Opcode.FADD_DIV2:
        out = ((Float.decode(op1) + Float.decode(op2)) * Float(22, 1)).normalized().encode()
    elif opcode == Opcode.FSUB:
        out = (Float.decode(op2) - Float.decode(op1)).normalized().encode()
    elif opcode == Opcode.FSUB_ABS:
        out = (Float.decode(op2) - Float.decode(op1)).abs().normalized().encode()
    elif opcode == Opcode.FSUB_DIV2:
        out = ((Float.decode(op2) - Float.decode(op1)) * Float(22, 1)).normalized().encode()
    elif opcode in [Opcode.FMULT, Opcode.FMULT_NEG]:
        res = Float.decode(op2) * Float.decode(op3)
        if opcode == Opcode.FMULT_NEG:
            res *= Float(23, -1)
        out = res.normalized().encode()
    elif opcode in [Opcode.FMULTACC, Opcode.FMULTACC_NEG]:
        res = Float.decode(op2) * Float.decode(op3) + Float.decode(op1)
        if opcode == Opcode.FMULTACC_NEG:
            res *= Float(23, -1)
        out = res.normalized().encode()
    elif opcode == Opcode.FMULTSUB:
        out = (Float.decode(op1) - \
                Float.decode(op2) * Float.decode(op3)).normalized().encode()
    elif opcode >= Opcode.MULT31 and opcode <= Opcode.MULT0:
        shift = Opcode.MULT0 - opcode
        out = fmt_s32(s32(op2) * s32(op3) >> shift)
    else:
        raise NotImplementedError()

    if out is not None:
        if i0_fields.OUTBANK == 1:
            ctx.bank1[i0_fields.OUTADDR] = out
    
        if i0_fields.OUTBANK == 2:
            ctx.bank2[i0_fields.OUTADDR] = out
    
        if i0_fields.OUTBANK == 3:
            ctx.bank3[i0_fields.OUTADDR] = out

    return ctx
