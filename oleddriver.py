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

def make_font(name, size):
    font_path = os.path.abspath(os.path.join( os.path.dirname(__file__), 'fonts', name))
    try:
        return ImageFont.truetype(font_path, size)
    except:
            print("make_font > error, font files not found at ", font_path)

class OLEDdriver(canvas):
    oled_height = 32
    oled_width  = 128
    bottom      = oled_height
    top         = 0
    bar_width   = 3
    bar_gap     = 2
    bar_space   = bar_gap + bar_width
    bars        = int(oled_width / bar_space)

    def __init__(self, device, fps):
        self.device     = device
        self.regulator  = framerate_regulator( fps=fps )
        self.device.persist = True
        self.readtime = []

    def calcDisplaytime(self,start=True):
        if start:
            self.startreadtime = time.time()
        else:
            self.readtime.append(time.time()-self.startreadtime)
            if len(self.readtime)>100: del self.readtime[0]
            print('OLEDdriver:calcDisplaytime> %3.3fms' % (1000*sum(self.readtime)/len(self.readtime)))

    def drawcallback(self, draw_fn):
        self.drawcallback = draw_fn

    def testdevice(self):
        self.font = make_font("arial.ttf", 11)
        with self.regulator:
            with canvas(self.device) as c:
                c.text((0,0), text='test 1234: %d' % self.device.height, fill="white", font=self.font)
        # time.sleep(3)

    def draw(self):
        self.calcDisplaytime(True)
        with self.regulator:
            with canvas(self.device) as c:
                self.drawcallback(c)
        self.calcDisplaytime(False)

    @property
    def boundary(self):
        return [0 , 0, self.device.width-1, self.device.height-1]

    def rectangle(self, basis, geo, outline):
        basis.rectangle(self.trabcd(geo.coords), outline=outline)

        """ need some methods to align the screen object relative to a given position:
            eg leftof(x,y), centre(y)...
        """
    def drawFrameCentredText( self, basis, geo, text, font):
        w, h = basis.textsize(text=text, font=font)
        if w > geo.w: print("OLEDdriver.drawFrameCentredText> text to wide for frame")
        if h > geo.h: print("OLEDdriver.drawFrameCentredText> text to high for frame")
        xy = (geo.centre[0]-w/2, geo.centre[1]+h/2)
        basis.text(self.trxy( xy ), text=text, font=font , fill="white")

    def drawFrameTopCentredText( self, basis, geo, text, font):
        w, h = basis.textsize(text=text, font=font)
        xy = (geo.centre[0]-w/2, geo.d)
        basis.text(self.trxy( xy ), text=text, font=font , fill="white")

    def drawFrameLRCentredText( self, basis, xc, yc, r, text, font, maxw ):
        print("drawFrameLRCentredText deprecated - use drawFrameCentredText")

    def drawFrameCentredImage( self, basis, geo, image ):
        w = image.width
        h = image.height
        xy = (geo.centre[0]-w/2, geo.centre[1]+h/2)
        image =  image.convert("L")  #(self.platform.device.mode)
        basis.bitmap( self.trxy( xy ), image) # fill="white" )

    def drawFrameTriange( self, basis, w, h, col ):
        x1y1   = (self.fx+self.x + w, self.fy+self.y-h)
        x2y2   = (self.fx+self.x + w, self.fy+self.y)
        basis.polygon( [(self.fx + self.x, self.fy + self.y ), x1y1, x2y2] , fill=col, outline=col )
        # print "Location.drawFrameTriange>", self
        #basis.polygon([(self.x, self.y), (self.x + self.width, self.y-self.height), (self.x + self.width, self.y)], outline="red", fill="red")


    """ test code """
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


class internalOLED(OLEDdriver):
    """ driver for the internal 128,32 i2c display """
    I2CADDRESS = 0x3c
    I2CPORT    = 1
    HEIGHT     = 32
    WIDTH      = 128
    FPS        = 50

    def __init__(self):
        serial = i2c(port=internalOLED.I2CPORT, address=internalOLED.I2CADDRESS)
        OLEDdriver.__init__(self, device=ssd1306(serial, height=internalOLED.HEIGHT, width=internalOLED.WIDTH), fps=internalOLED.FPS)

        self.testdevice()
        print("internalOLED.__init__> display initialised")

    def trabcd(self, coords):
        new = (coords[0], self.device.height-coords[1]-1, coords[2], self.device.height-coords[3]-1)
        print("trabcd from %s to %s" % (coords, new))
        return new
        # translate coordinates to screen coordinates

    def trxy(self, coords):
        return (coords[0], self.device.height-coords[1]-1)
        # translate coordinates to screen coordinates


class frontOLED(OLEDdriver):
    """ driver for the front 256,64 spi display """
    pass


if __name__ == "__main__":
    try:
        d = internalOLED()
        d.test_oled4()
        d.draw_status()
    except KeyboardInterrupt:
        pass
