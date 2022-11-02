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

    OPCODE2 = 17, 17
    OUTBANK = 15, 14
    OP3BANK = 13, 12
    OP2BANK = 11, 10
    OP1BANK = 9,   8
    OPCODE1 = 7,   0

class Opcode(IntEnum):
    PDM1 = 0x95 # one-in-4 decimation
    PDM2 = 0x96
    PDM3 = 0x97 # one-in-3 decimation
    PDM4 = 0x98
    PDM5 = 0x99 # one-in-5 decimation
    PDM6 = 0x9a

    MUX = 0xe5

def fmt_s32(val):
    return val & 0xffff_ffff

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

    if opcode == Opcode.MUX:
        if op3 & 0x8000_0000:
            out = op2
        else:
            out = op1
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
