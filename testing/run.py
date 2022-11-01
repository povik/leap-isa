import sys
import random
from construct import Struct, Int32ul, StreamError
from model import exec_1inst

LEAPContext = Struct(
    "bank0" / Int32ul[0x40],
    "bank1" / Int32ul[0x40],
    "bank2" / Int32ul[0x40],
    "bank3" / Int32ul[0x40],
)

LEAPInstruction = Int32ul[4]

LEAPExecutionInfo = Struct(
    "context" / LEAPContext,
    "instruction" / LEAPInstruction,
)

f = sys.stdin.buffer
sys.stdout = open("/dev/null", "w")

good = 0
bad = 0
not_implemented = 0
bad_inst = []

while True:
	try:
		info = LEAPExecutionInfo.parse_stream(f)
	except StreamError:
		if not len(f.read(1)):
			break
		else:
			traceback.print_exc()
			sys.exit(1)

	observed = LEAPContext.parse_stream(f)

	try:
		predicted = exec_1inst(info.context, info.instruction)
	except NotImplementedError:
		not_implemented += 1
		continue

	if observed == predicted:
		good += 1
	else:
		bad_inst.append(info.instruction)
		bad += 1

if bad:
	print(f"Some badly modeled instructions:", file=sys.stderr)
	random.shuffle(bad_inst)
	for inst in bad_inst[:30]:
		print(f"\t{inst[0]:x}, {inst[1]:x}, {inst[2]:x}, {inst[3]:x}",
			  file=sys.stderr)

print(f"{good}/{bad}/{good + bad + not_implemented}",
	  file=sys.stderr)
