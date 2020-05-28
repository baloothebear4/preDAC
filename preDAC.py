#!/usr/bin/env python
"""

    preDAC is the top level package which instantiates the main classes
    and implements the control logic

 Part of mVista preDAC

 v1.0 Baloothebear4 Sept 17
 v2.0 Baloothebear4 May  20

"""


from events import Events
import time

from platform import Platform
from frames import *

# # logging
# logging.basicConfig(
#     level=logging.DEBUG,
#     format='%(asctime)-15s - %(message)s'
# )
# # ignore PIL debug messages
# logging.getLogger("PIL").setLevel(logging.ERROR)

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


class Controller():
    """ Main control logic managing events and callbacks """
    # timer constants
    volchangeTime = 2.0
    srcChangeTime = 2.0
    iconMoveTime  = 0.2
    menuTime      = 3.0
    welcomeTime   = 3.0
    screensaveTime= 6.0
    shutdownTime  = 1.0   # slight pause to ensure the shutdown screen is displayed

    loopdelay     = 0.0001

    def __init__(self):

        """ Setup the HW, Displays and audio processing """
        self.platform      = Platform()
        self.int_disp      = self.platform.internaldisplay
        self.front_display = self.platform. frontdisplay

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
                           'sourceVUVol'  : { 'class' : SourceVUVolScreen, 'base' : 'yes', 'title' : ' Source Icons, VU & Vol Dial' },
                           'spectrum'     : { 'class' : SpectrumScreen, 'base' : 'yes', 'title' : ' left channel spectrum and volume'},
                           'VUScreen'     : { 'class' : VUScreen, 'base' : 'yes', 'title' : ' horizontal VU'},
                           'VUVertScreen' : { 'class' : VUVScreen, 'base' : 'yes', 'title' : ' vertical VU'}
                           }
        for name, c in self.screenList.enumerate():
            self.screens.update( {name : c['class'](self) })
            print("Platform.__init__> screen %s initialised OK" % name)

        """ Menu functionality """
        self.menuMode = False
        self.menuSequence = {}
        pos = 0
        for name, c in self.screenList.enumerate():
            if c['base'] == 'yes':
                self.menuSequence.update( {name : pos })
                pos += 1

        print "Platform.__init__> all OK"



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



    """
        This is where execution starts..
            configure the HW & Display objects
            set up the event handling which controls the display Mode(ie which screen)
            run the Display in an infinite loop
    """
    def run():

        print ("Controller.run> preDAC startup configured at ", time.gmtime(t))

        """ loop around updating the screen and responding to events """
        while(True):
            self.platform.captureAudio()      # should become event driven
            screen = logic.checkScreen(basis) # this is a consequence of an event
            self.checkRemoteKeyPress()        # should become event driven
            self.int_display.draw(screen)     # this will just be the diagnostics in time
            self.front_display.draw(screen)
            time.sleep(Platform.loopdelay)

        print("Controller.run> terminated")

def cb( e):
    print "Timer> test callback with event ", e

if __name__ == "__main__":
    try:
        logic = Controller()
        logic.run()

    except KeyboardInterrupt:
    # except :
    #     print "Restarting..."
