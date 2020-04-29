#!/usr/bin/env python
"""
 preDAC preamplifier project

 Process Audio class
    - provides a full alsaaudio interface
    - maniuplates audio packages
    - does Digital signal processing
    - uses alsaaudio package to control ADC and DAC

 baloothebear4
 v1 April 2020

"""

import alsaaudio, struct, time, math
import numpy as np

# constants
CHANNELS        = 2
INFORMAT        = alsaaudio.PCM_FORMAT_S16_LE
RATE            = 44100/2
FRAMESIZE       = 1024
duration        = 10
maxValue        = float(2**16)
bars            = 20
offset          = 1
scale           = 0.3

WINDOW          = 15 # 4 = Hanning
FIRSTCENTREFREQ = 31.25        # Hz
OCTAVE          = 3
NUMPADS         = 0
BINBANDWIDTH    = RATE/(FRAMESIZE + NUMPADS) #ie 43.5 Hz for 44.1kHz/1024
DCOFFSETSAMPLES = 200





class AudioData():
    def __init__(self):
        self.audio = {  'SpectrumL'   : [],
                        'SpectrumR'   : [],
                        'VU_L'        : 0.0,
                        'VU_R'        : 0.0,
                        'Peak_L'      : 0.0,
                        'Peak_R'      : 0.0 }

    # def filter(self,signal, fc):
    #     return  3.0*signal - (10.0 + 5*39/fc)
    def filter(self, signal, fc):
        return signal

    def printPower(self, power, fCentre):
        # apply a frequency dependent filter
        print "%6.1f @f=%-5d %s" % (power, fCentre , "*"*int(self.filter(power, fCentre)))

    def seeData(self, data, title):
        line = "[%d] %s\n" % (len(data), title)
        for i in range(len(data)):
            line += "%6d "%data[i]
            if i % 16 == 15:
                print line
                line = ""

    def _print(self):
        print "Left Spectrum  >%s" % self.audio['SpectrumL']
        print "Right Spectrum >%s" % self.audio['SpectrumR']
        print "Left VU        >%f" % self.audio['VU_L']
        print "Right VU       >%f" % self.audio['VU_R']
        print "Left Peak      >%f" % self.audio['Peak_L']
        print "Right Peak     >%f" % self.audio['Peak_R']


