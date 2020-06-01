#!/usr/bin/env python
"""
 preDAC preamplifier project

Test class to generate events from keystrokes eg to emulate hardware

 Baloothebear4
 v2 May  20 - new

"""

import sys, select
from events import Events

class KeyEvent:
    def __init__(self, events):
        self.events = events

    def GetLine(self):
        while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline()
            if line:
              return line[:-1]
            else: # an empty line means stdin has been closed
              return False


    def checkKeys(self):
        line = self.GetLine()
        if line:

            if line   == "m" :
                self.events.RemotePress('mute')
            elif line   == "n" :
                self.events.RemotePress('unmute')    
            elif line == "u":
                self.events.RemotePress('volume_up')
            elif line == "d":
                self.events.RemotePress('volume_down')
            elif line == "q" :
                self.events.Platform('shutdown')
            elif line == "l" :
                self.events.CtrlTurn('anticlockwise')
            elif line == "r" :
                self.events.CtrlTurn('clockwise')
            elif line == "p" :
                self.events.CtrlPress('down')
            elif line == "s" :
                print (self)
            elif line >= "1"  and line <= "6":
                self.setSource( self.sourceLogic()[int(line)])
