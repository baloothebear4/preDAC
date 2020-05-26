#!/usr/bin/env python
"""
# mVista PreDAC Project
#
# v0.1	   04.09.17	Baloothebear4
#
# Module : volumeBoard.py
# Purpose: Class to manage the interface to the volume board HW. The volume
#		   board provides a read time update to the actual volume level and
#		   facilitates volume changes.  Further, the board also samples
#		   the input signal and provides instantaneous samples for RMS calculation,
#		   a 128 bin FFT output at 30ms intervals, plus board status and info
#		   dumps.
#
#		   Owing to the time critical nature of the interface, a process is
#		   used to continuously poll the board (via the i2c interface). This
#		   responds to the status of the board and reads data ie volume changes or
#          FFT dumps accordingly. Ad-hoc demands to update the volume are also
#		   (like mute) are sent.
#
"""

'''
Psuedo Code:

## How is the data between the i2c interface and the board class transferred
## pipe transfer strings hence use Newline characters to differentiate, and
## pickle to pack up the data structure and unpack it

i2c interface
	loop
		check pipe for info demand
			set vol: send volume demand
			config dump: build dump and place in pipe
		check board status
			alive      : read samples
			vol change : read volume
			fft ready  : read fft

VolumeBoardinterface class:
 ## all functions perform a pipe read and update the class objects accordingly
 ## question: are callbacks used to trigger the calls?  Or is the class simply
 ## called periodically?  How long does it take to dump all the data ie c.140 bytes
 ## NB: there is only ever one set of data, as new comes in the old is lost
 	objects:
		FFT[ number of samples ]
		SampleFreq
		Number of samples
		Sample size
		volume
		RMSlevel{ L, R }
		Peaklevel{ L, R }
Public:
	read FFT

	read volume

	read RMS

	write volume
Private:
	readi2cinterface
		called by all read requests and reads the pipe and fills the objects
	writei2cinterface
		called to set volume
		readi2cinterface follows
	readConfig
		used during initialisation to capture base config


Eg:

vb = VolumeBoard()

while(1)
	vb.readFFT()
	vb.readRMS()
	vb.readVolume()

	which is called is dependent on the function at the time, UI driven

'''


from multiprocessing import Process, Pipe
import serial
from events import Events
import time
import numpy as np
import math

try:
   import cPickle as pickle   # try to use cPickle as its much faster
except:
   import pickle

class RMS:
    def __init__(self):
        self.RMSsamples    	= 2		# number of samples to use in RMS calculation, need to check read Frequency
        self.Peaksamples    = 16     # number of samples to use in Peak calculation, assume this is greater than for RMS
        self.Vrms 		= { 'Left': 0.0, 'Right': 0.0 } 	# averages across captured RMSsamples
        self.Vpk  		= { 'Left': 0.0, 'Right': 0.0 }  	# peak level in RMS sample set
        self.ChSample 	= { 'Left': [],  'Right': [ ] }  #  Buffer of Left & Right channel samples
        self.rms     	= { 'Left': [],  'Right': [ ] }  #  Buffer of Left & Right channel rms values
        self.Sumsqs		= { 'Left': 0.0, 'Right': 0.0 } 	# hold the sum of squares to avoid resumming the whole array each time
        # print "RMS.__init__> "

    def LeftAdd(self, value):
        self.Add(value, 'Left')

    def RightAdd(self, value):
        self.Add(value, 'Right')

    def Add(self, value, side):
        self.ChSample[side].append( value )
        size = len( self.ChSample[side] )

        if size > self.Peaksamples:
            del self.ChSample[side][0]
            del self.rms[side][0]

        self.Sumsqs[side] = 0.0000001
        if size > self.RMSsamples:
            for i in range( size-self.RMSsamples, size-1 ):
                self.Sumsqs[side]  += (self.ChSample[side][i])**2
        else:
            for i in range( size-1 ):
                self.Sumsqs[side]  += (self.ChSample[side][i])**2
        scale = 0.4
        self.Vrms[side]		= math.log( 1+((self.Sumsqs[side]/self.RMSsamples)**0.5)/scale , 2 ) # RMS calculation
        self.rms[side].append( self.Vrms[side] )
        self.Vpk[side]		= max(self.rms[side])

        # print("RMS Add> rms %f to side %s =%d: sumsqs=%f" % (self.Vrms[side], side, value, (self.Sumsqs[side]/self.RMSsamples)**0.5) )

    def __repr__(self):
        print "RMS object: ", self.Vrms, self.Vpk, self.ChSample

    def __str__(self):  # may need to be a __repr__
        text  = "RMS Object:\n"
        text += " %20s : %f\n" % ('Left Vrms', self.Vrms['Left'])
        text += " %20s : %f\n" % ('Right Vrms', self.Vrms['Right'])
        text += " %20s : %s\n" % ('Vpk', self.Vpk)
        text += " %20s : %s\n" % ('ChSample', self.ChSample)
        text += " %20s : %s\n" % ('Sumsqs', self.Sumsqs)
        return text

