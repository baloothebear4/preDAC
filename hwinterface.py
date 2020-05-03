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

import RPi.GPIO as GPIO
import os, time, socket

class AudioBoard:  #subclass so that there is only 1 interface point to all the HW classes
    """                source   board relay,   i2c1 pin ref, gain state, text """
    audioBoardMap = { 'tape'    : [ 1,               4,  False, 'tape'],
                      'cd'      : [ 2,               5,  False, 'cd'],
                      'dac'     : [ 3,               6,  False, 'dac'],
                      'aux'     : [ 4,               7,  False, 'aux'],
                      'phono'   : [ 5,               3,  True,  'phono'],
                      'streamer': [ 6,               2,  False, 'streamer'],
                      'mute'    : [ 7,               1,  False, 'mute'  ],
                      'gain'    : [ 8,               0,  False, 'gain'  ]
                    }
    POS             = 0   #index to the actualinput position on the Board
    PIN             = 1   #index to the I2C1 chip PIN to control this item
    GAINSTATE       = 3
    SOURCETEXT      = 4

    OFF             = False
    ON              = True
    MUTE            = OFF
    UNMUTE          = ON
    PHONES_IN       = 0

    i2c1_port       = 1
    address         = 0x20
    PHONESDETECTPIN = 12

    def __init__(self):
        self.State  = {  'active'       : 'dac',
                         'phonesdetect' : AudioBoard.OFF,
                         'mute'         : AudioBoard.OFF,
                         'gain'         : AudioBoard.OFF }
        self.i2c1   = PCF8574(AudioBoard.i2c1_port, AudioBoard.address)

        """ run through the channels and set up the relays"""
        for source in AudioBoard.audioBoardMap:
            print "AudioBoard.__init__> channel:", AudioBoard.audioBoardMap[source]
            self.i2c1.port[ AudioBoard.audioBoardMap[source][AudioBoard.PIN] ] = AudioBoard.OFF

        """ setup the headphones insert detect control """
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(AudioBoard.PHONESDETECTPIN, GPIO.IN)
        GPIO.add_event_detect(AudioBoard.PHONESDETECTPIN, GPIO.BOTH, callback=self.phonesdetect)

        """ set up the default source and unmute """
        self.setSource(self.State['active'])

        print "AudioBoard._init__ > ready", self.i2c1.port

    def sourceLogic(self):
        logic = {}
        for s in AudioBoard.audioBoardMap:
            if s != 'mute' and s != 'gain':
                logic.update({s: AudioBoard.audioBoardMap[s][AudioBoard.POS]})
        print "AudioBoard.sourceLogic > ", logic
        return logic

    def chLogic(self):
        logic = {}
        for source in AudioBoard.audioBoardMap:
            logic.update({AudioBoard.audioBoardMap[source][AudioBoard.POS]: source})
        print "AudioBoard.chLogic > ", logic
        return logic

    def setSource(self, source):
        """ Set the HW to switch on the source selected"""
        self.i2c1.port[ AudioBoard.audioBoardMap[ self.State['active']][AudioBoard.PIN] ] = AudioBoard.OFF
        self.i2c1.port[ AudioBoard.audioBoardMap[source][AudioBoard.PIN] ] = AudioBoard.ON

        print "AudioBoard.setSource > switch from ", self.State['active'], "to ", source, "pin", AudioBoard.audioBoardMap[source][AudioBoard.PIN], self.i2c1.port
        print "AudioBoard.setSource > status: ", self.State
        self.State['active'] = source

    def mute(self):
        """ Mute the audio board"""
        self.State['mute'] = AudioBoard.ON
        self.i2c1.port[ AudioBoard.audioBoardMap['mute'][AudioBoard.PIN] ] = AudioBoard.MUTE
        print "AudioBoard.mute "

    def unmute(self):
        """ unmute the audio board"""
        self.State['mute'] = AudioBoard.OFF
        self.i2c1.port[ AudioBoard.audioBoardMap['mute'][AudioBoard.PIN] ] = AudioBoard.UNMUTE
        print "AudioBoard.unmute "

    def toggleMute(self, volume):
        """ unmute the audio board"""
        if self.State['mute'] == AudioBoard.ON and volume > 0:
            self.unmute()
        elif self.State['mute'] == AudioBoard.OFF and volume == 0:
            self.mute()
        print "AudioBoard.togglemute "

    def phonesdetect(self):
        """ phonesdetect pin has triggered an interupt """
        if GPIO.input(AudioBoard.PHONESDETECTPIN) == AudioBoard.PHONES_IN:
            self.State['phonesdetect'] = True
            print "AudioBoard.phonesdetect> Headphones insert detected"
        else:
            self.State['phonesdetect'] = False
            print "AudioBoard.phonesdetect> Headphones removed"

    def readAudioBoardState(self):
        return self.State

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

        print "ControlBoard._init__ > ready"

    def shutdown(self,event):
        print "ControlBoard.shutdown > shutdown request received", event
        self.mute()
        self.events.Shutdown('Shutdown')

    def poweroff(self,event=''):
        print "ControlBoard.poweroff ", event
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
        print ('starting up IR receiver on socket %s' % SOCKPATH)
        self.sock.connect(SOCKPATH)
        self.sock.setblocking(False)

        print "RemoteController._init__ > ready"

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
            # print "checkRemoteKeyPress ", words[2], words[1]
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


            #return words[2], words[1]
        except:
            #print "no key"
            #return "no", "key"
            pass

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
    DEFAULT_VOL  = 20

    """ Map of the volume relay step to the i2c pin """
    # RELAYMAP     = ( 3, 2, 1, 7, 6, 5, 4)
    # RELAYMAP     = ( 7, 1, 2, 3, 6, 5, 4)
    RELAYMAP       = ( 0, 1, 2, 3, 4, 5, 6)

    def __init__(self):
        self.i2c2         = PCF8574(VolumeBoard.i2c2_port, VolumeBoard.i2c2_address)
        self.volknob      = RotaryEncoder(VolumeBoard.PIN_A, VolumeBoard.PIN_B, VolumeBoard.BUTTON, self.volKnobEvent )
        self.demandVolume = VolumeBoard.DEFAULT_VOL
        self.Volume       = VolumeBoard.DEFAULT_VOL
        self.premuteVolume= VolumeBoard.DEFAULT_VOL
        self.ev           = "none"

        """ run through the channels and set up the relays"""
        for i in range(len(self.i2c2.port)):
            self.i2c2.port[ i ] = VolumeBoard.OFF

        """ set up the default volume """
        self.setVolume(VolumeBoard.DEFAULT_VOL)

        print "VolumeBoard._init__ > ready", self.i2c2.port

    def volKnobEvent(self, a):
        """ callback if the vol knob is turned or the button is pressed """
        """ ** Need to decide whether the volume write can be done in the interrupt? """
        if a == RotaryEncoder.CLOCKWISE:
            if self.demandVolume < VolumeBoard.MAX_VOLUME: self.demandVolume +=1
            self.ev = 'Clockwise'
        elif a == RotaryEncoder.ANTICLOCKWISE:
            if self.demandVolume > VolumeBoard.MIN_VOLUME: self.demandVolume -=1
            self.ev = 'Anti-clockwise'
        elif a == RotaryEncoder.BUTTONUP:
            self.ev = 'Button up'
        elif a == RotaryEncoder.BUTTONDOWN:
            self.ev = 'Button down'
            if self.Volume == VolumeBoard.MIN_VOLUME:
                # unmute
                self.demandVolume = self.premuteVolume
            else:
                # mute
                self.premuteVolume = self.Volume
                self.demandVolume = VolumeBoard.MIN_VOLUME

        # if self.demandVolume == 0: self.demandVolume = 1
        print "VolumeBoard.volKnobEvent >", self.ev, self.demandVolume

    def detectVolChange(self):
        """ use as part of the main loop to detect and implement volume changes """
        if self.Volume <> self.demandVolume:
            self.setVolume(self.demandVolume)
            return True
        else:
            return False

    def detectMuteChange(self):
        """ use as part of the main loop to detect and implement volume changes """
        if self.ev == 'Button down' and self.demandVolume == VolumeBoard.MIN_VOLUME:
            return 'mute'
        elif self.ev == 'Button down' and self.demandVolume <> VolumeBoard.MIN_VOLUME:
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
            print mask, volume & mask
            relays[i] = (volume & mask == mask)
            mask = mask << 1


        """ set the relays accordingly, NB: this does NOT attempt on/off optimisation """
        for i, r in enumerate(relays):
            self.i2c2.port[ VolumeBoard.RELAYMAP[i] ] = r

        self.Volume = volume
        print "VolumeBoard.setVolume> demand %d, volume %d, \nsteps %s, \nports %s" % (self.demandVolume, self.Volume, relays, self.i2c2.port)

    def readVolume(self):
        return self.Volume


class HWInterface(VolumeBoard, AudioBoard, ControlBoard, RemoteController):  #subclass so that there is only 1 interface point to all the HW classes
    def __init__(self,events):
        VolumeBoard.__init__(self, events)
        ControlBoard.__init__(self, events)
        AudioBoard.__init__(self)
        RemoteController.__init__(self, events)


"""
    test code for remote control
"""
if __name__ == '__main__':
    from events import Events
    e = Events(( 'Shutdown', 'CtrlPress', 'CtrlTurn', 'VolPress', 'VolTurn', 'VolPress', 'Pause', 'Start', 'Stop'))

    """ ir controller test code
    irRemote = RemoteController(e)

    while True:
        keyname, updown = irRemote.checkRemoteKeyPress()
        if keyname != "no":
            print('%s (%s)' % (keyname, updown))
    """

    """ Volume knob test code """
    v = VolumeBoard()

    while True:
        v.detectVolChange()
        time.sleep(0.1)
