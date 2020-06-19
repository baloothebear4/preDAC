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

import struct, time, math
import numpy as np
import pyaudio
from events import Events

# constants
CHANNELS        = 2
# INFORMAT        = alsaaudio.PCM_FORMAT_S16_LE
INFORMAT        = pyaudio.paInt16
RATE            = 33075  # 22050, 24000,
FRAMESIZE       = int(1024*2.0)
maxValue        = float(2**15)
SAMPLEPERIOD    = FRAMESIZE/RATE

SILENCESAMPLES  = 5 / SAMPLEPERIOD    #5 seconds worth of samples
PEAKSAMPLES     = 0.5 / SAMPLEPERIOD  #0.5 seconds worth of VU measurements

RMSNOISEFLOOR   = -66  #dB
SILENCETHRESOLD = 0.02

WINDOW          = 7 # 4 = Hanning
FIRSTCENTREFREQ = 31.25        # Hz
OCTAVE          = 3
NUMPADS         = 0
BINBANDWIDTH    = RATE/(FRAMESIZE + NUMPADS) #ie 43.5 Hz for 44.1kHz/1024
DCOFFSETSAMPLES = 200

class WindowAve:
    """ Class to find the moving average of a set of window of points """
    def __init__(self, size):
        self.window = [1.0]*int(size)
        self.size   = int(size)

    def average(self, data):
        #add the data point to the window
        self.window.insert(0, data)
        del self.window[-1]
        return sum(self.window)/len(self.window)

    def reset(self,type):
        if type == 'silence':
            self.window = [0.0]*int(self.size)
        else:
            self.window = [1.0]*int(self.size)

class AudioData():
    def __init__(self):
        data          = [0.5]*50
        data_s        = np.arange(FRAMESIZE)

        self.vu       = {'left': 0.5, 'right':0.6}
        self.peak     = {'left': 0.8, 'right':0.9}
        self.spectrum = {'left': data, 'right':data}
        self.bins     = {'left': data, 'right':data}
        self.samples  = {'left': data_s, 'right':data_s}
        self.monosamples     = data
        self.signal_detected = False
        self.peakwindow      = {'left': WindowAve(PEAKSAMPLES), 'right': WindowAve(PEAKSAMPLES)}

    def filter(self, signal, fc):
        return signal

    def printPower(self, power, fCentre):
        # apply a frequency dependent filter
        print("%6.1f @f=%-5d %s" % (power, fCentre , "*"*int(self.filter(power, fCentre))))

    def seeData(self, data, title):
        line = "[%d] %s\n" % (len(data), title)
        for i in range(len(data)):
            line += "%6d "%data[i]
            if i % 16 == 15:
                print(line)
                line = ""

    def _print(self):
        self.LR2(self.vu, self.peak)


