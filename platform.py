#!/usr/bin/env python
"""
 Base classes for entry to data model and HW
    - Platform: data access abstracted from data sources
    - Volume:   volume control management class, including Mute function
    - Source:   source select class
    - Audio:    source of all processed audio data inc VU, peak and spectrums


 Part of mVista preDAC2 project

 v1.0 Baloothebear4 May 2020

"""

from oleddriver  import internalOLED, frontOLED
from hwinterface import AudioBoard, ControlBoard, RemoteController, VolumeBoard
from processaudio import ProcessAudio

class Volume():
    def __init__(self):
        self._volume_dB      = -20.0
        self.volume_raw      = 34    # this is the -0.5 x the dB attenuation, + the gain + 12dB is the total
        self._volume         = 0.70
        self.mute = False
        self.gain = False

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, v):
        if v > 1.0 or v < 0: raise ValueError('Volume.volume> invalid volume ', v)
        self._volume = v

    @property
    def volume_db(self):
        return -0.5*self.volume_raw + 12 #+25 is gain is on



class Source:
    """
    Management of the source types

    NB: Sources are mapped to audioBoard control logical controls 0 - 5
    """

    IconFiles = {   'streamer'  : ["Streamer.png"],
                    'dac'       : ["Dac.png"],
                    'cd'        : ["CD 0.png", "CD 60.png", "CD 120.png", "CD 180.png", "CD 240.png", "CD 300.png" ],
                    'rec'       : ["Tape 0.png", "Tape 60.png", "Tape 120.png", "Tape 180.png", "Tape 240.png", "Tape 300.png"],
                    'aux'       : ["Aux.png"],
                    'phono'     : ["Phono 0.png", "Phono 60.png", "Phono 120.png", "Phono 180.png", "Phono 240.png", "Phono 300.png"]  }
    Text      = { 'streamer' : "Streamer", 'dac' : "DAC", 'cd': "CD", 'rec': "Tape", 'aux' : "AUX", 'phono' : "Phono" }

    def __init__(self, getSequence, setSource):
        self.activeSource      = 'dac'
        self.setSource         = setSource
        self.sourceSequence    = getSequence()            # a dictionary mapping the sources to logical values
        self.sourcesEnabled    = Source.Text.keys()       # List of available (can change as DAC settings are altered)
        self.currentIcon       = 0   # icon position in the list of icons for the current source
        self.screenName        = "description of current screen"

    def activeSource(self):
        return self.activeSource

    def activeSourceText(self):
        return Source.Text[ self.activeSource ]

    def sourceText(self):
        return Source.Text

    def getSourceIconFiles(self, source):
        return Source.IconFiles[source]

    def sourcesAvailable(self):
        return self.sourcesEnabled

    def nextSource(self):
        # find the current sequence position, increment and up the active source
        pos = self.sourceSequence[self.activeSource]
        if pos == len(self.sourceSequence)-1:
            pos= 0
        else:
            pos += 1
        for s, p in self.sourceSequence.iteritems():
            if p == pos:
                self.activeSource = s
                self.currentIcon  = 0
                self.setSource( s )
                return s

    def prevSource(self):
        # find the current sequence position, increment and up the active source
        pos = self.sourceSequence[self.activeSource]
        if pos == 0 :
            pos= len(self.sourceSequence)-1
        else:
            pos -= 1
        for s, p in self.sourceSequence.iteritems():
            if p == pos:
                self.activeSource = s
                self.currentIcon  = 0
                self.setSource( s )
                return s

    def nextIcon(self):
        if self.currentIcon+1 < len(Source.IconFiles[self.activeSource]):
            self.currentIcon += 1
        else:
            self.currentIcon  = 0
        # print "Source.nextIcon>", self.currentIcon,     len(Source.IconFiles[self.activeSource])


class Platform(Volume, Source, ProcessAudio, AudioBoard):
    """ this is the HW abstraction layer and includes the device handlers and data model """
    def __init__(self):
        Volume.__init__(self)
        Source.__init__(self, self.sourceLogic, self.setSource)
        ProcessAudio.__init__(self)

        # test data
        # testdataL      = [0.5]*50
        # testdataR      = [0.3]*50
        # self.vu       = {'left': 0.6, 'right':0.6}
        # self.peak     = {'left': 0.8, 'right':0.9}
        # self.spectrum = {'left': testdataL, 'right': testdataR}

        try:
            self.internaldisplay   = internalOLED()
        except:
            self.internaldisplay   = None
            print("Platform.__init__> failed to start internal display")

        try:
            self.frontdisplay      = frontOLED()
        except:
            self.frontdisplay = None
            print("Platform.__init__> failed to start front display")

    def __str__(self):
        text = ">"
        if self.internaldisplay is not None:
            text += type(self.internaldisplay).__name__

        if self.frontdisplay is not None:
            text += " >" + type(self.frontdisplay).__name__
        # return "Platform> status: displays  %s, %s" % (type(self.internaldisplay).__name__, type(self.frontdisplay).__name__)
        return "Platform> status: displays  %s" % ( text )

# end Platform
