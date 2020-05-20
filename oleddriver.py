#!/usr/bin/env python
"""
OLED driver classes

Abstracts over the luma package to create a flexible interface to
different OLED displays on different HW interfaces

baloothebear4

v1. 20 May 2020   Original, based on OLEDbar() class

"""


import time, sys, os



import datetime
from PIL import ImageFont
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from luma.core.sprite_system import framerate_regulator


class OLEDdriver():
    oled_height = 32
    oled_width  = 128
    bottom      = oled_height
    top         = 0
    bar_width   = 3
    bar_gap     = 2
    bar_space   = bar_gap + bar_width
    bars        = int(oled_width / bar_space)

    def make_font(self, name, size):
        font_path = os.path.abspath(os.path.join( os.path.dirname(__file__), 'fonts', name))
        try:
            return ImageFont.truetype(font_path, size)
        except:
            print("OLEDdriver.make_font > error, font files not found at ", font_path)

    def __init__(self):
        serial = i2c(port=1, address=0x3c)
        self.device = ssd1306(serial, height=32)
        self.device.persist = True
        self.font = self.make_font("arial.ttf", 11)
        print("OLEDdriver.__init__> all set. Max bars = ", OLEDdriver.bars)
        self.regulator = framerate_regulator(fps=60)
        self.readtime = []
        # self.test_oled()

    def draw_bar(self,col, h):
        with canvas(self.device) as draw:
            draw.rectangle((col, OLEDdriver.oled_height-h, col + OLEDdriver.bar_width, OLEDdriver.bottom), outline="blue", fill="white")
        # print "draw_bar at ", col," ",h
    def draw_line(self,col, h):
        with canvas(self.device) as draw:
            draw.line((col, OLEDdriver.oled_height-h, col + OLEDdriver.bar_width, OLEDdriver.bottom), fill="white")

    def draw_bar2(self,draw, col, h):
        ''' draws up to 32 pixels high, OLED.bar wide '''
        x = col * OLEDdriver.bar_space
        draw.rectangle((x, OLEDdriver.oled_height-h, x + OLEDdriver.bar_width, OLEDdriver.bottom), outline="blue", fill="blue")

    def draw_status(self, vol, source, mute, gain, headphonedetect):
        """ simple dignostic to see the current source channel and volume setting """

        states = ""
        if mute: states+= "Mute - "
        if gain: states+= "Gain - "
        if headphonedetect: states+= "H/P detect"

        self.calcDisplaytime()
        with self.regulator:
            with canvas(self.device) as draw:
                draw.text((0,0), text='Volume %2.1fdB' % (vol/2.0), fill="white", font=self.font)
                draw.text((0,11),text='Channel %s' % source, fill="white",font=self.font)
                draw.text((0,22),text=states, fill="white", font=self.font)

        self.calcDisplaytime(False)

    def draw_screen(self,data):
        self.calcDisplaytime()
        # print("OLEDdriver.draw_screen> ", data)
        bars = OLEDdriver.bars
        if len(data)< OLEDdriver.bars: bars = len(data)

        with self.regulator:
            with canvas(self.device) as c:
                for i in range(bars):
                    self.draw_bar2(c, i, 32*(35+data[i])/110 )
        self.calcDisplaytime(False)

    def calcDisplaytime(self,start=True):
        if start:
            self.startreadtime = time.time()
        else:
            self.readtime.append(time.time()-self.startreadtime)
            if len(self.readtime)>100: del self.readtime[0]
            # print('OLEDdriver:calcDisplaytime> %3.3fms, %3.3f' % (np.mean(self.readtime)*1000, self.readtime[-1]))

    def test_oled(self):
        print("OLED test full speed")
        self.device.persist = True
        for i in range(8):
            for j in range(OLEDdriver.bars):
                self.draw_bar(i*(OLEDdriver.bar_space+10), 32)
                # time.sleep(0.00002)
        print("OLED testing done")
        # time.sleep(4)

    def test_oled2(self):
        print("OLED test full speed")
        with canvas(self.device) as draw:
            for j in range(OLEDdriver.bars):
                print("draw at col", j)
                for i in range(OLEDdriver.oled_height):
                    self.draw_bar2(draw,j*OLEDdriver.bar_space+4, i)
                    time.sleep(0.2)

    def test_oled3(self):
        with canvas(self.device) as draw:

            self.draw_bar2(draw,OLEDdriver.bar_space+4, 10)
            self.device.persist = True
            self.draw_bar2(draw,OLEDdriver.bar_space+40, 20)
                    # time.sleep(0.2)

    def test_oled4(self):
        with self.regulator:
            with canvas(self.device) as c:
                self.draw_bar2(c,1,1)
                self.draw_bar2(c,3,10)
                self.draw_bar2(c,25,32)


if __name__ == "__main__":
    try:
        d = OLEDdriver()
        d.test_oled4()
    except KeyboardInterrupt:
        pass