class ProcessAudio(AudioData):
    def __init__(self):
        # set up audio input
        self.recorder = alsaaudio.PCM(type=alsaaudio.PCM_CAPTURE, mode=alsaaudio.PCM_NORMAL)
        self.recorder.setchannels(CHANNELS)
        self.recorder.setrate(RATE)
        self.recorder.setformat(INFORMAT)
        self.recorder.setperiodsize(FRAMESIZE)

        AudioData.__init__(self)

        self.peakC = 0.0
        self.minC  = maxValue
        self.dc    = []
        self.readtime=[]

        # window         = np.kaiser(FRAMESIZE+NUMPADS, WINDOW)  #Hanning window
        self.window = np.blackman(FRAMESIZE)
        self.createBands()
        print "ProcessAudio: reading from soundcard ", self.recorder.cardname()

    def process(self):
        '''
        Wait for the frame to be ready, then process the Samples
        '''
        self.calcReadtime()
        retry   = 0
        datalen = 0
        while datalen < FRAMESIZE:
            datalen, raw_data    = self.recorder.read()
            if datalen< 0: print 'ProcessAudio.process> *** datalen %d, buffer size %d' % (datalen, len(raw_data))

        while retry<5:
            try:
                data        = np.frombuffer( raw_data, dtype=np.int16 )
                dataL       = data[0::2]
                dataR       = data[1::2]

                self.audio['SpectrumL'] = self.packFFT(self.calcFFT(dataL))
                self.audio['SpectrumR'] = self.packFFT(self.calcFFT(dataR))
                self.audio['VU_L'], self.audio['Peak_L'] = self.VU(dataL)
                self.audio['VU_R'], self.audio['Peak_R'] = self.VU(dataR)
                # self.calibrate(data)

                break

            except Exception as e:
                print "Failed decode ", e
                retry += 1

        # self.calcReadtime(False)


    def createBands(self, spacing=OCTAVE, fcentre=FIRSTCENTREFREQ):
        '''
        Create the upper bounds of each interval as an array that can be used to fill the fft data
        '''
        self.octave         = spacing
        self.firstfreq      = fcentre
        self.intervalUpperF = []
        print "ProcessAudio.createBands >Calculate Octave band frequencies: 1/%2d octave, starting at %2f Hz" % (spacing, fcentre)
        #
        # Loop in octaves bands
        #
        startbin = 1
        FFACTOR = math.pow(2, 1.0/float(2*spacing) )
        intervalUpper   = fcentre * FFACTOR

        while intervalUpper < RATE/2.0: # 50 intervals if plenty would < 1/6 to get so many
            bincount        = startbin
            fcentre         = fcentre * math.pow(2, float(1.0/spacing))
            intervalUpper   = fcentre * FFACTOR

            if bincount*BINBANDWIDTH > intervalUpper:
                # Check if the bin will fit in the octave band, if not discard the current octave band
                # print "  band too low @%dHz for bin %d at %dHz - skip it" % (intervalUpper, bincount, bincount*BINBANDWIDTH)
                continue
            else:
                # Check how many bins will comprise this octave band (must be at least one)
                while (bincount+1)*BINBANDWIDTH <= intervalUpper:
                    bincount    += 1
                self.intervalUpperF.append( intervalUpper )

            # print " Fcentre %2.1f, Upper bound %2.1f, startbin %d (%4.0fHz), to bin %d (%4.0fHz)" % (fcentre, intervalUpper, startbin, startbin * BINBANDWIDTH, bincount, bincount * BINBANDWIDTH )
            startbin = bincount+1


        print "  %d bands determined\n" % (len(self.intervalUpperF))
        return self.intervalUpperF

    def VU(self,data):
        peak = scale*math.log( np.abs(np.max(data)-np.min(data))/maxValue, 10 ) + offset
        vu   = self.floor((1*math.log( self.rms(data)/100, 10)+offset),0)

        return (vu,peak)


    def floor(self, x,y):
        if x > y:
            return x
        else:
            return 0

    def calcReadtime(self,start=True):
        if start:
            self.startreadtime = time.time()
        else:
            self.readtime.append(time.time()-self.startreadtime)
            if len(self.readtime)>100: del self.readtime[0]
            print 'ProcessAudio:calcReadtime> %3.3fms, %3.3f' % (np.mean(self.readtime)*1000, self.readtime[-1])


    def calcDCoffset(self, data):
        """ Create a ring buffer of DC mean level """
        self.dc.append(np.mean(data))  #setDC

        if len(self.dc) > DCOFFSETSAMPLES:
            del self.dc[0]

        self.dcoffset = sum(self.dc)/len(self.dc)

        return self.dcoffset


    def calcFFT(self, data):
        self.calcDCoffset(data)
        r1   = np.abs(np.fft.rfft( data ))**2 #self.window
        p    = np.amax(r1)

        for i in range(0, len(r1)):
            if r1[i] == p: break
        print "peak power %2dHz=%2.1f: bin %d.  DCoffset = %f" % (i*BINBANDWIDTH, p, i, self.dcoffset)
        return r1


    def packFFT(self,bins):
        '''
        # Pack bins into octave intervals
        # Convert amplitude into dBs
        '''
        startbin = 1 #do not use bin[0] which is DC
        spectrumBands = []

        for band in self.intervalUpperF:  # collect bins at a time
            bincount    = startbin

            while bincount*BINBANDWIDTH <= band:
                bincount    += 1

            level = np.log10((bins[startbin:bincount].mean()))
            spectrumBands.append( level )
            startbin = bincount

        return spectrumBands

    def printSpectrum(self, left=True):
        FFACTOR = math.pow(2, 1.0/float(2*self.octave) )
        if left:
            power = self.audio['SpectrumL']
        else:
            power = self.audio['SpectrumR']

        for i in range (0,len(power)):
            fCentre = self.intervalUpperF[i]/FFACTOR
            self.printPower(power[i], self.intervalUpperF[i]/FFACTOR)
        print "--------------"

    def getSpectrum(self, left=True):
        FFACTOR = math.pow(2, 1.0/float(2*self.octave) )
        if left:
            power = self.audio['SpectrumL']
        else:
            power = self.audio['SpectrumR']

        channelPower = []
        for i in range (0,len(power)):
            fCentre = self.intervalUpperF[i]/FFACTOR
            channelPower.append(self.filter(power[i], fCentre))
        return channelPower


    def leftCh(self):
        return self.getSpectrum()

    def rightCh(self):
        return self.getSpectrum(left=False)


    def calibrate(self, data):
        """
        evaluate how many bits of data are being used by the ADC
        """
        text  = ''
        r = self.rms(data)
        maxS = np.max(np.abs(data))
        minS = np.min(np.abs(data))
        # print np.min(dataL), maxL

        if maxS > self.peakC:
            self.peakC = maxS
            text  += "peak %8d" % self.peakC
        if minS < self.minC:
            self.minC = minS
            text  += " min %8d\n" % self.minC
        return text

    def dynamicRange(self):
        print "max %d, min %d" % (self.peakC, self.minC)
        dr = 20.0*math.log(self.peakC/(self.minC+1),10)
        print "Dynamic range = %2.0f dB" % dr

    def rms(self, y):
        n=np.sqrt(np.abs(np.mean(np.square(y))))
        return n


    ''' test functions '''

    def printBins(bins):
        text  = ""
        for i in range (1,len(bins)):
            text += "[%2d %2.1f] " % (i*BINBANDWIDTH, bins[i]/250)
            if i >MAXBANDS: break
        print text

    def LR(data):
        dataL = data[0::2]
        dataR = data[1::2]

        peakL = scale*math.log(np.abs(np.max(dataL)-np.min(dataL))/maxValue,10)+offset
        peakR = scale*math.log(np.abs(np.max(dataR)-np.min(dataR))/maxValue,10)+offset
        lString = "-"*int(bars-peakL*bars)+"#"*int(peakL*bars)
        rString = "#"*int(peakR*bars)+"-"*int(bars-peakR*bars)
        print("[%s]=L%10f\t%10f R=[%s]"%(lString, peakL, peakR, rString))

    def LR2(data):

        lString = "-"*int(bars-left[0]*bars)+"#"*int(left[0]*bars)
        rString = "#"*int(right[0]*bars)+"-"*int(bars-right[0]*bars)
        print("[%s]=L%10f\t%10f R=[%s]"%(lString, left[1], right[1], rString))
        # print("L=[%s]\tR=[%s]"%(lString, rString))



def main():
    # main loop
    audioprocessor = ProcessAudio()
    runflag = 1
    while runflag:

        for i in range(int(duration*44100/FRAMESIZE)): #go for a few seconds

            audioprocessor.process()
            audioprocessor.printSpectrum()
            audioprocessor._print()

        audioprocessor.dynamicRange()
        runflag = 0

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
