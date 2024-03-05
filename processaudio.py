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

import struct, time, math, os
import numpy as np
import pyaudio
import wave
from events import Events

# constants
CHANNELS        = 2
# INFORMAT        = alsaaudio.PCM_FORMAT_S16_LE
INFORMAT        = pyaudio.paInt16
RATE            = 44100  #33075  # 22050, 24000,
FRAMESIZE       = int(1024*2.0)
maxValue        = float(2**15)
SAMPLEPERIOD    = FRAMESIZE/RATE

SILENCESAMPLES  = 7   / SAMPLEPERIOD  #7 seconds worth of samples
PEAKSAMPLES     = 0.7 / SAMPLEPERIOD  #0.5 seconds worth of VU measurements
VUSAMPLES       = 0.1 / SAMPLEPERIOD  #0.3 seconds is the ANSI VU standard

RECORDSTATE     = False
RECORDTIME      = 30 * 60 / SAMPLEPERIOD / CHANNELS # failfase to stop the disk filling up
RECORDPATH      = "/home/pi/preDAC/rec/"
RECORDFILESUFFIX = "preDAC"
RECORDINGS_PATTERN = RECORDPATH + RECORDFILESUFFIX + "-%s.wav"

WINDOW          = 7 # 4 = Hanning
FIRSTCENTREFREQ = 31.25        # Hz
OCTAVE          = 3
NUMPADS         = 0
BINBANDWIDTH    = RATE/(FRAMESIZE + NUMPADS) #ie 43.5 Hz for 44.1kHz/1024
DCOFFSETSAMPLES = 200


RMSNOISEFLOOR   = -70    # dB
DYNAMICRANGE    = 80     # Max dB
SILENCETHRESOLD = 0.001   #0.02   # Measured from VU Noise Floor + VU offset

# VU calibration and scaling  DEPRECATED
PeakRange = DYNAMICRANGE - 5 # was 50 antificipated dB range
VURange   = DYNAMICRANGE - 20
PeakOff   = -(RMSNOISEFLOOR + 10) # lower limit to display
VUOff     = -(RMSNOISEFLOOR + 10) # was 40

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
        self.vumax    = {'left': 0.01, 'right':0.01}
        self.peakmax  = {'left': 3.9, 'right':3.9}
        self.spectrum = {'left': data, 'right':data}
        self.bins     = {'left': data, 'right':data}
        self.samples  = {'left': data_s, 'right':data_s}
        self.monosamples     = data
        self.signal_detected = False
        self.peakwindow      = {'left': WindowAve(PEAKSAMPLES), 'right': WindowAve(PEAKSAMPLES)}
        self.vuwindow        = {'left': WindowAve(VUSAMPLES), 'right': WindowAve(VUSAMPLES)}
        self.recordfile = self.find_next_file( RECORDINGS_PATTERN )

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

        self.recordingState = RECORDSTATE
        self.recording      = []

        AudioData.__init__(self)

        self.peakC      = 0.0
        self.minC       = maxValue
        self.dc         = []
        self.readtime   = []
        self.silence    = WindowAve(SILENCESAMPLES)

        self.window     = np.kaiser(FRAMESIZE+NUMPADS, WINDOW)  #Hanning window

        print("AudioProcessor.__init__> ready and reading from soundcard %s, Recording is %s " % (self.recorder.get_default_input_device_info()['name'], RECORDSTATE))

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
        self.record(in_data)
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

                self.record(raw_data)

                break  # all good no data overruns detected

            except Exception as e:
                print("AudioProcessor.captureAudio> sample overrun ", e)
                self.stream   = self.recorder.open(format = INFORMAT,rate = RATE,channels = CHANNELS,input = True, frames_per_buffer=FRAMESIZE)
                retry += 1

        self.calcReadtime(False)

    def start_recording(self):
        self.recordingState = True

    def stop_recording(self):
        self.recordingState = False
        self.saveRecording()
        self.recording = []
        self.events.Audio('recording_stopped')

    def record(self, data):
        if self.recordingState:
            self.recording.append(data)

            if len(self.recording) >  RECORDTIME:
                self.stop_recording()

            elif len(self.recording) % SAMPLEPERIOD == 1:
                print("AudioProcessor.record> recorded %fs audio " % len(self.recording)/SAMPLEPERIOD )

    def saveRecording(self):
        # Save the recorded data as a WAV file
        self.recordfile = self.find_next_file( RECORDINGS_PATTERN )
        print('Finished recording to ', self.recordfile)
        try:
            # bits = self.recorder.get_sample_size(INFORMAT)
            # wf = PyWave.open(recordfile, mode='w', channels = CHANNELS, frequency = RATE, bits_per_sample = bits, format = INFORMAT)
            wf = wave.open(self.recordfile, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.recorder.get_sample_size(INFORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(self.recording))

            wf.close()
        except Exception as e:
            print("AudioProcessor.save_recording> ", e)


    def find_next_file(self, path_pattern):
        """
        Finds the next free path in an sequentially named list of files

        e.g. path_pattern = 'file-%s.txt':

        file-1.txt
        file-2.txt
        file-3.txt

        Runs in log(n) time where n is the number of existing files in sequence
        """
        i = 1

        # First do an exponential search
        while os.path.exists(path_pattern % i):
            i = i * 2

        # Result lies somewhere in the interval (i/2..i]
        # We call this interval (a..b] and narrow it down until a + 1 = b
        a, b = (i // 2, i)
        while a + 1 < b:
            c = (a + b) // 2 # interval midpoint
            a, b = (c, b) if os.path.exists(path_pattern % c) else (a, c)

        return path_pattern % b


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
        signal_level = (self.vu['left'] + self.vu['right'])/2.0
        ave_level    = self.silence.average(signal_level)
        # print (signal_level )

        if ave_level < SILENCETHRESOLD:
            print("ProcessAudio.detectSilence> Silence at", ave_level, signal_level)
            self.signal_detected = False
            self.silence.reset('signal')  # clear the window to keep checking for Silence
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
        # print("channel power = ", 10*math.log(self.rmsPower(self.samples[channel]), 10))
        """ OLD log version
        peak = 10*math.log( np.abs(np.square(np.max(self.samples[channel]) -np.min(self.samples[channel]))), 10 )
        vu   = self.floor(  (10*math.log( self.rmsPower(self.samples[channel]), 10)+VUOff)/VURange, 0)
        # print("vu ", vu, "peak", peak)
        """


        peak = np.abs(np.square(np.max(self.samples[channel]) -np.min(self.samples[channel])))
        vu   = 3 * self.vuwindow[channel].average( np.sqrt(np.mean(np.square( self.samples[channel] ) ) )/1.414 )
        # print (vu)

        # Leave the maximums preset
        if peak > self.peakmax[channel]:
            self.peakmax[channel] = peak
            print("vu max", vu, "peak max", peak, "channel ", channel)
        #
        if vu > self.vumax[channel]:
            self.vumax[channel] = vu
            print("vu max", self.vumax[channel], "peak max", self.peakmax[channel], "channel ", channel)

        peakave = self.peakwindow[channel].average(peak/ self.peakmax[channel])

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

            level = 10*np.log10((bins[startbin:bincount].mean()+0.0000001))
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
