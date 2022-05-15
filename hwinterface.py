#!/usr/bin/env python
"""
 preDAC preamplifier project

 HW interface class
    - controls the interaction with the HW driver objects:
        volumeBoard
        audioBoard
        controlBoard
        controllerKnob

 Baloothebear4
 v1 Sept 17
 v2 Apr  20 - new Audio & Control HW

"""

from rotenc import RotaryEncoder
from pcf8574 import PCF8574
from events import Events

import RPi.GPIO as GPIO
import os, time, socket

class Source:
    """
    Management of the source types

    NB: Sources are mapped to audioBoard control logical controls 0 - 5
    """

    IconFiles = {   'streamer'  : ["Streamer.png"],
                    'dac'       : ["Dac.png"],
                    'cd'        : ["CD 0.png", "CD 60.png", "CD 120.png", "CD 180.png", "CD 240.png", "CD 300.png" ],
                    'tape'      : ["Tape 0.png", "Tape 60.png", "Tape 120.png", "Tape 180.png", "Tape 240.png", "Tape 300.png"],
                    'aux'       : ["Aux.png"],
                    'phono'     : ["Phono 0.png", "Phono 60.png", "Phono 120.png", "Phono 180.png", "Phono 240.png", "Phono 300.png"],
                    'phono2'    : ["Phono 0.png", "Phono 60.png", "Phono 120.png", "Phono 180.png", "Phono 240.png", "Phono 300.png"]  }

    def __init__(self):
        self.sourcesEnabled    = Source.IconFiles.keys()       # List of available (can change as DAC settings are altered)
        self.currentIcon       = 0   # icon position in the list of icons for the current source
        self.screenName        = "description of current screen"
        self.activeSource      = ListNext(self.sourceLogic(), AudioBoard.DEFAULT_SOURCE)

    @property
    def activeSourceText(self):
        return AudioBoard.audioBoardMap[self.activeSource.curr][AudioBoard.SOURCETEXT]

    @property
    def longestSourceText(self):
        longest = 0
        for s in AudioBoard.audioBoardMap:
            l = len(AudioBoard.audioBoardMap[s][AudioBoard.SOURCETEXT])
            if l > longest:
                longest = l
                text    = AudioBoard.audioBoardMap[s][AudioBoard.SOURCETEXT]
        return text

    @property
    def widestSourceText(self):
        return "Tape"

    def getSourceIconFiles(self, source):
        return Source.IconFiles[source]

    @property
    def sourcesAvailable(self):
        return self.sourcesEnabled

    def prevSource(self):
        self.currentIcon  = 0
        self.setSource( self.activeSource.prev )
        return self.activeSource.curr

    def nextSource(self):
        self.currentIcon  = 0
        self.setSource( self.activeSource.next )
        return self.activeSource.curr

    def nextIcon(self):
        if self.currentIcon+1 < len(Source.IconFiles[self.activeSource.curr]):
            self.currentIcon += 1
        else:
            self.currentIcon  = 0
        # print "Source.nextIcon>", self.currentIcon,     len(Source.IconFiles[self.activeSource])

    def sourceLogic(self):
        #collect the signal sources into a list
        logic = []
        for s in AudioBoard.audioBoardMap:
            if  AudioBoard.audioBoardMap[s][AudioBoard.SIGNAL]:
                logic.append(s)
        print("AudioBoard.sourceLogic > ", logic)
        return logic