class VolumeBoardData(RMS):
    def __init__(self):
        RMS.__init__(self)
        self.clear()

    def clear(self):
        # Board data is held in a dictionary so it can be pickled and sent through a pipe
        self.board = {
            'Vrms'			: { 'Left': 0.0, 'Right': 0.0 }, 	# averages across captured RMSsamples
            'Vpk'			: { 'Left': 0.0, 'Right': 0.0 },  	# peak level in RMS sample set
            'sampleFreq'	: 0.0,							# sample Frequency of the volume board
            'boardSamples'	: 0,							# number of samples used on the volume board FFT
            'freqBins'		: 0,							# number of frequecny bins available
            'Fbin'			: 0.0,  						# 1/samplefreq/2/bins  ie half Nyquist Frequency/num bins = bandwidth per bin
            'acqTime'       : 0.0,
            'txTime'        : 0.0,
            'rxTime'        : 0.0,
            'procTime'      : 0.0,
            'rmsTime'       : 0.0,
            'txBlock'       : 0,                            # number of blocks to a sample dump is sent in
            'volume'		: 0,							# Board volume in dB NB 0 = -63dB
            'bins'          : []  }                         # output of the FFT
        self.mean    =        0.0                           # mean level of the input samples - used to remove DC offset
        self.samples =        [] 					        # array of received samples
        # print "VolumeBoardData clear> ", self.board

    def update(self):
        self.board['Vrms']['Left'] 	= self.Vrms['Left']
        self.board['Vrms']['Right'] = self.Vrms['Right']
        self.board['Vpk']['Left'] 	= self.Vpk['Left']
        self.board['Vpk']['Right'] 	= self.Vpk['Right']

    def __str__(self):  # may need to be a __repr__
        text  = "Volume Board data set:\n"
        text += " %20s : %s\n" % ('Vrms', self.board['Vrms'])
        text += " %20s : %s\n" % ('Vpk', self.board['Vpk'])
        text += " %20s : %d\n" % ('Sample Freq',self.board['sampleFreq'])
        text += " %20s : %d\n" % ("Num Board samples", self.board['boardSamples'])
        text += " %20s : %f\n" % ("Fbin", self.board['Fbin'])
        text += " %20s : %d\n" % ("Volume", self.board['volume'])
        text += " %20s : %d\n" % ("acqTime", self.board['acqTime'])
        text += " %20s : %d\n" % ("txTime", self.board['txTime'])
        text += " %20s : %d\n" % ("rxTime", self.board['rxTime'])
        text += " %20s : %d\n" % ("procTime", self.board['procTime'])
        text += " %20s : %d\n" % ("rmsTime", self.board['rmsTime'])
        text += " %20s : %d\n" % ("txBlock size", self.board['txBlock'])
        text += " %20s : %d\n" % ("Num bins", self.board['freqBins'])
        text += " %20s : %s\n" % ("Bins", self.board['bins'])
        text += " %20s : %s\n" % ("Samples", self.samples)
        text += " %20s : %2.1f\n" % ("Mean", self.mean)
        return text


