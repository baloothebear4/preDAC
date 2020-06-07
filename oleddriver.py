#!/usr/bin/env python
"""
OLED driver classes

Abstracts over the luma package to create a flexible interface to
different OLED displays on different HW interfaces

baloothebear4

v1. 20 May 2020   Original, based on OLEDbar() class

"""


import time, sys, os, math

import datetime
from PIL import ImageFont, Image, ImageOps
from luma.core.interface.serial import i2c, spi
from luma.core.render import canvas
from luma.oled.device import ssd1306, ssd1322
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

    image = Image.open(image_path).convert("L")  #RGBA
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
    """
        Base class to control the drawing primatives to the screen
        - maps the geometry across
    """

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
            # print('OLEDdriver:calcDisplaytime> %3.3fms' % (1000*sum(self.readtime)/len(self.readtime)))

    def drawcallback(self, draw_fn):
        self.drawcallback = draw_fn

    def testdevice(self):
        self.font = make_font("arial.ttf", 11)
        with self.regulator:
            with canvas(self.device) as c:
                c.text((0,0), text='test 1234: %d' % self.device.height, fill="white", font=self.font)
        # time.sleep(3)

    def draw(self, screen):
        if self.device is not None:
            self.calcDisplaytime(True)
            with self.regulator:
                with canvas(self.device) as c:
                    screen.draw(c)
            self.calcDisplaytime(False)

    def textsize(self, text, font):
        with canvas(self.device) as c:
            return c.textsize(text, font)

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
        coords = (geo.x0+xoffset, geo.centre[1]-wh[1]/2, geo.x0+xoffset+wh[0], geo.centre[1]+wh[1]/2)
        basis.rectangle(self.trabcd(coords), fill=fill)

    def drawFrameCentrerect(self, basis, geo, fill, wh, yoffset):
        """ yoffset is how far from the bottom side to draw the rect
            size is set to the given height"""
        if wh[0]>geo.w: print("OLEDdriver.drawFrameCentrerect> rectangle width is too large for frame")
        if wh[1]>geo.h: print("OLEDdriver.drawFrameCentrerect> rectangle height is too large for frame")
        coords = (geo.centre[0]-wh[0]/2, geo.y0+yoffset, geo.centre[0]+wh[0]/2, geo.y0+wh[1]+yoffset)
        basis.rectangle(self.trabcd(coords), fill=fill)

    def drawFrameLVCentredtext(self, basis, geo, text, font):
        w, h = basis.textsize(text=text, font=font)
        if w > geo.w+2: print("OLEDdriver.drawFrameCentredText> text to wide for frame")
        if h > geo.h+2: print("OLEDdriver.drawFrameCentredText> text to high for frame")
        xy = (geo.x0, geo.centre[1]+h/2)
        basis.text(self.trxy( xy ), text=text, font=font , fill="white")

    def drawFrameCentredText( self, basis, geo, text, font):
        """ text is written in the centre of the frame """
        w, h = basis.textsize(text=text, font=font)
        if w > geo.w+2: print("OLEDdriver.drawFrameCentredText> text %s too wide %d, for frame %d" % (text, w, geo.w))
        if h > geo.h+2: print("OLEDdriver.drawFrameCentredText> text %s too high %d, for frame %d" % (text, h, geo.h))
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
        xy  = self.trxy( (geo.x0, geo.y0) )
        xy1 = self.trxy( (geo.x0+geo.w*pc, geo.y0+geo.w*slope*pc) )
        xy2 = self.trxy( (geo.x0+geo.w*pc, geo.y0) )
        # print("triangle at ", ( xy, xy1, xy2 ), slope, pc)
        # print("Frame", geo.norm(), geo.abcd, geo.wh)
        basis.polygon( ( xy, xy1, xy2 ) , fill=fill, outline=fill )

    def drawFrameBar(self, basis, geo, x, ypc, w, fill ):
        coords = (geo.x0+x, geo.y0, geo.x0+x+w, geo.y0+geo.y1*ypc)
        basis.rectangle( self.trabcd(coords), fill=fill)

    def drawFrameCentredCircle(self, basis, geo, r, y, colour ):
        # print("Circle", geo.centre, r, y)
        coords = (geo.centre[0]-r, y+geo.centre[1]+r, geo.centre[0]+r, y+geo.centre[1]-r )
        basis.ellipse( self.trabcd(coords), fill=colour, outline='white' )
        # basis.ellipse( self.trabcd((21,5,41,25)), fill='white', outline='white' )

    def drawFrameCentredVector(self, basis, geo, len, val, yoffset, colour ):
        # print("drawFrameCentredVector> len %d, val %f, yoffset %d" % (len, val, yoffset))
        ab     = self.anglerange(geo.w, len)
        angle  = 180-(ab[0] + val * (ab[1]-ab[0]))
        xy     = self.posn(angle, len)
        # print("vector: angle %s, xy %s, ab %s, yoff %d, len %d" % (angle, xy, ab, yoffset, len))
        coords = ( geo.centre[0], yoffset,geo.centre[0]+xy[0], yoffset+xy[1] )
        basis.line( self.trabcd(coords), fill=colour)

    def drawFrameCentredVectorText(self, basis, geo, len, val, yoffset, colour, text, font ):
        # print("drawFrameCentredVectorText> len %d, val %f, yoffset %d, text %s" % (len, val, yoffset, text))
        ab     = self.anglerange(geo.w, len)
        angle  = 180-(ab[0] + val * (ab[1]-ab[0]))
        xy     = self.posn(angle, len)
        w, h   = basis.textsize(text=text, font=font)
        # print("vectorText: angle %s, xy %s, ab %s, yoff %d, len %d" % (angle, xy, ab, yoffset, len))
        xy = ( geo.centre[0]+xy[0]-w/2, yoffset+xy[1] )
        basis.text( self.trxy(xy), fill=colour, text=text, font=font)

    def drawFrameCentreArc(self, basis, geo, fill, wh, yoffset, len):
        """ yoffset is how far from the bottom side to draw the rect
            size is set to the given height"""
        if wh[0]>geo.w: print("OLEDdriver.drawFrameCentrerect> rectangle width is too large for frame")
        if wh[1]>geo.h: print("OLEDdriver.drawFrameCentrerect> rectangle height is too large for frame")
        coords = (geo.centre[0]-wh[0]/2, geo.y1+yoffset, geo.centre[0]+wh[0]/2, geo.y1-wh[1]+yoffset)
        ab     = self.anglerange(geo.w, len)
        # print("arc wh %s, coords %s, ab %s, geo.co %s, yoff %d, len %d" % (wh, coords, ab, geo.coords, yoffset, len))

        basis.arc(self.trabcd(coords), start=ab[0]+160, end=ab[1]+200, fill=fill)
        # basis.arc( self.trabcd((0,50,50,0)), start=180, end=270, fill='white')

    def drawFrameCentrePie(self, basis, geo, fill, wh, yoffset, len):
        """ yoffset is how far from the bottom side to draw the rect
            size is set to the given height"""
        if wh[0]>geo.w: print("OLEDdriver.drawFrameCentrerect> rectangle width is too large for frame")
        if wh[1]>geo.h: print("OLEDdriver.drawFrameCentrerect> rectangle height is too large for frame")
        coords = (geo.centre[0]-wh[0]/2, geo.y1+yoffset, geo.centre[0]+wh[0]/2, geo.y1-wh[1]+yoffset)
        ab     = self.anglerange(geo.w, len)
        # print("a  rc wh %s, coords %s, ab %s, geo.co %s, yoff %d, len %d" % (wh, coords, ab, geo.coords, yoffset, len))

        basis.pieslice(self.trabcd(coords), start=ab[0]+180, end=ab[1]+180, fill=fill)
        # basis.arc( self.trabcd((0,50,50,0)), start=180, end=270, fill='white')

    def posn(self, angle, length):
        dx = int(math.cos(math.radians(angle)) * length)
        dy = int(math.sin(math.radians(angle)) * length)
        return (dx, dy)

    def anglerange(self, w, len):
        # print("Anglerange", w, len)
        if len-w/2<0:
            angle_min = 0
        else:
            xmin=w/2
            angle_min = int(math.degrees(math.acos(xmin/len)))
        angle_max = 180-angle_min
        return (angle_min, angle_max)

    def draw_status(self, vol, source, id, mute, gain, headphonedetect):
        """ simple dignostic to see the current source channel and volume setting """

        states = ""
        if mute: states+= "Mute - "
        if gain: states+= "Gain - "
        if headphonedetect: states+= "H/P detect"

        self.calcDisplaytime()
        with self.regulator:
            with canvas(self.device) as draw:
                draw.text((0,0), text='Volume %2.1fdB' % vol, fill="white", font=self.font)
                draw.text((0,11),text='Channel %d  %s' % (id, source), fill="white",font=self.font)
                draw.text((0,22),text=states, fill="white", font=self.font)

        self.calcDisplaytime(False)

    def trabcd(self, coords):
        new = (coords[0], self.device.height-coords[1]-1, coords[2], self.device.height-coords[3]-1)
        # print("trabcd from %s to %s - device height %f" % (coords, new, self.device.height ))
        return new
        # translate coordinates to screen coordinates

    def trxy(self, coords):
        # print("trxy from %s to %s" % (coords, (coords[0], self.device.height-coords[1]-1)))
        return (coords[0], self.device.height-coords[1]-1)
        # translate coordinates to screen coordinates


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

class frontOLED(OLEDdriver):
    """ driver for the front 256,64 spi display """
    SPIPORT    = 0
    FPS        = 40

    def __init__(self):
        driver = spi(port=frontOLED.SPIPORT)
        OLEDdriver.__init__(self, device=ssd1322(driver), fps=frontOLED.FPS)

        self.testdevice()
        print("frontOLED.__init__> initialised")


if __name__ == "__main__":
    try:
        d = internalOLED()
        d.test_oled4()
        d.draw_status()
    except KeyboardInterrupt:
        pass
