#!/usr/bin/env python
"""
 Octave class
    - Maths and array manipulation to for Spectrum analyser

 Part of mVista preDAC

 Baloothebear4 Sept 17

"""
import math

class Octave:
    def __init__(self, interval, fftResolution, Nyquistfreq, binCount):
        self.interval      = interval		# the Octave interval to create  eg 1, 3, 6
        self.resolution    = fftResolution  # the freq interval of the FFT
        self.maxFreq       = 15000          # Limit the display max Nyquistfreq    # this is highest freq available
        self.binCount      = binCount
        self.minFreq       = fftResolution  #self.calcSideBands(fftResolution)['L'+str(fftResolution)]  # this is as low at the FFT resolves
        self.centreFreqs   = []             # array of freqs across the interval from min to max
        self.sideBands     = {}             # dict of upper & lower side band frequences : key syntax Lfff, Ufff
        self.barMap        = {}
        self.startFreq     = self.minFreq #self.resolution

        """ create the centre frequency & sidearray """
        f0 = self.startFreq
        while( f0 < self.maxFreq):
            if f0>=self.minFreq:
                self.centreFreqs.append( f0 )
                self.sideBands.update( self.calcSideBands( f0 ) )
            f0 = self.nextInterval( f0 )
        print "Octave __init: max freq", self.maxFreq
        print " freq bands:>", self

        """ map the bins to the bars """
        binCounter      = self.startFreq/self.resolution  #loose the first bin
        binFreq         = self.resolution * binCounter
        freqsNotmatched = []
        binsperband     = 0
        for f0 in self.centreFreqs:
            self.barMap.update({f0:[]})
            # print "Octave.init>is", binFreq, " in ", self.sideBands['L'+str(f0)], f0, self.sideBands['U'+str(f0)]
            while binFreq >= self.sideBands['L'+str(f0)] and binFreq <= self.sideBands['U'+str(f0)] and binCounter<self.binCount-1:
                # print "Octave.fill> found", f0, 'L'+str(f0), self.sideBands['L'+str(f0)], self.sideBands['U'+str(f0)], binFreq
                # print "Octave.fill>       match freq: binFreq, f1, f0, f2", binFreq, self.sideBands['L'+str(f0)], f0, self.sideBands['U'+str(f0)]
                self.barMap[f0].append(binCounter)
                binsperband   += 1
                binCounter    += 1
                binFreq       = self.resolution * binCounter
            if binsperband >= 1:
                # print "add freq ", f0
                binsperband = 0
            else:
                # pass
                # print "Octave.fill> no bins match freq: binFreq (bin[]), f1, f0, f2", binFreq, binCounter, self.sideBands['L'+str(f0)], f0, self.sideBands['U'+str(f0)]
                freqsNotmatched.append(f0)

                # print "Octave fills> bar Map"
                # for f in self.barMap:
                #     print(" %dHz to bins%s\n" % (f,self.barMap[f]))
        """ the match of bins to bars is not perfect at lower frequencies
            to maximise the low end display the frequency bars are simply deleted.
            The alternative solution is to interpolate even further or increase the
            minimum frequency.  Given the bars that do not match are approx 27 & 36Hz.
            This is a good compromise to have a wide bandwidth display and good performance """
        for f in freqsNotmatched:
            del self.barMap[f]
            self.centreFreqs.remove(f)
            # print "delete freq ", f
        print "Octave __init__> ready. Centre frequencies:", self.centreFreqs
        # print "Octave __init__> ready. Bar map:", self.barMap


    def intervalsCount(self):
        print "Octave.intervalsCount>", self.centreFreqs
        if len( self.centreFreqs ) == 0: print self
        return len( self.centreFreqs )

    def fill(self, fft):
        """
        From an array of FFT bins at a given frequency interval
        fill an array according to the Octave interval selected
        """
        intervals     = []
        binsperband   = 0
        # print "Octave.fill> len(fft)= ",len(fft),  " fft=",fft
        # print "Octave.fill> len barMap ", fft

        for f0 in self.centreFreqs:
            intervalLevel = 0
            # print "add bins ", self.barMap[f], "to band", f
            for b in self.barMap[f0]:
                if b> len(fft):
                    print "Octave.fill> fft data error: len=", len(fft), "Data",fft
                intervalLevel += fft[ b ]

            gain   = 10#11.0  #how much the signal ranges (higher less)
            scale  = 20#13.0  #how much a-weighting is applied
            offset = -0.5#-0.2  #to ensure the dc level is or noise floor
            # level = math.log(intervalLevel / (len(self.barMap[f0]) )**0.5, 2 )
            # intervals.append( 0.30+level/18)  #16*math.log((intervalLevel / binsperband)**0.5,2) )  # save the average level for the bins counted
            # level = (intervalLevel/len(self.barMap[f0])) **0.5
            level = self.aWeight(f0)/scale
            # intervals.append( math.log(1+level, 2) ) #16*math.log((intervalLevel / binsperband)**0.5,2) )  # save the average level for the bins counted
            intervals.append( offset+(level + math.log(1+intervalLevel, 2))/gain) #16*math.log((intervalLevel / binsperband)**0.5,2) )  # save the average level for the bins counted
            """ NB: these constants scale the levels to range of 0-1 (approx) """
            # print ("Octave.fill> f0=%d, intLevel=%f, mag=%f : log %f" % ( f0, intervalLevel, level,  level+math.log(1 + intervalLevel*scale, 2) ) )#math.log(1 +level, 2) ) )

            # print "Octave.fill > min, max", min(intervals), max(intervals)

            # # print "Octave fills end> bar Map"
            # # for f in self.barMap:
            # #     print(" %dHz to bins%s\n" % (f,self.barMap[f]))
            # for f in range(len(self.centreFreqs)):
            #     print ("Octave.fill end> f=%d, mag=%f" % ( self.centreFreqs[f], intervals[f]) )
        # raise Exception('quit')
        # print ("Octave.fill end> min mag=%f, max mag=%f" % ( min(intervals), max(intervals) ) )
        # print "intervals", intervals
        return intervals

    def calcSideBands(self, f0):
        exp = 1.0/(2*self.interval)
        f1 = f0 / 2**exp
        f2 = f0 * 2**exp
        # print ("Octave.calcSideBands> f0 %f, f1 %f, f2 %f" % (f0, f1, f2) ) #self.interval))
        return { 'L'+str(f0):int(f1), 'U'+str(f0):int(f2) }

    def nextInterval(self, f0):
        return int(f0*2**(1.0/(self.interval)))

    def aWeight(self, f):
        """
        Uses standard IEC 61672:2003 curve to compensate for the way the ear hears
        different frequencies.
        Returns the gain per input frequency in dB
        """
        Ra = 12194**2 * f**4/( (f**2 + 20.6**2) * ( (f**2 + 107.7**2) * ( f**2 + 737.9**2) )**0.5 * (f**2 + 12194**2))
        A  = 20 * math.log( Ra, 10) + 2.00

        return A

    def __repr__(self):
        print "Octave object: "

    def __str__(self):
        text  = "Octave Object:\n"
        text += " %20s : %d\n" % ('Interval', self.interval)
        text += " %20s : %d\n" % ('Resolution', self.resolution)
        text += " %20s : %d\n" % ('maxFreq', self.maxFreq)
        text += " %20s : %d\n" % ('minFreq', self.minFreq)
        text += " %20s : %s\n" % ('Centre freqs', self.centreFreqs)
        text += " %20s : %s\n" % ('Side freqs', self.sideBands)
        text += " %20s : %s\n" % ('Bins', self.binCount)
        text += "\nBarmap "
        for f in self.barMap:
            text += " %dHz to bins%s\n" % (f,self.barMap[f])
        return text



#### Test Code
if __name__ == '__main__':
    try:
        o = Octave( 3, 36, 9600, 256)
        for f in range (100, 10000, 100):
            print "f=", f, " Af=", o.aWeight(f)


    except:
        raise