class VolumeBoard(VolumeBoardData):

    def __init__(self, events):
        VolumeBoardData.__init__(self)
        self.events                 = events
        self.app_pipe, self.interface_pipe= Pipe()    # need and in pipe too
        self.interface				= processInterface(self.interface_pipe)
        self.p 						= Process(target=self.interface.manage)
        self.block      			= '' 		# used to hold the string read from the Pipe
        self.p.start()
        while not self.app_pipe.poll(0):            #wait until the pipe has some data
            time.sleep(0.001)
        #     print "waiting for pipe"
        # print "VolumeBoard>init"

    def readFreqBins(self):
        self.readInterface()
        # self.readTime()
        return self.board['bins']

    def readBinBandwidth(self):
        self.readInterface()
        return self.board['Fbin']/2  # With the zero padding the bin bandwidth is halved which serves as interpolation

    def readTime(self):
        self.readInterface()
        print "VolumeBoard.readTime> Timing analysis: "
        print( "acquire in %3.4f\ntransmit in %3.4f\nReceive in %3.4f\nprocess in %3.4f\nrms Time %f\n readTime deficit" % (self.board['acqTime'], self.board['txTime'], self.board['rxTime'], self.board['procTime'], self.board['rmsTime']) )
        return self.board['acqTime']-(self.board['txTime']+self.board['procTime'])

    def readNyquist(self):
        self.readInterface()
        return self.board['sampleFreq']/2.0

    def readbinCount(self):
        self.readInterface()
        return self.board['boardSamples']      # Padding ensures that there are as many bins as samples

    def readVolume(self):
        vol = self.board['volume']
        self.readInterface()
        if vol != self.board['volume']:
            self.events.VolTurn('startVol')
            # print "VolumeBoard> trigger VolTurn"
        if self.board['volume'] == 0:
            self.events.VolTurn('mute')
        else:
            self.events.VolTurn('unmute')

        return self.board['volume']

    def writeVolume(self, vol):
        self.app_pipe.send(vol)
        # if self.readVolume() != vol:
        # 	print("writeVolume> vol write failed demand %d, latest %d" % (vol, self.board['volume'] ) )
        # return self.board['volume']

    def readVrms(self):
        self.readInterface()
        return self.board['Vrms']

    def readVpeak(self):
        self.readInterface()
        return self.board['Vpk']

    def readInterface(self):
        s = 0

        while self.app_pipe.poll(0):
        	s += 1
        	self.block = pickle.loads(self.app_pipe.recv())
        	#print "readInterface> received block [%s]" % self.block
        	self.board = self.block
        	#print "readInterface> unpickle pipe into data block...", self.board

        if  s > 20:
        	print "readInterface> time read times = ", s

    def __repr__(self):
        print "VolumeBoard> data set= "




'''

This version builds a fast response version on the i2C to pull off samples as fast as possible when available

//Protocol:  cmd ID (8 bit int)
//
//  don't use block writes use a pipe method based on 1 cmd (written by Pi, 1 data byte by Volume Board):
//
//  * cmd 0 - return : status value: 0=alive, 1=samples ready, 2=get vol change, 3=error
//  * cmd 1 - return : num samples available to send 0->128
//  * cmd 2 - return : reset counters
//  * cmd 3 - return : data dump: Sample Frequency=%d  Sample size=%d  Vref=%d   Acquire Time=%d   Process time=%d
//  * cmd 4 - return : send vol level (NB: 63 = mute - in -dB ie 0= full, 63= mute)
//  * cmd 5 + set vol level data : return vol level
//  * cmd 6 - return : Left channel sample
//  * cmd 7 - return : Right channel sample
//  * cmd 8 - return : num dump bytes left to send
//  * cmd 9 - return : send next sample

'''


