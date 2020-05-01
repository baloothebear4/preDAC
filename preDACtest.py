#!/usr/bin/env python
"""
preDAC Test harness

    Main test harness for testing the preDAC HW
    uses the core classes and wraps in a user interface
    for testing the HW board

baloothebear4
v1 April 2020

"""

from smbus2 import SMBus
import time, sys, os
import struct, math
import numpy as np


import datetime
from PIL import ImageFont, Image
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from luma.core.sprite_system import framerate_regulator

import processaudio
from rotenc import RotaryEncoder
from pcf8574 import PCF8574
from hwinterface import AudioBoard


class OLEDbar():
    oled_height = 32
    oled_width  = 128
    bottom      = oled_height
    top         = 0
    bar_width   = 3
    bar_gap     = 2
    bar_space   = bar_gap + bar_width
    bars        = oled_width / bar_space

    def make_font(self, name, size):
        font_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 'fonts', name))
        return ImageFont.truetype(font_path, size)

    def __init__(self):
        serial = i2c(port=1, address=0x3c)
        self.device = ssd1306(serial, height=32)
        self.device.persist = True
        self.font = self.make_font("arial.ttf", 11)
        print "OLED all set. Max bars = ", OLEDbar.bars
        self.regulator = framerate_regulator(fps=60)
        self.readtime = []
        # self.test_oled()

    def draw_bar(self,col, h):
        with canvas(self.device) as draw:
            draw.rectangle((col, OLEDbar.oled_height-h, col + OLEDbar.bar_width, OLEDbar.bottom), outline="blue", fill="white")
        # print "draw_bar at ", col," ",h
    def draw_line(self,col, h):
        with canvas(self.device) as draw:
            draw.line((col, OLEDbar.oled_height-h, col + OLEDbar.bar_width, OLEDbar.bottom), fill="white")

    def draw_bar2(self,draw, col, h):
        ''' draws up to 32 pixels high, OLED.bar wide '''
        x = col * OLEDbar.bar_space
        draw.rectangle((x, OLEDbar.oled_height-h, x + OLEDbar.bar_width, OLEDbar.bottom), outline="blue", fill="blue")

    def draw_status(self, vol, source, mute, gain, headphonedetect):
        """ simple dignostic to see the current source channel and volume setting """

        states = ""
        if mute: states+= "Mute - "
        if gain: states+= "Gain - "
        if headphonedetect: states+= "H/P detect"

        self.calcDisplaytime()
        with self.regulator:
            with canvas(self.device) as draw:
                draw.text((0,0), text='Volume -%2.1fdB' % (vol/2.0), fill="white", font=self.font)
                draw.text((0,11),text='Channel %d' % source, fill="white",font=self.font)
                draw.text((0,22),text=states, fill="white", font=self.font)

        self.calcDisplaytime(False)

    def draw_screen(self,data):
        self.calcDisplaytime()
        bars = OLEDbar.bars
        if len(data)< OLEDbar.bars: bars = len(data)

        with self.regulator:
            with canvas(self.device) as c:
                for i in range(bars):
                    self.draw_bar2(c, i, data[i]*(40/32.0) )
        self.calcDisplaytime(False)

    def calcDisplaytime(self,start=True):
        if start:
            self.startreadtime = time.time()
        else:
            self.readtime.append(time.time()-self.startreadtime)
            if len(self.readtime)>100: del self.readtime[0]
            print 'OLEDbar:calcDisplaytime> %3.3fms, %3.3f' % (np.mean(self.readtime)*1000, self.readtime[-1])



    def test_oled(self):
        print "OLED test full speed"
        self.device.persist = True
        for i in range(8):
            for j in range(OLEDbar.bars):
                self.draw_bar(i*(OLEDbar.bar_space+10), 32)
                # time.sleep(0.00002)
        print "OLED testing done"
        # time.sleep(4)

    def test_oled2(self):
        print "OLED test full speed"
        with canvas(self.device) as draw:
            for j in range(OLEDbar.bars):
                print "draw at col", j
                for i in range(OLEDbar.oled_height):
                    self.draw_bar2(draw,j*OLEDbar.bar_space+4, i)
                    time.sleep(0.2)

    def test_oled3(self):
        with canvas(self.device) as draw:

            self.draw_bar2(draw,OLEDbar.bar_space+4, 10)
            self.device.persist = True
            self.draw_bar2(draw,OLEDbar.bar_space+40, 20)
                    # time.sleep(0.2)

    def test_oled4(self):
        with self.regulator:
            with canvas(self.device) as c:
                OLEDbar.draw_bar2(c,1,1)
                OLEDbar.draw_bar2(c,3,10)
                OLEDbar.draw_bar2(c,25,32)



loops = 0
BinCount = 24
BlockSize = 32
WordLen   = 2

def testdata(a):
    d = []
    for i in range(0,25):
        d.append(16+i*math.sin(a*30))
    # print d
    return d

MAX = 8
MIN = 1
count=MIN
mute = True
new = True

def buttonpress(a):
    global count,mute, MAX, MIN, new

    if a == RotaryEncoder.CLOCKWISE:
        if count < MAX: count +=1
        ev = 'Clockwise'
    elif a == RotaryEncoder.ANTICLOCKWISE:
        if count > MIN: count -=1
        ev = 'Anti-clockwise'
    elif a == RotaryEncoder.BUTTONUP:
        ev = 'Button up'
    elif a == RotaryEncoder.BUTTONDOWN:
        ev = 'Button down'
        mute = not mute

    new = True
    print "Rot enc event ", ev , count, mute


pinA = 26
pinB = 16
button = 13

def main():
    '''
    Test harness for the i2c and 2 display classes
    '''
    global mute, new
    audio = AudioBoard()
    logic = audio.chLogic()
    print "source logic:", audio.sourceLogic()

    OLED = OLEDbar()
    r = RotaryEncoder(pinA, pinB, button, buttonpress)
    # OLED.test_oled2()
    # for i in range(0,100):
    #     OLED.draw_screen(testdata(i))
    #     time.sleep(0.2)
    # OLED.draw_status(45,3,True,True,True)
    # V   = Volume()
    # V.test1()
    # V.blink()

    loops = 0

    while(loops<1000):
        start = time.time()
        if new:
            print "Count=", count, " source=", logic[count]
            audio.setSource(logic[count])
            if mute:
                audio.mute()
            else:
                audio.unmute()
            OLED.draw_status(0,count,mute,True,True)
            print "Audio board status ", audio.readAudioBoardState()
            new = False
        loops += 1
        time.sleep(.5)
    return



    proc = processaudio.ProcessAudio()
    loops = 0

    while(loops<1000):
        start = time.time()

        loops += 1
        proc.process()
        # proc.printSpectrum()
        # proc._print()
        # print proc.leftCh()

        OLED.draw_screen(proc.leftCh())
        # OLED.draw_screen(testdata(loops))
        # proc._print()

        # print 'pause'
        # time.sleep(.02)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