class AudioBoard(Source, PCF8574):  #subclass so that there is only 1 interface point to all the HW classes
    """                source   board relayi2c1 pin ref, gain , text, signal? """
    audioBoardMap = { 'tape'    : [ 1,               4,  False, 'Tape', True],
                      'phono2'  : [ 2,               5,  True, 'Ext Phono', True],
                      'dac'     : [ 3,               6,  False, 'DAC', True],
                      'cd'      : [ 4,               7,  False, 'CD', True],
                      'phono'   : [ 5,               3,  True,  'Phono', True],
                      'streamer': [ 6,               2,  False, 'Streamer', True],
                      'mute'    : [ 7,               1,  False, 'mute', False],
                      'gain'    : [ 8,               0,  False, 'gain', False]
                    }

    POS             = 0   #index to the actualinput position on the Board
    PIN             = 1   #index to the I2C1 chip PIN to control this item
    GAINSTATE       = 2
    SOURCETEXT      = 3
    SIGNAL          = 4

    OFF             = False
    ON              = True
    MUTE            = OFF
    UNMUTE          = ON
    PHONES_IN       = 0
    DEFAULT_SOURCE  = 'tape'

    i2c1_port       = 1
    address         = 0x20
    PHONESDETECTPIN = 12

    GAINONDB        = 25
    GAINOFFDB       = 12

    def __init__(self, events):
        self.events = events
        self.State  = {  'source'       : AudioBoard.DEFAULT_SOURCE,
                         'phonesdetect' : AudioBoard.OFF,
                         'mute'         : AudioBoard.OFF,
                         'gain'         : AudioBoard.OFF }
        self.i2c1 = PCF8574(AudioBoard.i2c1_port, AudioBoard.address)
        Source.__init__(self)

        """ run through the channels and set up the relays"""
        for source in AudioBoard.audioBoardMap:
            print("AudioBoard.__init__> channel:", AudioBoard.audioBoardMap[source])
            self.i2c1.port[ AudioBoard.audioBoardMap[source][AudioBoard.PIN] ] = AudioBoard.OFF

        """ setup the headphones insert detect control """
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(AudioBoard.PHONESDETECTPIN, GPIO.IN)
        GPIO.add_event_detect(AudioBoard.PHONESDETECTPIN, GPIO.BOTH, callback=self.phonesdetect)

        """ set up the default source and unmute """
        self.setSource(self.State['source'])

        print("AudioBoard.__init__ > ready", self.audiostatus())

    @property
    def muteState(self):
        return self.State['mute']

    @property
    def gainState(self):
        return self.State['gain']

    @property
    def phonesdetectState(self):
        return self.State['phonesdetect']

    @property
    def gaindB(self):
        if self.gainState:
            return AudioBoard.GAINONDB
        else:
            return AudioBoard.GAINOFFDB

    @property
    def chid(self):
        return AudioBoard.audioBoardMap[self.activeSource.curr][AudioBoard.POS]

    def chLogic(self):
        logic = {}
        for source in AudioBoard.audioBoardMap:
            logic.update({AudioBoard.audioBoardMap[source][AudioBoard.POS]: source})
        print("AudioBoard.chLogic > ", logic)
        return logic

    def setSource(self, source):
        """ Set the HW to switch on the source selected"""
        self.i2c1.port[ AudioBoard.audioBoardMap[ self.State['source']][AudioBoard.PIN] ] = AudioBoard.OFF
        self.i2c1.port[ AudioBoard.audioBoardMap[source][AudioBoard.PIN] ] = AudioBoard.ON
        self.gain(AudioBoard.audioBoardMap[source][AudioBoard.GAINSTATE] )

        print("AudioBoard.setSource > switch from ", self.State['source'], "to ", source, "pin", AudioBoard.audioBoardMap[source][AudioBoard.PIN], self.i2c1.port)
        print("AudioBoard.setSource > status: ", self.State)
        self.State['source'] = source

    def mute(self):
        """ Mute the audio board"""
        self.State['mute'] = AudioBoard.ON
        self.i2c1.port[ AudioBoard.audioBoardMap['mute'][AudioBoard.PIN] ] = AudioBoard.MUTE
        print("AudioBoard.mute ")

    def unmute(self):
        """ unmute the audio board"""
        self.State['mute'] = AudioBoard.OFF
        self.i2c1.port[ AudioBoard.audioBoardMap['mute'][AudioBoard.PIN] ] = AudioBoard.UNMUTE
        print("AudioBoard.unmute ")

    def invertMute(self, volume):
        """ unmute the audio board"""
        if self.State['mute'] == AudioBoard.ON and volume > 0:
            self.unmute()
        elif self.State['mute'] == AudioBoard.OFF and volume == 0:
            self.mute()

    def gain(self, on=True):
        """ Mute the audio board"""
        if on:
            self.State['gain'] = AudioBoard.ON
            self.i2c1.port[ AudioBoard.audioBoardMap['gain'][AudioBoard.PIN] ] = AudioBoard.ON
        else:
            self.State['gain'] = AudioBoard.OFF
            self.i2c1.port[ AudioBoard.audioBoardMap['gain'][AudioBoard.PIN] ] = AudioBoard.OFF
        print("AudioBoard.gain > ", self.State['gain'])

    def phonesdetect(self,ev):
        """ phonesdetect pin has triggered an interupt """
        if GPIO.input(AudioBoard.PHONESDETECTPIN) == AudioBoard.PHONES_IN:
            self.State['phonesdetect'] = True
            self.events.Platform('phones_in')
            print("AudioBoard.phonesdetect> Headphones insert detected")
        else:
            self.State['phonesdetect'] = False
            print("AudioBoard.phonesdetect> Headphones removed")
            self.events.Platform('phones_out')

    def readAudioBoardState(self):
        return self.State

    def audiostatus(self):
        return "AudioBoard> state %s, active %s, ports %s" % (self.State, self.activeSource, self.i2c1.port)

