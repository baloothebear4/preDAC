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

from oleddriver   import internalOLED, frontOLED
from processaudio import AudioProcessor
from keyevents    import KeyEvent   # used for testing without all HW attached
from rotenc       import RotaryEncoder
from rotary       import RotaryEncoder2
from pcf8574      import PCF8574
from streamerif   import StreamerInterface

from events       import Events
from threading    import Thread
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
                    'phono'     : ["Phono 0.png", "Phono 60.png", "Phono 120.png", "Phono 180.png", "Phono 240.png", "Phono 300.png"]  }

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
    audioBoardMap = { 'dac'     : [ 1,               4,  False, 'DAC', True],
                      'cd'      : [ 2,               5,  False, 'CD', True],
                      'tape'    : [ 3,               6,  False, 'Tape', True],
                      'aux'     : [ 4,               7,  False, 'Aux', True],
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
    DEFAULT_SOURCE  = 'dac'

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
        self.streamersource(source)

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

    def invertMute(self):
        """ unmute the audio board"""
        if self.State['mute'] == AudioBoard.ON:
            self.unmute()
        elif self.State['mute'] == AudioBoard.OFF:
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
        return "AudioBoard> state %s, active %s, \n            ports %s" % (self.State, self.activeSource, self.i2c1.port)

class ControlBoard:
    """
    The control board provides 2 functions:
        1. Shutdown/Reboot detects
        2. Source controller rotary input
    """
    # Define GPIO inputs for shutdowna and rotary encoder : in BCM NOT pins

    OFFDETECTPIN = 23
    POWERRELAYSPIN= 26
    off          = 0     # signal sent to Control Board to power off
    # LHS Knob
    # PIN_A        = 27 	# Pin 10
    # PIN_B        = 22	# Pin 8
    # BUTTON       = 17	# Pin 7

    # RHS Knob
    # PIN_A        = 16
    # PIN_B        = 26
    # BUTTON       = 13
    KNOBS        = { 'RHS': [16, 7, 13, '/dev/input/event1'], \
                     'LHS': [27, 22, 17, '/dev/input/event0'] }
    PIN_A        = 0
    PIN_B        = 1
    BUTTON       = 2
    DEVICE       = 3
    ON           = 1
    OFF          = 0
    POWER        = { 'on' : ON, 'off': OFF}
    VOL_KNOB     = 'RHS'
    CTRL_KNOB    = 'LHS'

    def __init__(self, events):
        self.events = events

        """ set up the button shutdown """
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(ControlBoard.OFFDETECTPIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(ControlBoard.OFFDETECTPIN, GPIO.FALLING, callback=self.shutdown)

        """ set up the controller knob events to change the source and menus """
        self.controllerKnob = RotaryEncoder2( ControlBoard.KNOBS[ControlBoard.CTRL_KNOB], self.controlKnobEvent, (-10,10,0) )

        """ setup the Relay control PIN """
        GPIO.setup(ControlBoard.POWERRELAYSPIN, GPIO.OUT)

        print("ControlBoard.__init__ > ready")

    def powerAudio(self, state='off'):
        print("ControlBoard.powerAudio > request received", state)
        GPIO.output(ControlBoard.POWERRELAYSPIN, ControlBoard.POWER[state])

    def shutdown(self, event):
        print("ControlBoard.shutdown > shutdown request received", event)
        self.mute()
        self.events.Platform('shutdown')

    def poweroff(self,event=''):
        print("ControlBoard.poweroff ", event)
        self.stop_capture()
        os.system("sudo poweroff")

    def controlKnobEvent(self, event):
        """  Callback routine to handle Control Knob events """
        print("ControlBoard.controlKnobEvent> event %d" % (event))
        if event == RotaryEncoder.CLOCKWISE:
            self.events.CtrlTurn('clockwise')
        elif event == RotaryEncoder.ANTICLOCKWISE:
            self.events.CtrlTurn('anticlockwise')
        elif event == RotaryEncoder.BUTTONDOWN:
            self.events.CtrlPress('down')
        elif event == RotaryEncoder.BUTTONUP:
            self.events.CtrlPress('up')



class RemoteController():
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
        print('starting up IR receiver on socket %s, %s' % (SOCKPATH, events.RemotePress))
        self.sock.connect(SOCKPATH)
        self.sock.setblocking(True)

        # self.start()
        """ as key events block, run as a separate thread """
        self.remote_running = True
        self.remote = Thread(target=self.checkRemoteKeyPress)
        self.remote.start()
        print("RemoteController._init__ > ready")

    def run(self):
        self.checkRemoteKeyPress()
        print("RemoteController.run > exit")

    def remotestop(self):
        self.remote_running = False

    def checkRemoteKeyPress(self):
        '''Get the next key pressed. raise events accordingly
        '''
        while self.remote_running:
            try:
                # print ("checkRemoteKeyPress> wait for remote key press ")
                data = self.sock.recv(128)    # blocked wait for keypress
                data = data.strip().decode('UTF-8')

                words = data.split()
                print ("checkRemoteKeyPress ", words[2], words[1])
                '''  using the sequence number removes all key re-trigger '''

                if words[2]   == "KEY_MUTE" and words[1] == "00":
                    self.events.RemotePress('mute')
                elif words[2] == "KEY_VOLUMEUP":
                    self.events.RemotePress('volume_up')
                elif words[2] == "KEY_VOLUMEDOWN":
                    self.events.RemotePress('volume_down')
                elif words[2] == "KEY_POWER" and words[1] == "00":
                    self.events.RemotePress('shutdown')
                elif words[2] == "KEY_LEFT" and words[1] == "00":
                    self.events.RemotePress('back')
                elif words[2] == "KEY_RIGHT" and words[1] == "00":
                    self.events.RemotePress('forward')
                elif words[2] == "KEY_STOP" and words[1] == "00":
                    self.events.RemotePress('stop')
                elif words[2] == "KEY_PAUSE" and words[1] == "00":
                    self.events.RemotePress('pause')
                    # print("RemoteController.checkRemoteKeyPress> pause key pressed, no linked event")
                elif words[2] == "KEY_PLAY" and words[1] == "00":
                    # print("RemoteController.checkRemoteKeyPress> play key pressed, no linked event")
                    self.events.RemotePress('play')
            # else:
            #     print("RemoteController.checkRemoteKeyPress> key press not recognised ",words[2], words[1] )

            # return words[2], words[1]
            except Exception as e:
                print("RemoteController.checkRemoteKeyPress> exception", e)
                time.sleep(1)
                break
            #print "no key"
            # return "no", "key"
                pass

    def RemoteAction(self, e):
        print('RemoteController> Remote Keypress: event %s' % e)


""" Data model for all volume related items """
class Volume():
    def __init__(self):
        # self.gaindB          = read_gain   #callback to find gain setting True
        self.demandVolume    = VolumeBoard.DEFAULT_VOL
        self.volume_raw      = VolumeBoard.DEFAULT_VOL # this is the -0.5 x the dB attenuation, + the gain + 12dB is the total
        self.premuteVolume   = VolumeBoard.DEFAULT_VOL

    @property   #volume as a percentage
    def volume(self):
        return self.volume_raw/VolumeBoard.MAX_VOLUME

    @property
    def volume_db(self):
        return 0.5*(self.volume_raw-VolumeBoard.MAX_VOLUME) + self.gaindB


class VolumeBoard(PCF8574, Volume):
    i2c2_port    = 1
    i2c2_address = 0x21
    OFF          = False
    ON           = True

    """ Volume Control Rotary Encoder on the Volume Board """
    # PIN_A        = 16
    # PIN_B        = 26
    # BUTTON       = 13

    # KNOBS are defined in the ControlBoard class
    # PIN_A        = 27 	# Pin 10
    # PIN_B        = 22	# Pin 8
    # BUTTON       = 17	# Pin 7

    VOLUMESTEPS  = 7
    MIN_VOLUME   = 0
    MAX_VOLUME   = 127   #""" NB: this is 2xdB """
    DEFAULT_VOL  = 51
    HWSETTLETIME = 0.6   #after powering up the Volume and Source select relays, let them settle

    """ Map of the volume relay step to the i2c pin """
    RELAYMAP       = ( 0, 1, 2, 3, 4, 5, 6)

    def __init__(self, events):
        self.i2c2         = PCF8574(VolumeBoard.i2c2_port, VolumeBoard.i2c2_address)
        self.volknob      = RotaryEncoder2(ControlBoard.KNOBS[ControlBoard.VOL_KNOB], self.volKnobEvent,\
                                (VolumeBoard.MIN_VOLUME, VolumeBoard.MAX_VOLUME, VolumeBoard.DEFAULT_VOL))
        Volume.__init__(self)   # volume data model
        self.events       = events

        """ run through the channels and set up the relays"""
        for i in range(len(self.i2c2.port)):
            self.i2c2.port[ i ] = VolumeBoard.OFF

        print("VolumeBoard._init__ > ready", self.volumestatus())

    def volKnobEvent(self, event):
        """ callback if the vol knob is turned or the button is pressed """

        if event == RotaryEncoder.CLOCKWISE:
            if self.demandVolume < VolumeBoard.MAX_VOLUME: self.demandVolume +=1
            self.events.VolKnob('vol_change')

        elif event == RotaryEncoder.ANTICLOCKWISE:
            if self.demandVolume > VolumeBoard.MIN_VOLUME: self.demandVolume -=1
            self.events.VolKnob('vol_change')

        elif event == RotaryEncoder.BUTTONUP:
            pass

        elif event == RotaryEncoder.BUTTONDOWN:
            self.events.VolKnob('togglemute')
            # if self.volume_raw == VolumeBoard.MIN_VOLUME:
            #     # unmute
            #     self.demandVolume = self.premuteVolume
            #     self.events.VolKnob('vol_change')
            # else:
            #     # mute
            #     self.premuteVolume = self.volume_raw
            #     self.demandVolume = VolumeBoard.MIN_VOLUME
            #     self.events.VolKnob('vol_change')

        print("VolumeBoard.volKnobEvent >", event, self.demandVolume)

    def volumeUp(self):
        self.volKnobEvent(RotaryEncoder.CLOCKWISE)

    def volumeDown(self):
        self.volKnobEvent(RotaryEncoder.ANTICLOCKWISE)

    def toggleMute(self):
        self.volKnobEvent(RotaryEncoder.BUTTONDOWN)

    def detectVolChange(self):
        """ use as part of the main loop to detect and implement volume changes """
        if self.volume_raw != self.demandVolume:
            self.setVolume(self.demandVolume)
            self.detectMuteChange()
            return True
        else:
            return False


    def detectMuteChange(self):
        """ use as part of the main loop to detect and implement volume changes """
        if self.demandVolume == VolumeBoard.MIN_VOLUME:
            self.events.VolKnob('mute')
        else:
            self.events.VolKnob('unmute')


    def setVolume(self, volume):
        """ algorithm to set the volume steps in a make before break sequence to reduce clicks
            1. need to convert the demand volume into pattern of relays to switch
            2. need to go through a pattern of turn on's, then turn off's to minimise clicks
        """
        """ volume to relays: map integer into bits, map bits to i2c2 ports """
        if volume > VolumeBoard.MAX_VOLUME or volume < VolumeBoard.MIN_VOLUME:
            print("VolumeBoard.setVolume> error volume demand out of range", volume)
            return

        relays = [False] * VolumeBoard.VOLUMESTEPS
        mask   = 0x01
        for i in range(VolumeBoard.VOLUMESTEPS):
            # print(mask, volume & mask)
            relays[i] = (volume & mask == mask)
            mask = mask << 1


        """ set the relays accordingly, NB: this does NOT attempt on/off optimisation """
        for i, r in enumerate(relays):
            self.i2c2.port[ VolumeBoard.RELAYMAP[i] ] = r

        self.volume_raw = volume
        print("VolumeBoard.setVolume> demand %d, volume %d, \nVolumeBoard.setVolume>steps %s, \nVolumeBoard.setVolume>ports %s" % (self.demandVolume, self.volume_raw, relays, self.i2c2.port))

    def volumestatus(self):
        return "VolumeBoard> vol %f, vol_dB %f, ports %s" % (self.volume, self.volume_db, self.i2c2.port)

class Platform(VolumeBoard, ControlBoard, AudioBoard, \
                    RemoteController, AudioProcessor, StreamerInterface, KeyEvent):
    """ this is the HW abstraction layer and includes the device handlers and data model """
    def __init__(self, events):
        """ start the displays """
        try:
            self.internaldisplay   = internalOLED()
        except Exception as e:
            self.internaldisplay   = None
            print("Platform.__init__> failed to start internal display ", e)

        try:
            self.frontdisplay      = frontOLED()
        except Exception as e:
            self.frontdisplay = None
            print("Platform.__init__> failed to start front display ", e)

        """ setup all the HW drivers and interfaces """
        if self.internaldisplay is not None:
            hwifs = (ControlBoard, AudioBoard, VolumeBoard, AudioProcessor, KeyEvent, RemoteController, StreamerInterface)
            for hw in hwifs:
                try:
                    hw.__init__(self, events)
                except Exception as e:
                    print("Platform.__init__> failed to start %s > %s" % (hw.__name__, e))
            self.nohw = False



            print("Platform.__init__>\n", self)

        else:
            """ this is a test mode """
            self.activeSource       = ListNext(['dac','cd','tape'],'dac')
            self.screenName         = "description of current screen"
            data                    = [0.5]*50
            import numpy as np
            data_r                  = np.arange(2048)
            data_l                  = np.arange(50)
            self.vu                 = {'left': 0.5, 'right':0.6}
            self.peak               = {'left': 0.8, 'right':0.9}
            self.spectrum           = {'left': data, 'right':data}
            self.bins               = {'left': data_l, 'right':data_r}
            self.State  = {  'source'       : AudioBoard.DEFAULT_SOURCE,
                             'phonesdetect' : AudioBoard.OFF,
                             'mute'         : AudioBoard.OFF,
                             'gain'         : AudioBoard.OFF }
            self.nohw               = True
            Source.__init__(self)
            Volume.__init__(self)
            RemoteController.__init__(self, events)
            ControlBoard.__init__(self, events)
            KeyEvent.__init__(self, events)
            print("Platform.__init__> in test mode")

    def start_hw(self):
        self.powerAudio('on')
        time.sleep(Platform.HWSETTLETIME)

        """ set up the default volume """
        self.setVolume(VolumeBoard.DEFAULT_VOL)
        """ set up the default source and unmute if signal detected """
        self.setSource(self.State['source'])
        self.start_capture()


    def stop(self):
        self.powerAudio('off')
        self.stop_capture()
        self.remotestop()
        self.streamerstop()

    def __str__(self):
        text = " >> Displays:"
        if self.internaldisplay is not None:
            text += type(self.internaldisplay).__name__
        if self.frontdisplay is not None:
            text += " , %s" % type(self.frontdisplay).__name__
        text+= "\n %s\n" % self.audiostatus()
        text+= " %s\n" % self.volumestatus()
        text+= " %s" % self.processstatus()
        return text

# end Platform

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

"""
    test code for remote control
"""
def RemoteAction(e):
    print('Remote Keypress: event %s' % e)


if __name__ == '__main__':

    e = Events(( 'Platform', 'CtrlTurn', 'CtrlPress', 'VolKnob', 'Audio', 'RemotePress'))

    c = ControlBoard(e)
    print("Power up")
    c.powerAudio('on')
    time.sleep(3)
    print("Power down")
    c.powerAudio('off')

    #
    # try:
    #     """ ir controller test code """
    #     irRemote = RemoteController(e)
    #
    #     e.RemotePress  += RemoteAction    # when the remote controller is pressed
    #     irRemote.run()
    #     e.RemotePress('test')
    #
    #     while True:
    #         # keyname, updown = irRemote.checkRemoteKeyPress()
    #         # if keyname != "no":
    #         #     print('%s (%s)' % (keyname, updown))
    #         time.sleep(0.01)
    #
    # except KeyboardInterrupt:
    #     pass

    # """ Volume knob test code """
    # v = VolumeBoard()
    #
    # while True:
    #     v.detectVolChange()
    #     time.sleep(0.1)


""" test code for ListNext object """
# if __name__ == '__main__':
#     l = ['a','bb','ccc','dddd','eeeee']
#     a = ListNext(l, 'bb')
#     print(l)
#     print (" curr %s next %s prev %s " % (a.curr, a.next, a.prev))
#     a.prev
#     a.prev
#     a.prev
#     a.prev
#     print (" curr %s next %s prev %s " % (a.curr, a.next, a.prev))
#     a.next
#     a.next
#     a.next
#     print (" curr %s next %s prev %s " % (a.curr, a.next, a.prev))
# if __name__ == '__main__':
#     a = AudioBoard()
