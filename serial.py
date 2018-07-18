from vcd import *

LSB_FIRST = 0
MSB_FIRST = 1

PARITY_NONE = 0
PARITY_EVEN = 1
PARITY_ODD = 2

STOPBITS_1 = 1
STOPBITS_1_5 = 1.5
STOPBITS_2 = 2

LOGIC_INVERTED = 0
LOGIC_NON_INVERTED = 1

DATA_BITS = 8
BAUD = 9600.0
BYTEORDER = LSB_FIRST
PARITY = PARITY_NONE
STOPBITS = STOPBITS_1
LOGIC = LOGIC_INVERTED

SERIAL_TRACE_NAME = "module_top.VCC"

def gotSerialByte(data,parity):
	print "0x%02x" % data


def decodeSerial(vcd,signal, arg):
	vcd.triggerEnabled(False)
	vcd.advanceTime(((1.0/BAUD)/2.0))
	vcd.advanceTime(1.0/BAUD) #start bit

	byte = 0x00
	parity = 0
	for i in xrange(DATA_BITS):
		thisbit =  vcd.getSignal(SERIAL_TRACE_NAME)
		if thisbit:
			parity += 1
		
		if BYTEORDER == LSB_FIRST:
			if (thisbit and LOGIC_NON_INVERTED) or ( not thisbit and LOGIC_INVERTED):
				byte |= (0x01 << i)
		elif BYTEORDER == MSB_FIRST:
			if (thisbit and LOGIC_NON_INVERTED) or (not thisbit and LOGIC_INVERTED):
				byte |= ((1<<(DATA_BITS - 1)) >> i)

		vcd.advanceTime(1.0/BAUD)

	if PARITY != PARITY_NONE:
		vcd.advanceTime(1.0/BAUD) #parity bit

	vcd.advanceTime((1.0/BAUD) * STOPBITS) #stop bits

	if ((PARITY_EVEN & parity) == 1) or ((PARITY_ODD & parity) == 0):
		parity_ok = False
	else:
		parity_ok = True

	gotSerialByte(byte,parity_ok)
	vcd.triggerEnabled(True)


f = VCDFile("serial2.vcd")
print f.getSignals()

if LOGIC_NON_INVERTED:
	f.setTrigger(SERIAL_TRACE_NAME, decodeSerial,SIGNAL_TYPE_CHANGE_FALLING)
else:
	f.setTrigger(SERIAL_TRACE_NAME, decodeSerial,SIGNAL_TYPE_CHANGE_RISING)

f.updateSequence()
f.runFile()
print "done"
