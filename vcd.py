
import matplotlib.pyplot as plt
import numpy as np

SIGNAL_TYPE_CHANGE_NONE = 0
SIGNAL_TYPE_CHANGE_ANY = 1
SIGNAL_TYPE_CHANGE_RISING = 2
SIGNAL_TYPE_CHANGE_FALLING = 4
SIGNAL_TYPE_CHANGE_TIME = 8
import collections


TIMESCALES = {'s':1, 'ms':1e-3,'us':1e-6, '\xc2s':1e-6, 'ns':1e-9, 'ps':1e-12,'fs':1e+15}

WHENCE_SET = 0
WHENCE_CUR = 1

class VCDFile():
	def __init__(self,file, starttime =0):
		self.file = open(file)
		self.done = 0
		self.state = 0
		self.variables = {}
		self.time_per_sample = 1.0
		self.t1 = 0
		self.t2 = 0
		self.signal =  []
		self.loader_time = 0
		self.loadFile()
		self.current_time = 0
		self.doneFile = 0
		self.sequence = self.timeSequence(self.t1,self.t2)
		self.triggers_enabled = True
		self.annotations = []

	def addAnnotation(self, signal, text):
		channelcnt = 0
		for e,v in self.variables.items():
			if v["name"]  == signal:
				self.annotations.append((self.current_time, channelcnt, text))
			channelcnt += 1

	def plot(self):
		(t,v) = self.asTrace()
		for tt,l in v.items():
			plt.plot(t,l, label=tt)
		
		for (t,o,txt) in self.annotations:
			plt.scatter(t,o+ (.45 * .95), 10, color='black')
			plt.text(t,o + (.5 * .95),txt, ha="center", va="center",size=15)

		plt.legend()
		plt.show()

	def enableTriggers(self,true_false=None):
		if true_false != None:
			self.triggers_enabled = bool(true_false)
		return self.triggers_enabled

	def secondsToTimescale(self, seconds):
		return int( float(seconds) /float(self.time_per_sample))
	
	def timescaleToSeconds(self, timescale):
		return (float(timescale) * float(self.time_per_sample))

	def getSignals(self):
		return [y['name'] for x,y in self.variables.items()]

	def getSignal(self,signal):
		for x,y in self.variables.items():
			if signal == y['name']:
				return y['state']
		raise Warning("unknown Signal %s" % signal)

	def signalToChar(self,signal):
		for x,y in self.variables.items():
			if signal == y['name']:
				return x
		raise Warning("unknown Signal %s" % signal)
	
	def _setTimeStep(self,time):
		self.loader_time  = time

	def createNewVar(self,c,name,type, bits=1):
		self.variables[c] = {'name':name, 'type':type,'state':'X','bits':bits, 'callbacks':[], 'flags':0}

	def loadFile(self):
		in_dollar_tag = 0
		dollar_tag = []
		changes = []
		
		scopestack = []
		while self.done == 0:
			l = self.file.readline().strip()
			if len(l):
				if in_dollar_tag == 0:
					if l[0] == '$':
						dollar_tag.append(l[1:])
						in_dollar_tag = 1
					
					elif l[0] == '#':
						if len(changes):
							self.signal.append((self.loader_time,changes))
						self._setTimeStep(int(l[1:]))
						changes = []
					
					elif l[1] in self.variables:
						if l[0][0] in ['b','B']: #is binary?
							state = int(l[0][1:], 2)
						elif l[0][0] in ['r','R']: #is real?
							state = float(l[0][1:])
						elif l[0][0] in ['x','X']: #undefined
							state = None
						elif l[0][0] in ['z','z']: #tristate
							state = None
						elif l[0][0] == '1': #one
							state = 1
						elif l[0][0] == '0': #zero
							state = 0
						changes.append((l[1:],state))
							
				while in_dollar_tag == 1:
					mergeargs = " ".join(dollar_tag)
					args = mergeargs.split(" ")
					if args[-1] != "$end":
						l = self.file.readline().strip()
						dollar_tag.append(l)
					else:
						in_dollar_tag = 0
						mergeargs = " ".join(dollar_tag)
						dollar_tag = []
						
						args = [x.strip() for x in mergeargs.split(" ")]
						
						if args[0] == "var":
							self.createNewVar(args[3],".".join(scopestack+[args[4]]),args[1], args[2])
						
						elif args[0] == "enddefinitions":
							self.header_done = 1
						
						elif args[0] == "timescale":
							self.setTimescale(args[1],args[2])

						elif args[0] == "scope":
							scopestack.append("%s_%s" % (args[1],args[2]))
						
						elif args[0] == "upscope":
							scopestack.pop()

			else:
				self.done = 1
		self.t2 = self.loader_time
		return
			
	def setTimescale(self, mul, scale):
		self.time_per_sample = float(mul) * float(TIMESCALES[scale])

	def setTrigger(self, signal, cb, type=SIGNAL_TYPE_CHANGE_ANY):
		c = self.signalToChar(signal)
		if c != None:
			self.variables[c]['callbacks'].append((type,cb))
		else:
			raise Warning("unknown signal")

	def timeToIndex(self, t):
		for i in xrange(len(self.signal)):
			if t <= self.signal[i][0]: #its in mt index:
				return i
		return None

	def asTrace(self):
		timelist = []
		datalist = {}
		channelcnt = 0
		for e,v in self.variables.items():
			datalist[e] = {"trace": [], "state":0,"newstate":0, "offset":channelcnt, "name":v['name']}
			channelcnt += 1
		
		for i in xrange(len(self.signal)):
			for c, dat in self.signal[i][1]:   #process the changes
				datalist[c]['newstate'] = dat

			if self.t2 > self.signal[i][0] > self.t1:
				timelist.append(self.signal[i][0]-1)
				for e,v in datalist.items():
					datalist[e]['trace'].append(( datalist[e]['state'] * .95) + datalist[e]['offset']  )
				timelist.append(self.signal[i][0])
				for e,v in datalist.items():
					datalist[e]['trace'].append((datalist[e]['newstate']  * .95 ) + datalist[e]['offset'])
			for e,v in datalist.items():
				datalist[e]['state'] = datalist[e]['newstate']
		ndl = {}
		names = []
		for v,d in datalist.items():
			ndl[d["name"]] = d["trace"]
		return (timelist,ndl)

	def timeSequence(self,t1,t2):
		for i in xrange(len(self.signal)):
			if t2 > self.signal[i][0] > t1:
				yield i

	def updateVar(self, var, val):
		if (self.variables[var]['state'] != val):
			self.variables[var]['flags']  = SIGNAL_TYPE_CHANGE_ANY
		else:
			self.variables[var]['flags']  =  SIGNAL_TYPE_CHANGE_NONE
		
		if val in ['X','x','Z','z']:
			val = 0
		if val:
			self.variables[var]['flags'] |=  SIGNAL_TYPE_CHANGE_RISING
		else:
			self.variables[var]['flags'] |=  SIGNAL_TYPE_CHANGE_FALLING
		self.variables[var]['state'] = val

	def updateSignal(self, signal, val):
		self.updateVar(signalToChar(signal),val)

	def updateSequence(self):
		self.sequence = self.timeSequence(self.current_time,self.t2)

	def setTime(self,t):
		nt = 0
		while nt < t and self.doneFile == 0:
			try:
				i = self.sequence.next()
				nt = self.signal[i][0]
				if nt < t:
					for (c,v) in self.signal[i][1]:
						self.updateVar(c, v)
			except StopIteration:
				self.doneFile = 1
		self.current_time = t
		self.updateSequence()

	def advanceTime(self,s):
		self.updateTime(self.current_time + self.secondsToTimescale(s))

	def updateTime(self, t):
		self.setTime(t)
		
		for (c,v) in self.variables.items():
			if self.triggers_enabled == True:
				for (type,cb) in v['callbacks']:
					if type & v['flags']:
						cb(self,v['name'], (t,self.getSignals()))
						self.variables[c]['flags'] = SIGNAL_TYPE_CHANGE_NONE

	def setT1(self, val):
		self.t1 = val

	def setT2(self, val):
		self.t2 = val

	def setT1s(self, val):
		self.setT1(secondsToTimescale(val))
	
	def setT2s(self, val):
		self.setT2(secondsToTimescale(val))

	def getTime(self):
		return self.timescaleToSeconds(self.current_time)

	def getSampleNumber(self):
		return self.current_time

	def nextEdge(self, signal):
		cur = self.getSignal(signal)
		while (not self.doneFile) and (self.getSignal(signal) == cur):
			i = self.sequence.next()
			try:
				for (c,v) in self.signal[i][1]:
					self.updateVar(c, v)
			except StopIteration:
				self.doneFile = 1
		self.current_time = self.signal[i][0]
		self.updateSequence()
		

	def runFile(self):
		while not self.doneFile:
			try:
				i = self.sequence.next()
				for (c,v) in self.signal[i][1]:
					self.updateVar(c, v)
				self.updateTime(self.signal[i][0])

			except StopIteration:
				self.doneFile = 1

if __name__ == '__main__':
	def thingie(vcd,signal, arg):
		print "callback!",arg

	f = VCDFile("untitled.vcd")
	print f.getSignals()
	f.setTrigger("module_top.SERIAL", thingie,SIGNAL_TYPE_CHANGE_FALLING)
	
	f.runFile()
	print "done"