class AudioProcessor(AudioData):
    def __init__(self, events):
        self.events   = events
        # set up audio input
        self.recorder = pyaudio.PyAudio()


        AudioData.__init__(self)

        self.peakC      = 0.0
        self.minC       = maxValue
        self.dc         = []
        self.readtime   = []
        self.silence    = WindowAve(SILENCESAMPLES)

        self.window         = np.kaiser(FRAMESIZE+NUMPADS, WINDOW)  #Hanning window
        # self.window     = np.blackman(FRAMESIZE)
        print("AudioProcessor.__init__> ready and reading from soundcard ", self.recorder.get_default_input_device_info()['name'])

    def start_capture(self):
        try:
            self.stream   = self.recorder.open(format = INFORMAT,rate = RATE,channels = CHANNELS,input = True, frames_per_buffer=FRAMESIZE, stream_callback=self.callback)
            self.stream.start_stream()
            print("AudioProcessor.start_capture> ADC/DAC ready")
        except Exception as e:
            print("AudioProcessor.start_capture> ADC/DAC not available", e)

    def stop_capture(self):
        try:
            self.stream.stop_stream()
            self.stream.close()
        except Exception as e:
            print("AudioProcessor.Stop_capture> error", e)

    def callback(self, in_data, frame_count, time_info, status):

        # print('AudioProcessor.callback> received %d frames, time %s, status %s, data bytes %d' % (frame_count, time_info, status, len(in_data)))
        self.calcReadtime()
        data        = np.frombuffer(in_data, dtype=np.int16 )/maxValue
        self.samples['left']  = data[0::2]
        self.samples['right'] = data[1::2]
        self.events.Audio('capture')
        # self.calcReadtime(False)
        return (in_data, pyaudio.paContinue)

    def captureAudio(self):
        '''
        Wait for the frame to be ready, then process the Samples
         - this is used for blocking calls
        '''
        self.calcReadtime()
        retry   = 0
        datalen = 0


        while retry<5:
            try:
                while datalen < FRAMESIZE:
                    raw_data    = self.stream.read(FRAMESIZE)
                    datalen = len(raw_data)
                    if datalen< 0: print('AudioProcessor.process> *** datalen %d, buffer size %d' % (datalen, len(raw_data)))

                data        = np.frombuffer(raw_data, dtype=np.int16 )/maxValue
                self.samples['left']  = data[0::2]
                self.samples['right'] = data[1::2]
                # self.monosamples = data.sum(axis=1) / 2

                self.process()

                # self.seeData(dataL,"left")
                # self.seeData(dataR,"right")
                # print("L: %s <-> %s :R" % (self.calibrate(dataL),self.calibrate(dataR)))
                self.calibrate(self.samples['left'])
                self.calibrate(self.samples['right'])

                break  # all good no data overruns detected

            except Exception as e:
                print("AudioProcessor.captureAudio> sample overrun ", e)
                self.stream   = self.recorder.open(format = INFORMAT,rate = RATE,channels = CHANNELS,input = True, frames_per_buffer=FRAMESIZE)
                retry += 1

        self.calcReadtime(False)

    def process(self):
        self.bins['left']     = self.calcFFT(self.samples['left'])
        self.bins['right']    = self.calcFFT(self.samples['right'])
        self.vu['left'], self.peak['left']  = self.VU('left')
        self.vu['right'], self.peak['right'] = self.VU('right')
        self.detectSilence()
        self.calcReadtime(False)
                # other functions to calculate DC offset, noise level, silence, RMS quiet etc can go here

    def detectSilence(self):
        # use hysterises - quick to detect a signal, slow to detect silience (5 seconds)
        signal_level = self.vu['left']
        ave_level    = self.silence.average(signal_level)

        if self.signal_detected and ave_level < SILENCETHRESOLD:
            print("ProcessAudio.detectSilence> Silence at", ave_level, signal_level)
            self.signal_detected = False
            self.silence.reset('silence')
            self.events.Audio('silence_detected')
        elif not self.signal_detected and signal_level >= SILENCETHRESOLD:
            print("ProcessAudio.detectSilence> Signal at", ave_level, signal_level)
            self.signal_detected = True
            self.silence.reset('signal')
            self.events.Audio('signal_detected')
        #else: no change to the silence detect state


    def createBands(self, spacing, fcentre=FIRSTCENTREFREQ):
        '''
        Create the upper bounds of each interval as an array that can be used to fill the fft data
        - spacing is the octave spacing eg 3.0, 6.0
        - fcentre is the lowest start frequency eg 31.25
        '''
        self.firstfreq      = fcentre
        intervalUpperF = []
        centres        = []
        # print("AudioProcessor.createBands >Calculate Octave band frequencies: 1/%2d octave, starting at %2f Hz" % (spacing, fcentre))
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
                intervalUpperF.append( intervalUpper )
                centres.append( fcentre )

            # print " Fcentre %2.1f, Upper bound %2.1f, startbin %d (%4.0fHz), to bin %d (%4.0fHz)" % (fcentre, intervalUpper, startbin, startbin * BINBANDWIDTH, bincount, bincount * BINBANDWIDTH )
            startbin = bincount+1


        # print("AudioProcessor.createBands>  %d bands determined at: %s" % (len(centres), ["%1.0f" % f for f in centres]))
        return intervalUpperF

    def VU(self,channel):
        """ normalise to 0-1 """

        PeakRange = 50  # antificipated dB range
        VURange   = 45
        PeakOff   = 40  # lower limit to display
        VUOff     = 40


        peak = 10*math.log( np.abs(np.square(np.max(self.samples[channel]) -np.min(self.samples[channel]))), 10 )
        vu   = self.floor(  (10*math.log( self.rmsPower(self.samples[channel]), 10)+VUOff)/VURange, 0)
        # print("vu ", vu, "peak", peak)
        peakave = self.floor( (self.peakwindow[channel].average(peak)+PeakOff)/PeakRange, 0)

        return (vu, peakave)


    """ use this to shift the noise floor eg: RMS 20 - 5000 -> 0->5000"""
    def floor(self, x,y):
        if x > y:
            return x
        else:
            return y

    def calcReadtime(self,start=True):
        if start:
            self.startreadtime = time.time()
        else:
            self.readtime.append(time.time()-self.startreadtime)
            if len(self.readtime)>100: del self.readtime[0]
            # print('AudioProcessor:calcReadtime> %3.3fms' % (np.mean(self.readtime)*1000))


    def calcDCoffset(self, data):
        """ Create a ring buffer of DC mean level """
        self.dc.append(np.mean(data))  #setDC

        if len(self.dc) > DCOFFSETSAMPLES:
            del self.dc[0]

        self.dcoffset = sum(self.dc)/len(self.dc)

        return self.dcoffset


    def calcFFT(self, data):
        # self.calcDCoffset(data)
        r1   = np.abs(np.fft.rfft( data * self.window ))**2 #squared to get the power
        # p    = np.amax(r1)

        # for i in range(0, len(r1)):
        #     if r1[i] == p: break
        # print("AudioProcessor.calcFFT> peak power %2dHz=%2.1f: bin %d.  DCoffset = %f" % (i*BINBANDWIDTH, p, i, self.dcoffset))
        return r1


    def packFFT(self, intervalUpperF, channel):
        '''
        # Pack bins into octave intervals
        # Convert amplitude into dBs
        '''
        bins = self.bins[channel]
        startbin = 1 #do not use bin[0] which is DC
        spectrumBands = []

        for band in intervalUpperF:  # collect bins at a time
            bincount    = startbin

            while bincount*BINBANDWIDTH <= band:
                bincount    += 1

            level = 10*np.log10((bins[startbin:bincount].mean()))
            spectrumBands.append( self.normalise(level) )
            startbin = bincount

        return spectrumBands

    def normalise(self, level):
        """ convert from dB into a percentage """
        """ need to calibrate this more carefully """
        return (20 + level)/70

    def printSpectrum(self, octave, intervalUpperF, left=True):
        FFACTOR = math.pow(2, 1.0/float(2*octave) )
        if left:
            power = self.spectrum['left']
        else:
            power = self.spectrum['right']

        for i in range (0,len(power)):
            fCentre = intervalUpperF[i]/FFACTOR
            self.printPower(power[i], intervalUpperF[i]/FFACTOR)
        print("--------------")

    def getSpectrum(self, octave, intervalUpperF, left=True):
        FFACTOR = math.pow(2, 1.0/float(2*octave) )
        if left:
            power = self.spectrum['left']
        else:
            power = self.spectrum['right']

        channelPower = []
        for i in range (0,len(power)):
            fCentre = intervalUpperF[i]/FFACTOR
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
        text = ''
        r    = self.rmsPower(data)
        text = "%f" % r
        maxS = np.max(r)
        minS = np.min(r)
        # print np.min(dataL), maxL

        if maxS > self.peakC:
            self.peakC = maxS
            text  += "max %8d " % self.peakC
        if minS < self.minC:
            self.minC = minS
            text  += " min %8d " % self.minC
        return text

    def dynamicRange(self):
        print("dynamicRange> RMS max %d, min %d" % (self.peakC, self.minC))
        dr = 20.0*math.log(self.peakC,10)
        print("dynamicRange> Dynamic range = %2.0f dB" % dr)

    """ calculate the RMS power (NB: sqrt is not required) """
    def rmsPower(self, y):
        return np.abs(np.mean(np.square(y)))

    def processstatus(self):
        text  = "Process audio> signal det %s" % self.signal_detected
        text += "\n L%10f-^%10f^%10f\t%10f R"% (self.vu['left'], self.peak['left'], self.peak['right'], self.vu['right'])
        text += "\n Peak Spectrum L:%f, R:%f" % (max(self.bins['left']), max(self.bins['right']) )
        return text



    """ test code """

    def LR2(self, vu, peak):
        lString = "-"*int(bars-vu['left']*bars)+"#"*int(vu['left']*bars)
        rString = "#"*int(vu['right']*bars)+"-"*int(bars-vu['right']*bars)
        print(("[%s]=L%10f-^%10f^%10f\t%10f R=[%s]"% (lString, vu['left'], peak['left'], peak['right'], vu['right'], rString)))
        # print("L=[%s]\tR=[%s]"%(lString, rString))

    def printBins(bins):
        text  = ""
        for i in range (1,len(bins)):
            text += "[%2d %2.1f] " % (i*BINBANDWIDTH, bins[i]/250)
            if i >50: break
        print(text)

def main():
    # main loop
    events = Events('Audio')
    audioprocessor = AudioProcessor(events)
    runflag = 1
    while runflag:

        for i in range(int(10*44100/FRAMESIZE)): #go for a few seconds

            audioprocessor.process()
            audioprocessor.printSpectrum()
            # audioprocessor._print()
            # audioprocessor.calibrate()

        audioprocessor.dynamicRange()
        runflag = 0

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
