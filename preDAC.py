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

from hwplatform import Platform, ListNext
from frames import *


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
        for r, t in timer_class.Table.items():
            # print "Timer.checkTimers> timer", r, t['starttime'] + t['duration'], time.time()
            if t['starttime'] > 0 and time.time() >= t['starttime'] + t['duration']:
                t['starttime'] = 0
                t['callback'](t['event'][0])

    @classmethod
    def cancel_all(timer_class):
        for r, t in timer_class.Table.items():
            t['starttime'] = 0

    def __str__(self):
        print("Timer.Table.__str__> ")
        for t in Timer.Table:
            print(Timer.Table[t]['name'])
    #
    # def __repr__(self):
    # 	print "Timer.Table> ",


class Controller:
    """ Main control logic managing events and callbacks """
    # timer constants
    volchangeTime = 2.0
    srcChangeTime = 2.0
    iconMoveTime  = 0.2
    menuTime      = 7.0
    welcomeTime   = 3.0
    screensaveTime= 6.0
    shutdownTime  = 1.0   # slight pause to ensure the shutdown screen is displayed
    trackchangeTime= 7.0
    recordTime    = 7.0

    loopdelay     = 0.0001

    def __init__(self, test_mode=False):
        self.test_mode = test_mode

        """ Setup the events """
        self.events          = Events(( 'Platform', 'CtrlTurn', 'CtrlPress', 'VolKnob', 'Audio', 'RemotePress', 'Streamer'))

        """ Setup the HW, Displays and audio processing """
        self.platform = Platform(self.events)
        if test_mode:
            display = self.platform.internaldisplay  # this is used in test modes
        else:
            display = self.platform.frontdisplay

        """ Setup the Timer events """
        self.volChangeTimer  = Timer(Controller.volchangeTime, self.VolumeChange,  ['stopVol'], 'volChangeTimer' )
        self.srcChangeTimer  = Timer(Controller.srcChangeTime, self.SourceChange, ['stopCtrl'], 'srcChangeTimer' )
        self.iconMoveTimer   = Timer(Controller.iconMoveTime, self.MoveIcon, ['iconTimeout'] , 'iconMoveTimer')
        self.menuTimer       = Timer(Controller.menuTime, self.MenuAction, ['endmenu'] , 'menuTimer')
        self.screensaveTimer = Timer(Controller.screensaveTime, self.ScreenSave, ['start_screensave'] , 'screensaveTimer')
        self.welcomeTimer    = Timer(Controller.welcomeTime, self.Welcomed, ['welcomeTimeout'], 'welcomeTimer' )
        self.shutdownTimer   = Timer(Controller.shutdownTime, self.platform.poweroff, ['shutdownTimeout'], 'shutdownTimer' )
        self.trackChangeTimer= Timer(Controller.trackchangeTime, self.StreamerAction, ['trackNotified'], 'trackChangeTimer')
        self.recordTimer     = Timer(Controller.recordTime, self.AudioAction, ['recordNotified'], 'recordTimer')

        """ Setup the event callbacks """
        self.events.VolKnob      += self.VolumeChange    # when the volume knob, remote or switch is changed
        self.events.CtrlTurn     += self.SourceChange    # when the control knob, remote or switch is pressed
        self.events.CtrlPress    += self.MenuAction      # when when the control knob is pressed start the menu options
        self.events.Platform     += self.PlatformAction  # when the system detects a change to be acted on , eg Shutdown
        self.events.RemotePress  += self.RemoteAction    # when the remote controller is pressed
        self.events.Audio        += self.AudioAction     # respond to a new sample, or audio silence
        self.events.Streamer     += self.StreamerAction     # respond to a new sample, or audio silence



        """Set up the screen for inital Mode"""
        self.baseScreen     = 'spectrum'
        self.preScreenSaver = self.baseScreen

        """ Set up the screen objects to be used """
        self.screens    = {}  # dict for the screen objects
        self.screenList = {'main'         : { 'class' : MainScreen, 'base' : 'yes', 'title' : '1/3 Oct Spectrum Analyser, Dial & source' },
                           'start'        : { 'class' : WelcomeScreen, 'base' : 'no', 'title' : 'welcome' },
                           'volChange'    : { 'class' : VolChangeScreen, 'base' : 'no', 'title' : 'Incidental volume change indicator' },
                           # 'fullSpectrum' : { 'class' : FullSpectrumScreen, 'base' : 'yes', 'title' : '1/6 Octave Spectrum Analyser' },
                           #'StreamerMeta' : { 'class' : PlayerScreen, 'base' : 'yes', 'title' : 'Track data, volume and source' },
                           #'trackChange'  : { 'class' : TrackScreen, 'base' : 'no', 'title' : 'New Track data' },
                           'stereoSpectrum' :{'class' : StereoSpectrumScreen, 'base' : 'yes', 'title' : 'Stereo Spectrum Analyser' },
                           'VUMeters'     : { 'class' : MetersAScreen, 'base' : 'yes', 'title' : 'Stereo VU Meters' },
                           'shutdown'     : { 'class' : ShutdownScreen, 'base' : 'no', 'title' : 'end' },
                           'sourceVol'    : { 'class' : SourceVolScreen,'base' : 'no', 'title' : 'Source Icons & Volume Dial' },
                           'screenTitle'  : { 'class' : ScreenTitle, 'base' : 'no', 'title' : 'Displays screen titles for menu' },
                           'screenSaver'  : { 'class' : ScreenSaver, 'base' : 'no', 'title' : 'all gone quiet' },
                           'sourceVUVol'  : { 'class' : SourceVUVolScreen, 'base' : 'yes', 'title' : ' Source Icons, VU & Vol Dial' },
                           'spectrum'     : { 'class' : SpectrumScreen, 'base' : 'yes', 'title' : ' left channel spectrum and volume'},
                           'VUScreen'     : { 'class' : VUScreen, 'base' : 'yes', 'title' : ' horizontal VU'},
                           'VUVertScreen' : { 'class' : VUVScreen, 'base' : 'yes', 'title' : ' vertical VU'},
                           'RecordScreen' : { 'class' : RecordingScreen, 'base' : 'no', 'title' : ' recording'},
                           'recordFinishScreen' : { 'class' : RecordFinishScreen, 'base' : 'no', 'title' : ' record_end'}
                           }

        for i, (name, c) in enumerate(self.screenList.items()):
            print(("Controller.__init__> screen %s %s" % (name,c)))
            self.screens.update( {name : c['class'](self.platform, display) })
            print(("Controller.__init__> screen %s initialised OK" % name))

        """ Menu functionality """
        self.menuMode = False
        menuSequence = []
        for name, c in self.screenList.items():
            if c['base'] == 'yes':
                menuSequence.append( name )
        self.screenmenu = ListNext(menuSequence, self.baseScreen)


        print("Controller.__init__> all OK", self.screenmenu)


    def startAction(self):
        self.welcomeTimer.start()
        self.setScreen('start')
        self.audioready = 0
        self.platform.start_hw()

    def stopAction(self):
        self.platform.stop()


    def checkScreen(self, basis):
        """ return the current screen object to run """
        Timer.checkTimers()
        if self.menuMode:
            self.screens['screenTitle'].draw( basis, self.screenList[self.activeScreen]['title'] )
        return self.screens[self.activeScreen]

    def setScreen(self, s):
        self.activeScreen = s

    def VolumeChange(self, e='startVol'):
        if e == 'vol_change':
            self.volChangeTimer.start()
            self.activeScreen= 'volChange'
            self.platform.detectVolChange()

        elif e =='stopVol':
            self.activeScreen= self.baseScreen

        elif e =='mute':
            self.platform.mute()   #mute the audio board

        elif e =='unmute':
            self.platform.unmute() #unmute the audio board

        elif e =='togglemute':
            self.platform.invertMute() #unmute the audio board

        elif e =='Button up':
            #detected that the mute button has raised - no action
            pass
        else:
            print("Controller.setVolumeChange> unknown event", e)

    def RemoteAction(self, e):
        print("Controller.RemoteAction: received event<%s>" % e)
        if e == 'volume_up':
            self.platform.volumeUp()

        elif e =='volume_down':
            self.platform.volumeDown()

        elif e =='mute':
            self.platform.toggleMute()

        elif e == 'shutdown':
            self.PlatformAction('shutdown')

        elif e =='forward':
            self.events.CtrlTurn('clockwise')

        elif e =='back':
            self.events.CtrlTurn('anticlockwise')

        elif e =='stop':
            self.events.CtrlPress('down')

        elif e =='pause':
            self.platform.streamerpause()

        elif e =='record':
            if self.platform.recordingState:
                self.platform.stop_recording()
            else:
                self.activeScreen= 'RecordScreen'
                self.platform.start_recording()

        else:
            print("Controller.RemoteAction> unknown event <%s>" % e)

    def MoveIcon(self,e):
        if self.activeScreen== 'sourceVol' or self.activeScreen== 'sourceVUVol':
            # print "MoveIcon>", e, self.activeScreen
            if  e == 'iconTimeout':
                self.platform.nextIcon()
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
            # self.platform.mute()
            self.platform.nextSource()

        elif e == 'anticlockwise':
            self.activeScreen= 'sourceVol'
            self.MoveIcon('startIcons')  # get the icons moving is not already
            self.srcChangeTimer.start()
            self.events.CtrlPress -= self.MenuAction
            # self.platform.mute()
            self.platform.prevSource()

        elif e =='stopCtrl':
            self.activeScreen      = self.baseScreen
            self.events.CtrlPress += self.MenuAction

        else:
            print("Controller.SourceChange>  unknown event", e)

    def Welcomed(self, e):
        self.activeScreen= self.baseScreen

    def ScreenSave(self, e):
        print("Platform: ScreenSave: event %s, screen %s" % (e,self.activeScreen))
        if   e == 'time_screensave':
            if not self.screensaveTimer.is_alive():
                self.screensaveTimer.start()
        elif e == 'cancel_screensave':
            self.screensaveTimer.cancel()
            if self.activeScreen == 'screenSaver':
                self.activeScreen   = self.preScreenSaver
        elif e == 'start_screensave':
            if self.activeScreen != 'screenSaver':
                self.preScreenSaver = self.activeScreen
                self.activeScreen = 'screenSaver'
        else:
            print(("Platform: ScreenSave: event not recognised ", e))

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
            # print "Controller.MenuAction> prev screen", self.activeScreen
        if   e == 'clockwise':
            self.menuTimer.start()
            self.menuNext()
            self.MoveIcon('startIcons')  # get the icons moving is not already
            # print "Controller.MenuAction> next screen", self.activeScreen

    def AudioAction(self, e):
        if e == 'silence_detected':
            self.platform.mute()
            self.ScreenSave('time_screensave')

        elif e == 'signal_detected':
            self.platform.unmute()
            self.ScreenSave('cancel_screensave')

        elif e == 'capture':
            # if self.audioready>0:
            #     print("Controller.AudioAction> %d sample buffer underrun, dump old data " % self.audioready)
            self.platform.process()
            self.audioready +=1

        elif e == 'recording_stopped':
            self.recordTimer.start()
            self.activeScreen= 'recordFinishScreen'

        elif e == 'recordNotified':
            self.activeScreen= self.baseScreen

        else:
            print("Controller.AudioAction> unknown event ",e)


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

    def menuPrev(self):
        self.baseScreen   = self.screenmenu.prev
        self.activeScreen = self.baseScreen
        print("Controller.menuPrev> active screen %s" % (self.activeScreen))
        return self.screenmenu.curr

    def menuNext(self):
        self.baseScreen   = self.screenmenu.next
        self.activeScreen = self.baseScreen
        print("Controller.menuPrev> active screen %s" % (self.activeScreen))
        return self.screenmenu.curr

    def SystemChange(self, e='error'):
        print("Controller.SystemChange> event ", e)

    def PlatformAction(self, e='error'):
        if e == 'shutdown':
            self.activeScreen= 'shutdown'
            Timer.cancel_all()
            self.shutdownTimer.start()
            print("Controller.Platform> event ", e)
        elif e == 'phones_in':
            self.platform.mute()
        elif e == 'phones_out':
            self.platform.unmute()
        elif e == 'exit':
            exit()  # this is a debug mode to terminate execution from the keyboard


    def StreamerAction(self, e):
        print("Controller.StreamerAction> event ", e)
        if e == 'new_track' or e == 'start':
            print("Controller.StreamerAction> new track - pop up display ", e)
            self.trackChangeTimer.start()
            self.activeScreen= 'trackChange'

        elif e == 'stop':
            print("Controller.StreamerAction> track stopped - display nothing new")
            self.platform.clear_track()

        elif e =='trackNotified':
            print("Controller.StreamerAction> track notification timeout")
            self.activeScreen= self.baseScreen

        else:
            print("Controller.StreamerAction> unknown event ", e)



    """
        This is where execution starts..
            configure the HW & Display objects
            set up the event handling which controls the display Mode(ie which screen)
            run the Display in an infinite loop
    """
    def run(self):

        print("Controller.run> preDAC startup configured at ", time.gmtime())
        self.startAction()
        self.audioready = 0

        t = time.time()

        """ loop around updating the screen and responding to events """
        while(True):
            # self.platform.captureAudio()      # should become event driven
            """ return the current screen object to run """
            Timer.checkTimers()
            self.platform.checkKeys()
            if self.platform.nohw: self.audioready = 1

            if self.audioready>0:
                screen = self.screens[self.activeScreen]

                if self.test_mode:
                    self.platform.internaldisplay.draw(screen)     # this will just be the diagnostics in time
                    # self.platform.internaldisplay.draw_status(self.platform.volume_db, \
                    #     self.platform.activeSourceText, \
                    #     self.platform.chid, \
                    #     self.platform.muteState, self.platform.gainState, self.platform.phonesdetectState)    # this will just be the diagnostics in time


                else:
                    self.platform.frontdisplay.draw(screen)
                    # if self.platform.internaldisplay is not None:
                    #     self.platform.internaldisplay.draw_status(self.platform.volume_db, \
                    #         self.platform.activeSourceText, \
                    #         self.platform.chid, \
                    #         self.platform.muteState, self.platform.gainState, self.platform.phonesdetectState)    # this will just be the diagnostics in time

                self.audioready = 0

                # print("run> waited for audio: waited", 1000*(time.time()-t))
                t = time.time()
            else:
                # print("run> waiting for audio: waited", 1000*(time.time()-t))
                time.sleep(Controller.loopdelay)

        print("Controller.run> terminated")

def cb( e):
    print("Timer> test callback with event ", e)

if __name__ == "__main__":
    try:
        logic = Controller(test_mode=False)
        logic.run()

    except KeyboardInterrupt:
        logic.stopAction()
