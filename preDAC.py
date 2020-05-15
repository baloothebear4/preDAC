#!/usr/bin/env python
"""
 Display classes:
    - base screens
    - screen classes & object mangement
    - display driver control

 Part of mVista preDAC

 Baloothebear4 Sept 17
 test


"""

# ToDo
#  - object placement
#  - spectrum analyser
#  - mVista integration
#  - menus


from hwinterface import HWInterface
from octave import Octave
from screenobjs import *

import os
import sys
import random
import RPi.GPIO as GPIO
from events import Events
from PIL import ImageFont

from luma.core.render import canvas
from luma.core.sprite_system import framerate_regulator

import logging
import time

from luma.core import cmdline, error

# logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)-15s - %(message)s'
)
# ignore PIL debug messages
logging.getLogger("PIL").setLevel(logging.ERROR)

class Timer:
    """
    A custom Timer class which is non-threaded is developed to work with the
    luma screen handling timing interaction.  This is to make Timers more stable
    """
    Table = {}
    ref   = 0      # Unique timer reference
    Alive = 1
    Dead  = 0

    def __init__(self, duration, callback, event, name):
        """ new Timers are added to the Timer Table """
        self.ref = Timer.ref
        Timer.Table.update( {self.ref : { 'duration': float(duration), 'callback' : callback, 'event' : event, 'starttime' : 0, 'name':name }} )
        """ NB non-zero start time means a timer is running """
        Timer.ref += 1
        # print "Timer.__init__> new timer", self.ref, name

    def start(self):
        """ resets and starts a timer """
        Timer.Table[self.ref]['starttime'] = time.time()
        # print "Timer.start>", self.ref, Timer.Table[self.ref]['name'], Timer.Table[self.ref]['starttime']

    def cancel(self):
        """ cancels a Timer.  Does nothing if the Timer is not started."""
        # print "Timer.cancel>", self.ref, Timer.Table[self.ref]['name']
        Timer.Table[self.ref]['starttime'] = 0
        # print "Timer.cancel>", self.ref

    def is_alive(self):
        """ checks if a Timer has already been started but has not expired"""
        if Timer.Table[self.ref]['starttime'] > 0:
            return Timer.Alive
        else:
            return Timer.Dead

    @classmethod
    def checkTimers(timer_class):
        """ this should be called every screen refresh peroid and will update the Timer Table
        and call Timer events if a Timer has expired """
        for r, t in timer_class.Table.iteritems():
            # print "Timer.checkTimers> timer", r, t['starttime'] + t['duration'], time.time()
            if t['starttime'] > 0 and time.time() >= t['starttime'] + t['duration']:
                t['starttime'] = 0
                t['callback'](t['event'][0])

    @classmethod
    def cancel_all(timer_class):
        for r, t in timer_class.Table.iteritems():
            t['starttime'] = 0

    def __str__(self):
        print "Timer.Table.__str__> "
        for t in Timer.Table:
            print Timer.Table[t]['name']
    #
    # def __repr__(self):
    # 	print "Timer.Table> ",




