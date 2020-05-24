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
from PIL import ImageFont, Image, ImageOps
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from luma.core.sprite_system import framerate_regulator

def make_font(name, size):
    font_path = os.path.abspath(os.path.join( os.path.dirname(__file__), 'fonts', name))
    try:
        return ImageFont.truetype(font_path, int(size))
    except Exception as e:
            print("make_font > error ", e)

def scaleImage(image_path, geo):
    """  scales an image to fit the frame, with the height or width changing proportionally """
    """  Find out which parameter does not fit the frame """
    # print float(image.width) / self.fwidth,  float(image.height) /self.fheight
    image = Image.open(image_path)
    image = ImageOps.invert(image)
    # logo = Image.open(img_path).convert("RGBA")
    if   float(image.width) / geo.w > float(image.height) / geo.h:
        wpercent = (geo.w/float(image.width))
        hsize = int((float(image.height)*float(wpercent)))
        # print ("SourceIcon.scaleimage> height", hsize, wpercent)
        return image.resize((geo.w, hsize), Image.ANTIALIAS)
    else:
        wpercent = (geo.h/float(image.height))
        wsize = int((float(image.width)*float(wpercent)))
        # print ("SourceIcon.scaleimage> width", wsize, wpercent)
        return image.resize((wsize, geo.h), Image.ANTIALIAS)
    return image

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
        self.device.persist = False
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

    def draw(self, screen):
        self.calcDisplaytime(True)
        with self.regulator:
            with canvas(self.device) as c:
                screen(c)
        self.calcDisplaytime(False)

    @property
    def boundary(self):
        return [0 , 0, self.device.width-1, self.device.height-1]

    def outline(self, basis, geo, outline):
        basis.rectangle(self.trabcd(geo.coords), outline=outline)

    def drawFrameMiddlerect(self, basis, geo, fill, wh,  xoffset=0):
        """ xoffset is how far from the left side to draw the rect
            size is set to the given height"""
        if wh[0]>geo.w: print("OLEDdriver.drawFrameMiddlerect> rectangle width is too large for frame")
        if wh[1]>geo.h: print("OLEDdriver.drawFrameMiddlerect> rectangle height is too large for frame")
        coords = (geo.a+xoffset, geo.centre[1]-wh[1]/2, geo.a+xoffset+wh[0], geo.centre[1]+wh[1]/2)
        basis.rectangle(self.trabcd(coords), fill=fill)

    def drawFrameLVCentredtext(self, basis, geo, text, font):
        w, h = basis.textsize(text=text, font=font)
        if w > geo.w: print("OLEDdriver.drawFrameCentredText> text to wide for frame")
        if h > geo.h: print("OLEDdriver.drawFrameCentredText> text to high for frame")
        xy = (geo.a, geo.centre[1]+h/2)
        basis.text(self.trxy( xy ), text=text, font=font , fill="white")

    def drawFrameCentredText( self, basis, geo, text, font):
        """ text is written in the centre of the frame """
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
        if w > geo.w: print("OLEDdrive.drawFrameCentredImage> image width exceeds frame")
        if h > geo.h: print("OLEDdrive.drawFrameCentredImage> image width exceeds frame")
        xy = (geo.centre[0]-w/2, geo.centre[1]+h/2)
        image =  image.convert("L")  #(self.platform.device.mode)
        basis.bitmap( self.trxy( xy ), image) # fill="white" )

    def drawFrameTriange( self, basis, geo, pc, fill ):
        # pc is a percentage of the maximum height
        slope = geo.h/geo.w
        xy  = self.trxy( (geo.a, geo.b) )
        xy1 = self.trxy( (geo.a+geo.w*pc, geo.d*slope*pc) )
        xy2 = self.trxy( (geo.a+geo.w*pc, geo.b) )
        basis.polygon( ( xy, xy1, xy2 ) , fill=fill, outline="white" )


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
        # print("trabcd from %s to %s" % (coords, new))
        return new
        # translate coordinates to screen coordinates

    def trxy(self, coords):
        return (coords[0], self.device.height-coords[1]-1)
        # translate coordinates to screen coordinates

def getDevice(actual_args=None):
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


from luma.core import cmdline, error
class frontOLED(OLEDdriver):
    """ driver for the front 256,64 spi display """
    SPIPORT    = 1
    HEIGHT     = 64
    WIDTH      = 256
    FPS        = 40
    config        = ['-i=spi', '--width=256', '-d=ssd1322', '--spi-bus-speed=2000000']

    def __init__(self):

        OLEDdriver.__init__(self, device=getDevice( frontOLED.config ), fps=frontOLED.FPS)

        self.testdevice()
        # driver = spi(port=internalOLED.I2CPORT, address=internalOLED.I2CADDRESS)
        # OLEDdriver.__init__(self, device=ssd1306(serial, height=internalOLED.HEIGHT, width=internalOLED.WIDTH), fps=internalOLED.FPS)
        #
        # self.testdevice()
        print("frontOLED.__init__> *** not implemented ***")

    def trabcd(self, coords):
        new = (coords[0], self.device.height-coords[1]-1, coords[2], self.device.height-coords[3]-1)
        # print("trabcd from %s to %s" % (coords, new))
        return new
        # translate coordinates to screen coordinates

    def trxy(self, coords):
        return (coords[0], self.device.height-coords[1]-1)
        # translate coordinates to screen coordinates


if __name__ == "__main__":
    try:
        d = internalOLED()
        d.test_oled4()
        d.draw_status()
    except KeyboardInterrupt:
        pass
