#!/usr/bin/env python
"""

 HW Test package

 Part of mVista preDAC

 v1.0 Baloothebear4 Jul  20

"""


from events import Events
import time

from platform import Platform, ListNext

import sys, select
def GetLine():
    while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        line = sys.stdin.readline()
        if line:
          return line[:-1]
        else: # an empty line means stdin has been closed
          return False

class HWTest:
    def __init__(self):
        test_mode = False
        self.e = Events(( 'Platform', 'CtrlTurn', 'CtrlPress', 'VolKnob', 'Audio', 'RemotePress', 'Streamer'))

        """ Setup the event callbacks """
        self.e.VolKnob      += self.VolumeChange    # when the volume knob, remote or switch is changed
        self.e.CtrlTurn     += self.SourceChange    # when the control knob, remote or switch is pressed
        self.e.CtrlPress    += self.defaultAction      # when when the control knob is pressed start the menu options
        self.e.Platform     += self.PlatformAction  # when the system detects a change to be acted on , eg Shutdown
        self.e.RemotePress  += self.RemoteAction    # when the remote controller is pressed
        self.e.Audio        += self.AudioAction     # respond to a new sample, or audio silence
        self.e.Streamer     += self.StreamerAction     # respond to a new sample, or audio silence

        self.platform = Platform(self.e)


        if test_mode:
            self.display = self.platform.internaldisplay  # this is used in test modes
        else:
            self.display = self.platform.frontdisplay

            self.platform.powerAudio('on')

    def defaultAction(self,e):
        print("HWTest.defaultAction>  event", e)

    def VolumeChange(self, e='startVol'):
        print("VolumeChange>  event", e)
        if e == 'vol_change':
            self.platform.detectVolChange()

        elif e =='mute':
            self.platform.mute()   #mute the audio board

        elif e =='unmute':
            self.platform.unmute() #unmute the audio board


    def RemoteAction(self, e):
        print("RemoteAction: received event<%s>" % e)
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

        elif e =='play':
            self.platform.streamerplay()

        else:
            print("Controller.RemoteAction> unknown event <%s>" % e)


    def SourceChange(self, e):
        print("SourceChange>  event", e)
        if   e == 'clockwise':
            self.platform.nextSource()

        elif e == 'anticlockwise':
            self.platform.prevSource()


    def AudioAction(self, e):
        print("AudioAction>  event ",e)
        if e == 'silence_detected':
            self.platform.mute()

        elif e == 'signal_detected':
            self.platform.unmute()

        elif e == 'capture':
            # if self.audioready>0:
            #     print("Controller.AudioAction> %d sample buffer underrun, dump old data " % self.audioready)
            self.platform.process()
            self.audioready +=1

    def PlatformAction(self, e='error'):
        print("PlatformAction> event ", e)


    def StreamerAction(self, e):
        print("Controller.StreamerAction> event ", e)
        if e == 'new_track' or e == 'start':
            print("Controller.StreamerAction> new track - pop up display ", e)

        elif e == 'stop':
            print("Controller.StreamerAction> track stopped - display nothing new")
            self.platform.clear_track()

        elif e =='trackNotified':
            print("Controller.StreamerAction> track notification timeout")



    """ use the platform API to test each of the HW functions """

    def main(self):

        logic   = self.platform.sourceLogic()
        chlogic = self.platform.chLogic()
        status  = self.platform.readAudioBoardState()

        chchanged = True   # display status first time around
        while True:

            line = GetLine()
            if line:

                print("pressed>",line)
                if line == "q":
                    return
                elif line >= "0"  and line <= "5":
                    ch   = int(line)
                    print("Channel=", ch, " source=", logic[ch])
                    self.platform.setSource(logic[ch])
                    chchanged = True
                elif line == "g":
                    self.platform.gain(not status['gain'])
                    chchanged = True
                elif line == "m":
                    self.platform.volKnobEvent(RotaryEncoder.BUTTONDOWN)
                    chchanged = True
                elif line == "s":
                    print("AudioBoard>", self.platform.readAudioBoardState())
                    chchanged = True

            self.display.draw_status(self.platform.volume_db, \
                self.platform.activeSourceText, \
                self.platform.chid, \
                self.platform.muteState, self.platform.gainState, self.platform.phonesdetectState)    # this will just be the diagnostics in time

            time.sleep(0.005)



if __name__ == "__main__":
    try:
        h = HWTest()
        h.main()
    except KeyboardInterrupt:
        pass
