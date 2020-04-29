#!/usr/bin/env python
"""
    preDAC Test harness

    Main test harness for testing the preDAC HW
    uses the core classes and wraps in a user interface
    for testing the HW board

    baloothebear4 April 2020

"""
    
from smbus2 import SMBus
import time, sys
import struct, math
import numpy as np


import datetime

from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from luma.core.sprite_system import framerate_regulator

import processaudio
from pcf8574 import PCF8574


class OLEDbar():
    oled_height = 32
    oled_width  = 128
    bottom      = oled_height
    top         = 0
    bar_width   = 3
    bar_gap     = 2
    bar_space   = bar_gap + bar_width
    bars        = oled_width / bar_space

    def __init__(self):
        serial = i2c(port=1, address=0x3c)
        self.device = ssd1306(serial, height=32)
        self.device.persist = True
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
        with canvas(self.device) as draw:
            for j in range(OLEDbar.bars):
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
                OLED.draw_bar2(c,1,1)
                OLED.draw_bar2(c,3,10)
                OLED.draw_bar2(c,25,32)



class Volume(PCF8574):
    i2c_port = 1
    address  = 0x20
    mute_in  = 0
    dBout32  = 1
    dBout16  = 2
    dBout8   = 3
    dBout4   = 4
    dBout2   = 5
    dBout1   = 6
    testLEDout = 0

    def __init__(self):
        PCF8574.__init__(self, Volume.i2c_port, Volume.address)

    def printPorts(self):
        print "Volume.printPorts> ", self.port

    def test1(self):
        for i in range (0,8):
            self.port[i]= True
            print "set pin ", i , ' read ', self.port[i]
            time.sleep(0.3)
            self.printPorts()
            self.port[i]= False

    def test(self,i):
        self.send(i)
        a = self.read()
        print "send ", i , ' read ', a


    def blink(self):
        for _ in range(10):
            self.port[Volume.testLEDout]= True
            self.printPorts()
            time.sleep(1)
            self.port[Volume.testLEDout]= False
            self.printPorts()


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

def main():
    '''
    Test harness for the i2c and 2 display classes
    '''

    OLED = OLEDbar()
    V   = Volume()
    V.test1()
    V.blink()
    return

    # OLED.test_oled2()


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
