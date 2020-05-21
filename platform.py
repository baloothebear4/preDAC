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

from oleddriver import internalOLED, frontOLED

class Volume():
    def __init__(self):
        self.volume_dB      = -20.0
        self.volume_percent = 70
        self.mute = False
        self.gain = False

    @property
    def volume(self):
        return

class Source():
    def __init__(self):
        self.source_name    = 'dac'
        self.source_channel = 1

class Audio():
    def __init__(self):
        pass

class Platform(Volume, Source, Audio):
    """ this is the HW abstraction layer and includes the device handlers and data model """
    def __init__(self):
        Volume.__init__(self)
        Source.__init__(self)
        Audio.__init__(self)
        self.display = internalOLED()
        # frontOLED.__init__(self)

        """ need to work out how the hw boards are combined for cross functionality """

# end Platform