""" Class to manage lists eg of menu items or sources to find previous and next items """
class ListNext:
    def __init__(self, list, startItem):
        self._list = list
        self._curr = startItem

    def findItemIndex(self, item):
        for index, element in enumerate(self._list):
            if element == item: return index
        raise ValueError("ListNext.findItemIndex> item not found in list", item, self._list)

    @property
    def curr(self):
        return self._curr

    @curr.setter
    def curr(self, v):
        if v in self._list:
            self._curr = v
        else:
            raise ValueError("ListNext.curr> item not found in list", v, self._list)

    @property
    def prev(self):
        i = self.findItemIndex(self._curr)
        if i > 0:
            self.curr = self._list[i-1]
        else:
            self.curr = self._list[-1]
        return self.curr

    @property
    def next(self):
        i = self.findItemIndex(self._curr)
        if i < len(self._list)-1:
            self.curr =  self._list[i+1]
        else:
            self.curr =  self._list[0]
        return self.curr

    def __str__(self):
        return "list>%s, current>%s" % (self._list, self.curr)

class ControlBoard:
    """
    The control board provides 2 functions:
        1. Shutdown/Reboot detects
        2. Source controller rotary input
    """
    # Define GPIO inputs for shutdowna and rotary encoder : in BCM NOT pins

    OFFDETECTPIN = 23
    off          = 0     # signal sent to Control Board to power off
    PIN_A        = 22 	# Pin 8
    PIN_B        = 27	# Pin 10
    BUTTON       = 17	# Pin 7

    def __init__(self, events):
        self.events = events
        """ set up the button shutdown """
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(ControlBoard.OFFDETECTPIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(ControlBoard.OFFDETECTPIN, GPIO.FALLING, callback=self.shutdown)

        """ set up the controller knob events to change the source and menus """
        self.controllerKnob = RotaryEncoder( ControlBoard.PIN_A, ControlBoard.PIN_B, ControlBoard.BUTTON, self.controlKnobEvent )

        print("ControlBoard._init__ > ready")

    def shutdown(self,event):
        print("ControlBoard.shutdown > shutdown request received", event)
        self.mute()
        self.events.Shutdown('Shutdown')

    def poweroff(self,event=''):
        print("ControlBoard.poweroff ", event)
        os.system("sudo poweroff")

    def controlKnobEvent(self, event):
        """  Callback routine to handle Control Knob events """
        if event == RotaryEncoder.CLOCKWISE:
            self.events.CtrlTurn('clockwise')
        elif event == RotaryEncoder.ANTICLOCKWISE:
            self.events.CtrlTurn('anticlockwise')
        elif event == RotaryEncoder.BUTTONDOWN:
            self.events.CtrlPress('down')
        elif event == RotaryEncoder.BUTTONUP:
            self.events.CtrlPress('up')


class RemoteController:
    """
        The IR receiver device is managed by the system lirc Module
        this is configured to use a particular remote control.

        This class abstracts lirc and is used to poll for Remote controller
        button presses and raise events accordingly

    """
    def __init__(self, events):
        self.events = events
        """ set up the button shutdown """
        SOCKPATH = "/var/run/lirc/lircd"

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        print(('starting up IR receiver on socket %s' % SOCKPATH))
        self.sock.connect(SOCKPATH)
        self.sock.setblocking(True)

        print("RemoteController._init__ > ready")

    def checkRemoteKeyPress(self):
        '''Get the next key pressed. raise events accordingly
        '''
        try:
            while True:
                data = self.sock.recv(128)
                #print("Data: " + data)
                data = data.strip()
                if data:
                    break

            words = data.split()
            print ("checkRemoteKeyPress ", words[2], words[1])
            return words[2], words[1]
            '''  using the sequence number removes all key re-trigger '''

            if words[2]   == "KEY_MUTE" and words[1] == "00":
                self.events.RemotePress('mute')
            elif words[2] == "KEY_VOLUMEUP":
                self.events.RemotePress('volume_up')
            elif words[2] == "KEY_VOLUMEDOWN":
                self.events.RemotePress('volume_down')
            elif words[2] == "KEY_POWER" and words[1] == "00":
                self.events.Shutdown('mute')
            elif words[2] == "KEY_LEFT" and words[1] == "00":
                self.events.CtrlTurn('anticlockwise')
            elif words[2] == "KEY_RIGHT" and words[1] == "00":
                self.events.CtrlTurn('clockwise')
            elif words[2] == "KEY_STOP" and words[1] == "00":
                self.events.CtrlPress('down')


        except:
            return 'no','happened'
            # this will cause "Error 11 - resource unavailable - if nothing pressed"

class VolumeBoard(PCF8574):
    i2c2_port    = 1
    i2c2_address = 0x21
    OFF          = False
    ON           = True

    """ Volume Control Rotary Encoder on the Volume Board """
    PIN_A        = 26
    PIN_B        = 16
    BUTTON       = 13

    VOLUMESTEPS  = 7
    MIN_VOLUME   = 0
    MAX_VOLUME   = 127   #""" NB: this is 2xdB """
    DEFAULT_VOL  = 100

    """ Map of the volume relay step to the i2c pin """
    # RELAYMAP     = ( 3, 2, 1, 7, 6, 5, 4)
    # RELAYMAP     = ( 7, 1, 2, 3, 6, 5, 4)
    RELAYMAP       = ( 0, 1, 2, 3, 4, 5, 6)

    def __init__(self, events):
        self.i2c2         = PCF8574(VolumeBoard.i2c2_port, VolumeBoard.i2c2_address)
        self.volknob      = RotaryEncoder(VolumeBoard.PIN_A, VolumeBoard.PIN_B, VolumeBoard.BUTTON, self.volKnobEvent )
        self.demandVolume = VolumeBoard.DEFAULT_VOL
        self.Volume       = VolumeBoard.DEFAULT_VOL
        self.premuteVolume= VolumeBoard.DEFAULT_VOL
        self.events       = events

        """ run through the channels and set up the relays"""
        for i in range(len(self.i2c2.port)):
            self.i2c2.port[ i ] = VolumeBoard.OFF

        """ set up the default volume """
        self.setVolume(VolumeBoard.DEFAULT_VOL)

        print("VolumeBoard._init__ > ready", self.i2c2.port)

    def volKnobEvent(self, a):
        """ callback if the vol knob is turned or the button is pressed """
        """ ** Need to decide whether the volume write can be done in the interrupt? """
        if a == RotaryEncoder.CLOCKWISE:
            if self.demandVolume < VolumeBoard.MAX_VOLUME: self.demandVolume +=1
            self.events.VolTurn('vol_change')
        elif a == RotaryEncoder.ANTICLOCKWISE:
            if self.demandVolume > VolumeBoard.MIN_VOLUME: self.demandVolume -=1
            self.events.VolTurn('vol_change')
        elif a == RotaryEncoder.BUTTONUP:
            self.ev = 'Button up'
        elif a == RotaryEncoder.BUTTONDOWN:
            self.events.VolTurn('mute_change')
            if self.Volume == VolumeBoard.MIN_VOLUME:
                # unmute
                self.demandVolume = self.premuteVolume
            else:
                # mute
                self.premuteVolume = self.Volume
                self.demandVolume = VolumeBoard.MIN_VOLUME

        # if self.demandVolume == 0: self.demandVolume = 1
        # self.setVolume(self.demandVolume)
        print("VolumeBoard.volKnobEvent > **check timing for interrupt update**", a, self.demandVolume)

    def detectVolChange(self):
        """ use as part of the main loop to detect and implement volume changes """
        if self.Volume != self.demandVolume:
            self.setVolume(self.demandVolume)
            return True
        else:
            return False

    def detectMuteChange(self):
        """ use as part of the main loop to detect and implement volume changes """
        if self.ev == 'Button down' and self.demandVolume == VolumeBoard.MIN_VOLUME:
            return 'mute'
        elif self.ev == 'Button down' and self.demandVolume != VolumeBoard.MIN_VOLUME:
            return 'unmute'
        else:
            return 'false'

    def setVolume(self, volume):
        """ algorithm to set the volume steps in a make before break sequence to reduce clicks
            1. need to convert the demand volume into pattern of relays to switch
            2. need to go through a pattern of turn on's, then turn off's to minimise clicks
        """
        """ volume to relays: map integer into bits, map bits to i2c2 ports """
        relays = [False] * VolumeBoard.VOLUMESTEPS
        mask   = 0x01
        for i in range(VolumeBoard.VOLUMESTEPS):
            # print(mask, volume & mask)
            relays[i] = (volume & mask == mask)
            mask = mask << 1


        """ set the relays accordingly, NB: this does NOT attempt on/off optimisation """
        for i, r in enumerate(relays):
            self.i2c2.port[ VolumeBoard.RELAYMAP[i] ] = r

        self.Volume = volume
        print("VolumeBoard.setVolume> demand %d, volume %d, \nVolumeBoard.setVolume>steps %s, \nVolumeBoard.setVolume>ports %s" % (self.demandVolume, self.Volume, relays, self.i2c2.port))

    def readVolume(self):
        return self.Volume


class HWInterface(VolumeBoard, AudioBoard, ControlBoard, RemoteController):  #subclass so that there is only 1 interface point to all the HW classes
    def __init__(self, events):
        VolumeBoard.__init__(self, events)
        ControlBoard.__init__(self, events)
        AudioBoard.__init__(self, events)
        RemoteController.__init__(self, events)

        """ consider whether group together the data pull requests?
            especially is the polling for vol change does not work well """
        # self.toggleMute()

"""
    test code for remote control
"""
if __name__ == '__main__':

    e = Events(( 'Shutdown', 'CtrlPress', 'CtrlTurn', 'VolPress', 'VolTurn', 'VolPress', 'Pause', 'Start', 'Stop'))

    """ ir controller test code """
    irRemote = RemoteController(e)

    while True:
        keyname, updown = irRemote.checkRemoteKeyPress()
        # if keyname != "no":
        #     print('%s (%s)' % (keyname, updown))


    """ Volume knob test code """
    v = VolumeBoard()

    while True:
        v.detectVolChange()
        time.sleep(0.1)
