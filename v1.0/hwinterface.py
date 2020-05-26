#!/usr/bin/env python
"""
 HW interface class
    - controls the interaction with the HW driver objects:
        volumeBoard
        audioBoard
        controlBoard
        controllerKnob

 Part of mVista preDAC

 Baloothebear4 Sept 17


"""


from volumeboard import VolumeBoard
from rotary_class import RotaryEncoder

import RPi.GPIO as GPIO
import os, time, socket

class AudioBoard:  #subclass so that there is only 1 interface point to all the HW classes
                # name         logicalposition, pin ref
    audioBoardMap = { 'mute'    : [ 0,                5],
                      'streamer': [ 0,               20],
                      'rec'     : [ 1,               26],
                      'cd'      : [ 2,               16],
                      'dac'     : [ 3,               13],
                      'aux'     : [ 4,               12],
                      'phono'   : [ 5,                6]
                    }
    POS    = 0   #index to the actualinput position on the Board
    PIN    = 1   #index to the GPIO PIN to control this item

    OFF    = 0
    ON     = 1
    MUTE   = 0
    UNMUTE = 1

    def __init__(self):
        self.muteState    = AudioBoard.MUTE
        self.active       = 'dac'

        """ run through the sources and set up the GPIO pins"""
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        for p in AudioBoard.audioBoardMap:
            GPIO.setup(  AudioBoard.audioBoardMap[p][AudioBoard.PIN], GPIO.OUT)
            GPIO.output( AudioBoard.audioBoardMap[p][AudioBoard.PIN], AudioBoard.OFF)

        """ set up the default source and unmute """
        self.setSource(self.active)
        # self.unmute()
        print "AudioBoard._init__ > ready"

    def sourceLogic(self):
        logic = {}
        for s in AudioBoard.audioBoardMap:
            if s != 'mute':
                logic.update({s: AudioBoard.audioBoardMap[s][AudioBoard.POS]})
        # print "AudioBoard.sourceLogic > ", logic
        return logic

    def setSource(self, source):
        """ Set the HW to switch on the source selected"""
        GPIO.output(AudioBoard.audioBoardMap[self.active][AudioBoard.PIN], AudioBoard.OFF)
        # print "AudioBoard.setSource >", self.active, AudioBoard.audioBoardMap[self.active][AudioBoard.PIN], AudioBoard.OFF
        GPIO.output(AudioBoard.audioBoardMap[source][AudioBoard.PIN], AudioBoard.ON)

        # print "AudioBoard.setSource > switch from ", self.active, "to source ", source
        self.active = source

    def mute(self):
        """ Mute the audio board"""
        self.muteState    = AudioBoard.MUTE
        GPIO.output(AudioBoard.audioBoardMap['mute'][AudioBoard.PIN], AudioBoard.MUTE)
        # print "AudioBoard.mute "

    def unmute(self):
        """ unmute the audio board"""
        self.muteState    = AudioBoard.UNMUTE
        GPIO.output(AudioBoard.audioBoardMap['mute'][AudioBoard.PIN], AudioBoard.UNMUTE)
        # print "AudioBoard.unmute "

    def changeMute(self):
        """ unmute the audio board"""
        if self.muteState == AudioBoard.MUTE:
            self.unmute()
        else:
            self.mute()
        # print "AudioBoard.togglemute "

    def readAudioBoardMuteState(self):
        return self.muteState


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

    irRemote = RemoteController(e)

    while True:
        keyname, updown = irRemote.checkRemoteKeyPress()
        if keyname != "no":
            print('%s (%s)' % (keyname, updown))
