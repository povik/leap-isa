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

class OpCodes(IntEnum):
    MUX = 0xe5

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

    if opcode == OpCodes.MUX:
        if op3 & 0x8000_0000:
            out = op2
        else:
            out = op1
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