class processInterface(VolumeBoardData):

    def __init__(self, pipe):
        self.dumpSize 		= 11      					# size of the config dump in bytes
        self.ser            = serial.Serial("/dev/serial0", 1000000, timeout=0.1)
        self.ser.flushInput()
        VolumeBoardData.__init__(self)
        self.interface 		= pipe
        self.block    		= '' 						# used to hold the string read from the Pipe
        self.DCoffset       = 154.0
        self.sampleMax      = 2**7
        self.chTime         = time.time()
        self.Lrms           =0

        self.readVolumeBoard(3) 						# get a dump of the config parameters
        self.readVolumeBoard(4)                         # read the volume
        """ Create a window to improve the frequency definition.
            The Kaiser function beta value affects how peaky the display is : 4-6 is hanning.
            Trades off peakiness vs spill over into adjacent bins
        """
        self.window         = np.kaiser(self.board['boardSamples']*2, 5)

        print "processInterface __init__> ", self


    def writeNumber(self, data):
        retrys=0
        while(retrys<25):
            try:
                raw  = bytearray([data & 0xFF])
                self.ser.write(raw)
                # print "writeNumber", data
                return

            except IOError:
                retrys += 1
                #print "readNumber> retry ", retrys
        print "writeNumber> exceeded 25 retrys interface failure"		#print ">>writeNumber: ",value
        return -1

    def readNumber(self, length=1):
        retrys = 0
        while(retrys<5):
            try:
                raw =self.ser.read(length)
                intArray = []
                for i in raw:
                    intArray.append(ord(i))
                # print "readNumber>", intArray
                if len(raw) == length:
                    if length==1:
                        return intArray[0]
                    else:
                        return intArray
                # else:
                #     print "readNumber > failed to read required bytes ", length
                #     self.ser.flushInput()
                #     return self.ser.read(length)

            except IOError:
                retrys += 1
                #print "readNumber> retry ", retrys
        print "readNumber> exceeded 5 retrys interface failure"


    def manage(self):

        while(1):
            # read the pipe for commands & Process
            if self.interface.poll(0):
                self.block = self.interface.recv()
                #print "manage> received block [%s] -- this should be the volume demand - check its 1 byte" % self.block
                self.writeNumber( 5 )
                self.writeNumber( self.block )
                self.readVolumeBoard(5)
                print("manage> Interface send: Volume set to -%ddB sent" % int(self.block))

            # poll the board and respond accordingly, filling up the pipe with data as its received, calculate the RMS locally
            status = self.readVolumeBoard(0)
            # print "manage>received: Status response ", status
            if status == 0:
                # print "manage> idle"
                # print "Read samples and calculate RMS levels"
                self.readVolumeBoard(6)
                self.readVolumeBoard(7)
                self.readVolumeBoard(3)

            elif status == 1:
                # print "manage> Samples ready"
                self.readVolumeBoard(9)

            elif status == 2:
                # print "manage> volume change"
                self.readVolumeBoard(4)

            elif status == 3:
                # print "manage> Volume change and Samples ready"
                self.readVolumeBoard(4)
                #self.readVolumeBoard(9)
            else:
                print "manage> unknown board status ", status
                self.ser.flushInput()

                # pickle the board data and stuff into the pipe
                # print "manage> pickle into pipe ", self.board
            self.interface.send(pickle.dumps(self.board))

            time.sleep(0.003)  # check at least every 1ms

    def readVolumeBoard(self, var):
        status = 0
        startTime = time.time()

    	# print "readVolumeBoard>received: Status response ", var
        if var == 0:  # Status?
        	self.writeNumber(0)
        	status = self.readNumber()
        	#print "readVolumeBoard>received: Status response ", status

        elif var == 1: # Bins Available?
        	self.writeNumber(1)
        	samplesAvailable = self.readNumber()
        	#print( "readVolumeBoard>received: bins available %d. " % (samplesAvailable))

        elif var == 8: # Dump bytes Available?
        	self.writeNumber(8)
        	dumpAvailable=self.readNumber()
        	#print( "readVolumeBoard>received: dump bytes available %d. " % (dumpAvailable))

        elif var == 6: # Left Sample value
            self.writeNumber(6)
            self.LeftAdd( (self.readNumber()-self.DCoffset)/self.sampleMax )
            self.update()
            self.Lrms += 1
            if time.time()-self.chTime>1.0:
                self.board['rmsTime'] = self.Lrms
                self.chTime = time.time()
                self.Lrms = 0
        	#print( "readVolumeBoard>received: Left channel value %d. " % (self.LchV))

        elif var == 7: # Ricght Sample value
        	self.writeNumber(7)
        	self.RightAdd( (self.readNumber()-self.DCoffset)/self.sampleMax )
        	self.update()
        	#print( "readVolumeBoard>received: Right channel value %d. " % (self.RchV))

        elif var == 4:
        	self.writeNumber(4)
        	self.board['volume'] = self.readNumber()
        	#print "readVolumeBoard>received: volume set to -dB ", self.board['volume']

        elif var == 5:  # set volume command where the control byte is already written out
        	self.board['volume'] = self.readNumber()
        	#print "readVolumeBoard>received: volume set to -dB ", self.board['volume']

        elif var == 2:
        	self.writeNumber(2)
        	print "readVolumeBoard> Reset counters\n "

        elif var == 9:   # Sample dump
            self.writeNumber(9)
            self.samples += self.readNumber(self.board['txBlock'])  # Need offset the value as the ADC is biased to half the input,
            # print "readVolumeBoard> samples received=", len(self.samples), self.board['txBlock']
            if len(self.samples) == self.board['boardSamples']:
                t = time.time()
                self.board['rxTime'] = 1000.0*(t-startTime)
                """ FFT Calculation"""
                self.calcFFT()
                self.board['procTime'] = 1000.0*(time.time()-t)
                self.samples = []

        elif var == 3:
            # print "readVolumeBoard>Read Info dump values "
            self.writeNumber(3)
            dump = self.readNumber(self.dumpSize)
            elapsedTime = time.time()-startTime
            # print dump

            self.board['sampleFreq']	= makeWord(dump[0], dump[1])
            self.board['boardSamples'] 	= makeWord(dump[2], dump[3])
            self.board['freqBins'] 	    = makeWord(dump[2], dump[3])/2
            self.board['Fbin']			= (self.board['sampleFreq']/self.board['boardSamples']) 			# samplefreq/2 / numsamples/2 ie half Nyquist Frequency
            self.board['Vref']			= makeWord(dump[4], dump[5])
            self.board['acqTime']		= makeWord(dump[6], dump[7])
            self.board['txTime']		= makeWord(dump[8], dump[9])
            self.board['txBlock']		= dump[10]
            #print dump
            # print( "readVolumeBoard>Info Dump in %fms:\nSample Frequency=%d\nSample size=%d\nVref=%d\nAcquire Time=%d\nTransmit time=%d\n" \
            # % ( elapsedTime*1000, makeWord(dump[0], dump[1]),  makeWord(dump[2], dump[3]),  makeWord(dump[4], dump[5]), makeWord(dump[6], dump[7]), makeWord(dump[8], dump[9]) ))


        else:
        	pass

        return status

    def calcFFT(self):
        # mean   = np.mean(self.samples)
        # print "calcFFT> DCoffset", mean
        norm   = (np.array(self.samples) - self.DCoffset) / (self.sampleMax)
        _npads = self.board['boardSamples']*2 - len(norm)
        norm = np.pad( norm, pad_width=_npads, mode='constant', constant_values=0)[_npads:]

        f = np.fft.rfft(norm * self.window)
        self.board['bins'] =  np.abs(f)**2 # 20*np.log(np.abs(f))  # need to chuck away bin[0] and offset as its log
        # peak = np.amax(self.board['bins'])
        # binf = np.argmax(self.board['bins'])*75.0
        # rms = np.sqrt(np.mean(norm**2))
        # print( "samples received in %4.3fms:  size=%d  mean = %2.1f  peak = %2.1f  at F = %2.1f" % (self.board['txTime']*1000, len(self.samples), self.mean, peak, binf ) )
        # print "readVolumeBoard> samples\n ", self.samples, "\nnormalised ", norm
        # fq = self.board['Fbin']
        # for k in self.board['bins']:
        #     print " f=", fq, "bin=", k
        #     fq += self.board['Fbin']
        # raise Exception('quit')

#end of processi2c Class

def makeWord(a,b):
	c = a
	c <<= 8
	c += b
	return c


#### Test Code
if __name__ == '__main__':
    try:
        events         = Events(( 'System', 'CtrlPress', 'CtrlTurn', 'VolPress', 'VolTurn', 'VolPress', 'Pause', 'Start', 'Stop'))
        vb = VolumeBoard(events)

        print "Init complete : Accessing volume board"

        print "main> read BinBandwidth", vb.readBinBandwidth()

        print "main> read TxTime", vb.readTime()

        print "main> read readNyquist", vb.readNyquist()

        print "main> read writeVolume (25 sent)", vb.writeVolume( 25)

        while 1:
            print "main> read Vrms ", vb.readVrms()
            print "main> read Vpeak", vb.readVpeak()
            print "main> read readVolume", vb.readVolume()
            print "main> read FreqBins", vb.readFreqBins()
            vb.readFreqBins()
            print "main> read Time \n", vb.readTime()
            time.sleep(1)

    except:
        raise