class Source:
    """
    Management of the source types

    NB: Sources are mapped to audioBoard control logical controls 0 - 5
    """

    IconFiles = {   'streamer'  : ["streamer.png"],
                    'dac'       : ["dac.png"],
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



class Platform(Source, HWInterface):
    config        = ['-i=spi', '--width=256', '-d=ssd1322', '--spi-bus-speed=2000000']   # this is the base data for the OLED configuration
    refreshRate   = 30 # max fps
    volchangeTime = 2.0
    srcChangeTime = 2.0
    iconMoveTime  = 0.2
    menuTime      = 3.0
    welcomeTime   = 3.0
    screensaveTime= 6.0
    shutdownTime  = 1.0   # slight pause to ensure the shutdown screen is displayed
    loopdelay     = 0.0001

    def __init__(self):

        GPIO.setwarnings(False)
        """ Setup the display handling capability"""
        self.device     = self.getDevice( Platform.config )
        self.regulator  = framerate_regulator( fps=Platform.refreshRate )
        print "Platform.__init__> device OK"

        """ Setup the event handling capability """
        self.events         = Events(( 'Shutdown', 'CtrlPress', 'CtrlTurn', 'VolPress', 'VolTurn', 'VolPress', 'RemotePress', 'Pause', 'Start', 'Stop', 'ScreenSaving'))
        HWInterface.__init__(self, self.events)
        Source.__init__(self, self.sourceLogic, self.setSource)

        self.volChangeTimer  = Timer(Platform.volchangeTime, self.VolumeChange,  ['stopVol'], 'volChangeTimer' )
        self.srcChangeTimer  = Timer(Platform.srcChangeTime, self.SourceChange, ['stopCtrl'], 'srcChangeTimer' )
        self.iconMoveTimer   = Timer(Platform.iconMoveTime, self.MoveIcon, ['iconTimeout'] , 'iconMoveTimer')
        self.menuTimer       = Timer(Platform.menuTime, self.MenuAction, ['endmenu'] , 'menuTimer')
        self.screensaveTimer = Timer(Platform.screensaveTime, self.ScreenSave, ['save'] , 'screensaveTimer')
        self.welcomeTimer    = Timer(Platform.welcomeTime, self.Welcomed, ['welcomeTimeout'], 'welcomeTimer' ).start()
        self.shutdownTimer   = Timer(Platform.shutdownTime, self.poweroff, ['shutdownTimeout'], 'shutdownTimer' )


        self.events.VolTurn      += self.VolumeChange    # when the volume knob, remote or switch is changed
        self.events.CtrlTurn     += self.SourceChange    # when the control knob, remote or switch is pressed
        self.events.CtrlPress    += self.MenuAction      # when when the control knob is pressed start the menu options
        self.events.Shutdown     += self.ShutdownAction  # when the system detects a change to be acted on , eg Shutdown
        self.events.RemotePress  += self.RemoteAction    # when the remote controller is pressed
        self.events.ScreenSaving += self.ScreenSave

        """Set up the screen for inital Mode"""
        self.baseScreen     = 'main'
        self.activeScreen   = 'start'
        self.preScreenSaver = self.baseScreen

        print "Platform.__init__> events OK"
        """ Set up the screen objects to be used """
        self.screens    = {}  # placeholder for the screen objects
        self.screenList = {'main'         : { 'class' : MainScreen, 'base' : 'yes', 'title' : '1/3 Oct Spectrum Analyser, Dial & source' },
                           'start'        : { 'class' : WelcomeScreen, 'base' : 'no', 'title' : 'welcome' },
                           'volChange'    : { 'class' : VolChangeScreen, 'base' : 'no', 'title' : 'Incidental volume change indicator' },
                           'fullSpectrum' : { 'class' : FullSpectrumScreen, 'base' : 'yes', 'title' : '1/6 Octave Spectrum Analyser' },
                           'shutdown'     : { 'class' : ShutdownScreen, 'base' : 'no', 'title' : 'end' },
                           'sourceVol'    : { 'class' : SourceVolScreen,'base' : 'yes', 'title' : 'Source Icons & Volume Dial' },
                           'screenTitle'  : { 'class' : ScreenTitle, 'base' : 'no', 'title' : 'Displays screen titles for menu' },
                           'screenSaver'  : { 'class' : ScreenSaver, 'base' : 'no', 'title' : 'all gone quiet' },
                           'sourceVUVol'  : { 'class' : SourceVUVolScreen, 'base' : 'yes', 'title' : ' Source Icons, VU & Vol Dial' }
                           }
        for name, c in self.screenList.iteritems():
            self.screens.update( {name : c['class'](self) })
        print "Platform.__init__> screens initialised OK"

        """ Menu functionality """
        self.menuMode = False
        self.menuSequence = {}
        pos = 0
        for name, c in self.screenList.iteritems():
            if c['base'] == 'yes':
                self.menuSequence.update( {name : pos })
                pos += 1



        print "Platform.__init__> all OK"

    def getDevice(self, actual_args=None):
        """
        Create device from command-line arguments and return it.
        """
        if actual_args is None:
            actual_args = sys.argv[1:]
        parser = cmdline.create_parser(description='luma.examples arguments')
        args = parser.parse_args(actual_args)

        if args.config:
            # load config from file
            config = cmdline.load_config(args.config)
            args = parser.parse_args(config + actual_args)

        # create device
        try:
            device = cmdline.create_device(args)
        except error.Error as e:
            parser.error(e)

        return device

    def checkScreen(self, basis):
        """ return the current screen object to run """
        Timer.checkTimers()
        if self.menuMode:
            self.screens['screenTitle'].draw( basis, self.screenList[self.activeScreen]['title'] )
        return self.screens[self.activeScreen]

    def setScreen(self, s):
        self.activeScreen = s

    def VolumeChange(self, e='startVol'):
        if e == 'startVol':
            self.volChangeTimer.start()
            self.activeScreen= 'volChange'

        elif e =='stopVol':
            self.activeScreen= self.baseScreen

        elif e =='mute':
            self.mute()
        elif e =='unmute':
            self.unmute()
        else:
            print "Platform.setVolumeChange> unknown event", e

    def RemoteAction(self, e='volume_up'):
        if e == 'volume_up':
            # print "RemotePress: Calling volume up"
            self.volumeUp()

        elif e =='volume_down':
            # print "RemotePress: calling volume down"
            self.volumeDown()

        elif e =='mute':
            # print "RemotePress: toggle mute"
            self.toggleMute()

        else:
            print "Platform.RemotePress> unknown event", e

    def MoveIcon(self,e):
        if self.activeScreen== 'sourceVol' or self.activeScreen== 'sourceVUVol':
            # print "MoveIcon>", e, self.activeScreen
            if  e == 'iconTimeout':
                self.nextIcon()
                self.iconMoveTimer.start()
            elif e == 'startIcons':
                self.iconMoveTimer.start()
        # else:
        #     self.iconMoveTimer.cancel()

    def SourceChange(self, e):
        if   e == 'clockwise':
            self.activeScreen= 'sourceVol'
            self.MoveIcon('startIcons')  # get the icons moving is not already
            self.srcChangeTimer.start()
            self.events.CtrlPress -= self.MenuAction
            self.mute()
            self.nextSource()

        elif e == 'anticlockwise':
            self.activeScreen= 'sourceVol'
            self.MoveIcon('startIcons')  # get the icons moving is not already
            self.srcChangeTimer.start()
            self.events.CtrlPress -= self.MenuAction
            self.mute()
            self.prevSource()

        elif e =='stopCtrl':
            self.activeScreen      = self.baseScreen
            self.events.CtrlPress += self.MenuAction

        else:
            print "Platform.SourceChange>  unknown event", e

    def Welcomed(self, e):
        self.activeScreen= self.baseScreen

    def ScreenSave(self, e):
        # print("Platform: ScreenSave: event %s, screen %s" % (e,self.activeScreen))
        if   e == 'start':
            if not self.screensaveTimer.is_alive():
                self.screensaveTimer.start()
        elif e == 'stop':
            if self.activeScreen == 'screenSaver':
                self.screensaveTimer.cancel()
                self.activeScreen   = self.preScreenSaver
        elif e == 'save':
            if self.activeScreen != 'screenSaver':
                self.preScreenSaver = self.activeScreen
                self.activeScreen = 'screenSaver'
        else:
            print("Platform: ScreenSave: event not recognised ", e)

    def MenuAction(self, e):
        if   e == 'startmenu':
            self.startMenu()
        elif e == 'down':
            if self.menuMode:
                self.endMenu()
            else:
                self.startMenu()
        elif e == 'endmenu':
            self.endMenu()
        elif e == 'anticlockwise':
            self.menuTimer.start()
            self.menuPrev()
            self.MoveIcon('startIcons')  # get the icons moving is not already
            # print "Platform.MenuAction> prev screen", self.activeScreen
        if   e == 'clockwise':
            self.menuTimer.start()
            self.menuNext()
            self.MoveIcon('startIcons')  # get the icons moving is not already
            # print "Platform.MenuAction> next screen", self.activeScreen

    def startMenu(self):
        self.menuMode   = True
        self.events.CtrlTurn  -= self.SourceChange   #when the control knob or switch is pressed
        self.events.CtrlTurn  += self.MenuAction   #when the control knob or switch is pressed
        self.menuTimer.start()

    def endMenu(self):
        self.menuMode   = False
        self.menuTimer.cancel()
        self.events.CtrlTurn  += self.SourceChange   #when the control knob or switch is pressed
        self.events.CtrlTurn  -= self.MenuAction   #when the control knob or switch is pressed

    def menuNext(self):
        # find the current sequence position, increment and up the active source
        pos = self.menuSequence[self.activeScreen]
        if pos == len(self.menuSequence)-1:
            pos= 0
        else:
            pos += 1
        for s, p in self.menuSequence.iteritems():
            if p == pos:
                self.baseScreen   = s
                self.activeScreen = s
                return s

    def menuPrev(self):
        # find the current sequence position, increment and up the active source
        pos = self.menuSequence[self.activeScreen]
        if pos == 0 :
            pos= len(self.menuSequence)-1
        else:
            pos -= 1
        for s, p in self.menuSequence.iteritems():
            if p == pos:
                self.baseScreen   = s
                self.activeScreen = s
                return s

    def SystemChange(self, e='error'):
        print "Platform.SystemChange> event ", e

    def ShutdownAction(self, e='error'):
        self.activeScreen= 'shutdown'
        Timer.cancel_all()
        self.shutdownTimer.start()
        print "Platform.Shutdown> event ", e


class MainScreen:   # comprises volume on the left, spectrum on the right
    def __init__(self, platform):
        """ create the screen frames """
        self.volumeSource  = VolumeSourceFrame( platform )
        # self.volumeA     = VolumeAmountFrame( platform )

        self.spectrum    = SpectrumFrame( platform, interval=3)

        """ position them """
        # print "MainScreen> align volume source"
        self.volumeSource.alignFrameRight()
        # print "MainScreen> align spectrum"
        self.spectrum.setMaxFrameWidthLeftTo( self.volumeSource )
        self.spectrum.alignLeft()
        # print "MainScreen> spectrum loc", self.spectrum


    def draw(self, basis):
        self.volumeSource.draw(basis)
        self.spectrum.draw(basis)

class ScreenTitle:
    def __init__(self, platform):
        """ create the screen objects """
        self.menu  = MenuFrame( platform)

    def draw(self, basis, text):
        self.menu.draw(basis, text)

class WelcomeScreen:
    text = "      Welcome to \nmVista pre-Amplifier"
    def __init__(self, platform):
        """ create the screen objects """
        self.welcome  = TextFrame( platform, WelcomeScreen.text, 20 )

    def draw(self, basis):
        self.welcome.draw(basis)

class ShutdownScreen:
    text = "Loved the music"
    def __init__(self, platform):
        """ create the screen objects """
        self.platform = platform
        self.shutdown  = TextFrame( platform, ShutdownScreen.text, 30 )

    def draw(self, basis):
        self.platform.mute()
        self.shutdown.draw(basis)

class ScreenSaver:
    def __init__(self, platform):
        """ go blank after a while if everything is quiet """
        # print("ScreenSaver: ")
        self.platform = platform
        self.screensave  = TextFrame( platform, '', 30 )

    def draw(self, basis):
        self.screensave.draw(basis)
        self.platform.readVolume()   #see if anything has happened


class DACScreen:
    def __init__(self, platform):
        """ create the screen frames """
        self.dacScreen  = TextFrame( platform, 'int/ext DAC select', 20 )
        """ position them """

    def draw(self, basis):
        self.dacScreen.draw(basis)

class VolChangeScreen:
    def __init__(self, platform):
        """ create the screen objects """
        self.volume      = VolumeSourceFrame( platform )
        self.volumeA     = VolumeAmountFrame( platform )
        """ position them """
        self.volume.alignFrameRight()
        self.volumeA.alignLeftOf( self.volume )

    def draw(self, basis):
        self.volume.draw(basis)
        self.volumeA.draw(basis)

class SourceVolScreen:   # comprises volume on the left, spectrum on the right
    def __init__(self, platform):
        """ create the screen objects """
        self.volume      = VolumeSourceFrame( platform )
        self.sourceIcon  = SourceIconFrame( platform )

        """ position them """
        self.volume.alignFrameRight()
        self.sourceIcon.setMaxFrameWidthLeftTo( self.volume )
        self.sourceIcon.alignLeft()

    def draw(self, basis):
        self.volume.draw(basis)
        self.sourceIcon.draw(basis)

class SourceVUVolScreen:   # comprises volume on the left, spectrum on the right
    def __init__(self, platform):
        """ create the screen objects """
        self.volume      = VolumeSourceFrame( platform )
        self.sourceIcon  = SourceIconFrame( platform )
        self.vu          = VolumeUnitsFrame( platform )

        """ position them """
        self.volume.alignFrameRight()
        # print "SourceVUVolScreen> align volume to right - vol", self.volume

        self.vu.alignLeftOf( self.volume )
        self.vu.alignLeft()
        # print "SourceVUVolScreen> align vu to left of volume - vu", self.vu

        self.sourceIcon.setMaxFrameWidthLeftTo( self.vu )
        self.sourceIcon.alignLeft()
        # print "SourceVUVolScreen> align vu to left of volume - sourceIcon", self.sourceIcon

    def draw(self, basis):
        self.volume.draw(basis)
        self.sourceIcon.draw(basis)
        self.vu.draw(basis)

class FullSpectrumScreen:   # comprises volume on the left, spectrum on the right
    def __init__(self, platform):
        """ create the screen objects """
        self.spectrum    = SpectrumFrame( platform, interval=6)
        """ position  """

    def draw(self, basis):
        self.spectrum.draw(basis)

def main():
    """
        This is where execution starts..
            configure the HW & Display objects
            set up the event handling which controls the display Mode(ie which screen)
            run the Display in an infinite loop
    """
    print "main > startup"
    p   = Platform()
    t   = time.time()
    l   = 0
    poweredup = True
    print "main> Platform HW configured at ", time.gmtime(t)

    """ loop around updating the screen and responding to events """
    # try:
    while(poweredup):

        with p.regulator:
            with canvas(p.device) as basis:
                screen = p.checkScreen(basis)
                p.checkRemoteKeyPress()
                screen.draw(basis)
                time.sleep(Platform.loopdelay)
                # poweredup = p.is_poweredup()

    print "finished"

def cb( e):
    print "Timer> test callback with event ", e

if __name__ == "__main__":
    main()
    # while (1):
    #     try:
    #         main()
    #
    #
    #     # except KeyboardInterrupt:
    #     except :
    #         print "Restarting..."
