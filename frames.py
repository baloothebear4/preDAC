#!/usr/bin/env python
"""
 Display classes:
    - base screens
    - screen classes & object mangement
    - display driver control

 Part of mVista preDAC

 Baloothebear4 Sept 17


"""

from octave import Octave

import os
import sys
from PIL import ImageFont, Image
import time
from luma.core.render import canvas

def make_font(name, size):
    font_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 'fonts', name))
    return ImageFont.truetype(font_path, size)

def drawCentredText( basis, xc, yc, r, v, font, maxw):
    w, h = basis.textsize(text=str(v), font=font)
    # print "drawCentredText", xc-r+maxw/2-w/2, yc-r, xc, yc, r
    basis.text((xc-r+maxw/2-w/2, yc-r), text=str(v), font=font , fill="white")


class ActualScreen:
    """ facts about the actual display including its size """
    def __init__(self, platform):
        self.swidth  = platform.device.width  #baseline coordinates - rightmost position
        self.sheight = platform.device.height


class Frame(ActualScreen):
    """ facts about a frame including its size, which sits on the display and contains
        screen one or more screen objects that are placed in the frame
    """
    def __init__(self, platform):
        ActualScreen.__init__(self, platform) # Each frame sits on the screen
        self.fwidth  = self.swidth            # baseline size, frame is full screen
        self.fheight = self.sheight
        self.fx      = 0                      # coordiantes of the frame top left corner on the screen
        self.fy      = 0

    def sizeFrame(self, width, height):
        self.fwidth  = width  # baseline coordinates - rightmost position
        self.fheight = height

    """ where object is a screen class with inherited frame class """
    def alignLeftOf(self, frame):
        # self.fwidth = self.swidth - frame.fwidth
        self.fx     = frame.fx-self.fwidth
        # print "Frame.alignLeftOf", self
        if self.fx < 0:
            print "Frame.alignLeftOf> error insufficient screen width", self

    def alignRightOf(self, frame):
        if frame.x-self.fwidth >= 0:
            self.fx = frame.fx-self.fwidth
            # print "Frame.alignRightOf", self
        else:
            print "Frame.alignLeftOf> error insufficient screen width", self


    """ Alignments, relative to screen, assume drawing a rectangle with the coordinates in the top LH corner
        NB:  Frames are always full height """
    def alignFrameLeft(self):
        self.fx = 0
        # print "Frame.alignFrameLeft", self

    def setMaxFrameWidthLeftTo(self, frame):
        self.fx      = 0
        self.fwidth  = frame.fx
        # print "Frame.alignFrameLeft", self

    def alignFrameRight(self):
        if self.fwidth  <= self.swidth:
            self.fx = self.swidth-self.fwidth
            # print "Frame.alignFrameRight", self
        else:
            print "Frame.alignFrameRight> error insufficient screen width", self


class Location(Frame):
    """
        Manages the positional information relating to the screen objects
        NB shifts to lower left as 0,0 not upper left

        Manages the relative position of an object on a frame, the frame defaults to the whole screen
        Works on the basis of plotting rectangular objects, which have width & height

        NB:  (0,0) is top left corner and all coordinates are relative to the frame
        Hence greatly simplifies, drawing objects at relative positions as object size changes
    """
    def __init__(self, platform):
        Frame.__init__(self, platform)
        self.platform     = platform
        self.x            = 0   # position of the object on the frame
        self.y            = 0
        self.width        = 0
        self.height       = 0

        self.top          = 0
        self.bottom       = self.sheight


    """ need some methods to align the screen object relative to a given position:
        eg leftof(x,y), centre(y)...
    """
    def drawFrameCentredText( self, basis, text, font):
        w, h = basis.textsize(text=text, font=font)
        self.x = (self.fwidth  - w)/2
        self.y = (self.fheight - h)/2
        basis.text((self.fx+self.x, self.fy+self.y), text=text, font=font , fill="white")

    def drawFrameTopCentredText( self, basis, text, font):
        w, h = basis.textsize(text=text, font=font)
        self.x = (self.fwidth  - w)/2
        self.y = 0
        basis.text((self.fx+self.x, self.fy+self.y), text=text, font=font , fill="white")

    def drawFrameLRCentredText( self, basis, xc, yc, r, text, font, maxw ):
        w, h = basis.textsize(text=str(text), font=font)
        basis.text((xc-r+maxw/2-w/2, yc-r), text=str(text), font=font , fill="white")

    def drawFrameCentredImage( self, basis, image ):
        self.x = (self.fwidth  - image.width)/2
        self.y = (self.fheight - image.height)/2
        image =  image.convert("L")  #(self.platform.device.mode)
        basis.bitmap( (self.fx+self.x, self.fy+self.y), image) # fill="white" )

    def drawFrameTriange( self, basis, w, h, col ):
        x1y1   = (self.fx+self.x + w, self.fy+self.y-h)
        x2y2   = (self.fx+self.x + w, self.fy+self.y)
        basis.polygon( [(self.fx + self.x, self.fy + self.y ), x1y1, x2y2] , fill=col, outline=col )
        # print "Location.drawFrameTriange>", self
        #basis.polygon([(self.x, self.y), (self.x + self.width, self.y-self.height), (self.x + self.width, self.y)], outline="red", fill="red")

    """ Alignments, relative to frame, assume drawing a rectangle with the coordinates in the top LH corner """
    def alignLeft(self):
        self.x = self.fx

    def alignRight(self):
        if self.fwidth>self.width:
            self.x = self.fwidth-self.width
        else:
            print "Location.alignRight> insufficient frame width"

    def alignTop(self):
        self.y = 0

    def alignBottom(self):
        if self.fheight>self.height:
            self.y = self.fheight-self.height
        else:
            print "Location.alignBottom> insufficient frame height"

    def alignAbove(self, obj):
        if obj.height>self.height:
            self.y = obj.height-self.height
        else:
            print "Location.alignAbove> insufficient frame height"

    def alignBelow(self, obj):
        if obj.y+obj.height+self.height<self.fheight:
            self.y = obj.y+obj.height
        else:
            print "Location.alignBelow> insufficient frame height"

    def alignTCentre(self):   #top LH corner
        self.x = (self.fwidth  - self.width)/2
        self.y = (self.fheight - self.height)/2

    def alignBCentre(self):   # bottom LH corner
        self.x = (self.fwidth  - self.width)/2
        self.y = (self.fheight + self.height)/2

    def __repr__(self):
        print "Location object: ", self

    def __str__(self):  # may need to be a __repr__
        text  = "Location Object:\n"
        text += " %20s : %d, %d\n" % ('Screen (w, h)', self.swidth, self.sheight)
        text += " %20s : %d, %d\n" % ('Object (x, y)', self.x, self.y)
        text += " %20s : %d, %d\n" % ('Object (w, h)', self.width, self.height)
        text += " %20s : %d, %d\n" % ('Frame (x, y)',  self.fx, self.fy)
        text += " %20s : %d, %d\n" % ('Frame (w, h)',  self.fwidth,self.fheight)
        return text

class Bar:  # draws a filled rectangle at position x, height y
    topOffset = 5
    def __init__(self, x, yOffset, width, top):
        self.x           = x         # x location
        self.yOffset     = yOffset   # level off the bottom drawing starts from
        self.w           = width
        self.h           = top
        # print "Bar __init__> x,w,maxh", self.x, width

    def draw(self, basis, height):
        if height > self.h:
            height = self.h

        basis.rectangle((self.x, self.h-self.yOffset, self.x + self.w, self.h-height-self.yOffset ), fill="white")
            # print "Bar draw> x, h, lastHeight",self.x, height, self.lastHeight

#
    def drawPeak(self, basis, height, peak ):
        """
        Draw a VU bar with the VU with the whole bar outlined in grey, filled with VU and peak line showing
        """
        if height > self.h:
            height = self.h

        basis.rectangle((self.x, self.h-height-self.yOffset, self.x + self.w, Bar.topOffset ), fill="red")
        basis.rectangle((self.x, self.h-self.yOffset, self.x + self.w, self.h-height-self.yOffset ), fill="white")
        basis.line((self.x, self.h-peak-self.yOffset, self.x + self.w, self.h-peak-self.yOffset ), fill="white")


class SpectrumFrame(Location):
    """
    Creates a spectrum analyser of the width and octave interval specified
    intervals are 1, 3 or 6
    widths    are really half or whole screen
    """
    def __init__(self, platform, interval):
        Location.__init__(self, platform)
        self.platform   = platform
        self.gap        = 4  # between bars
        self.yOffset    = 0
        self.octave     = Octave(interval, self.platform.readBinBandwidth(), self.platform.readNyquist(), self.platform.readbinCount())
        self.numBars    = self.octave.intervalsCount()  # The number of bars is given by the Octave interval
        self.scale      = float(self.fheight-self.yOffset)
        self.barWidth   = None
        self.bars       = []
        self.barFreq    = []

    def draw(self, basis):
        if self.barWidth is None:
            self.barWidth  = (self.fwidth/self.numBars)-self.gap# round(float(self.fwidth)/self.numBars)-self.gap
            leftOffset     = (self.fwidth- (self.numBars*(self.barWidth+self.gap)) )/2
            for i in range(0, self.numBars):
                self.bars.append( Bar(i*(self.barWidth+self.gap)+ leftOffset, self.yOffset, self.barWidth, self.fheight) )
            # print ("Spectrum.setWidth>  barWidth %d, fwidth %d, numBars %d, scale %f, actWidth %d" % (self.barWidth, self.fwidth, self.numBars, self.scale, self.numBars*(self.barWidth+self.gap)) )

        freqbins = self.octave.fill( self.platform.readFreqBins() )
        # self.label.draw(basis)
        for i in range(0, self.numBars):
            self.bars[i].draw(basis, float(self.scale*freqbins[i]))

class VolumeSourceFrame(Location):
    """
    Simple numeric display of the current volume level as value 0-63
    number is centred.
    """
    def __init__(self, platform, topOffset=8):
        Location.__init__(self, platform)
        self.platform = platform
        self.topOffset=topOffset
        self.Pie  = 12

        """ Locate the Frame """
        self.alignFrameRight()

        self.x        = self.swidth-5  #baseline coordinates - rightmost position
        self.y        = self.sheight #                     - bottom most postion
        self.font     = make_font("arial.ttf", 30)
        self.srcfont  = make_font("arial.ttf", 14)

        with canvas(platform.device) as basis:
            self.twidth, self.theight = basis.textsize(text="22", font=self.font)  # calc the size of the widest object

            self.maxsh = 0
            self.maxsw = 0
            for i in self.platform.sourceText():
                w, h = basis.textsize(text=i, font=self.srcfont)  # calc the size of the highest object
                if h>self.maxsh:
                    self.maxsh = h
                if w>self.maxsw:
                    self.maxsw = w

        self.fwidth   = self.Pie + self.twidth + 20 #gap
        self.minA     = 135
        self.maxA     = 45

        # print "VolumeSourceFrame.__init__", self

    def draw1(self, basis):
        vol = self.platform.readVolume()
        w, h = basis.textsize(text=str(vol), font=self.font)

        x = self.x-self.twidth/2-10
        y = self.topOffset+self.theight/2+8
        m = self.minA +(vol*(360-self.minA+self.maxA))/63

        self.drawArc( basis, x, y, 7+self.twidth/2, self.maxA)
        self.drawArc( basis, x, y, 8+self.twidth/2, self.maxA)
        self.drawPieMark( basis, x, y, self.Pie+self.twidth/2, m, "white")
        self.drawCircle( basis, x, y, 4+self.twidth/2, "black")
        # drawCentredText( basis, x, y, self.twidth/2, vol, self.font, self.width)
        self.drawFrameLRCentredText( basis, x, y, self.twidth/2, vol, self.font, self.twidth)

        src= self.platform.activeSourceText()
        w, h = basis.textsize(text=src, font=self.srcfont)
        #print "y h", self.y, h
        # drawCentredText( basis, x, self.y-self.maxsh/2, -2+self.maxsh/2, src,self.srcfont, self.maxsh)
        self.drawFrameLRCentredText( basis, x, self.y-self.maxsh/2, -2+self.maxsh/2, src,self.srcfont, self.maxsh)

    def draw(self, basis):
        vol = self.platform.readVolume()
        w, h = basis.textsize(text=str(vol), font=self.font)

        x = self.x-self.twidth/2-10
        y = self.topOffset+self.theight/2+8
        m = self.minA +(vol*(360-self.minA+self.maxA))/63
        arcT  = 10
        marks = 8
        for i in range(5, arcT):
            self.drawArc( basis, x, y, i+self.twidth/2, self.minA, m, "grey")
            self.drawArc( basis, x, y, i+self.twidth/2, m, self.maxA, "green")

        # for a in range(0, marks):
        #     self.drawPieMark( basis, x, y, self.Pie+self.twidth/2,  self.minA + a*(360-self.minA+self.maxA)/marks, "black")
        # self.drawCircle( basis, x, y, 4+self.twidth/2, "black")
        # drawCentredText( basis, x, y, self.twidth/2, vol, self.font, self.width)
        self.drawFrameLRCentredText( basis, x, y, self.twidth/2, vol, self.font, self.twidth)

        src= self.platform.activeSourceText()
        w, h = basis.textsize(text=src, font=self.srcfont)
        #print "y h", self.y, h
        # drawCentredText( basis, x, self.y-self.maxsh/2, -2+self.maxsh/2, src,self.srcfont, self.maxsh)
        self.drawFrameLRCentredText( basis, x, self.y-self.maxsh/2, -2+self.maxsh/2, src,self.srcfont, self.maxsh)

    def drawArc(self, basis, xc, yc, r, a, b, col="red"):
        basis.arc((xc-r, yc-r,xc+r, yc+r), a, b, fill=col)

    def drawPieMark(self, basis, xc, yc, r, m, colour):
        basis.pieslice((xc-r, yc-r,xc+r, yc+r), m,m+4, fill=colour)

    def drawCircle(self, basis, xc, yc, r, colour):
        basis.ellipse((xc-r, yc-r,xc+r, yc+r), outline="black", fill=colour)

class VolumeAmountFrame(Location):
    """
        Displays a triangle filled proportional to the Volume level
    """
    def __init__(self, platform, size=1):  # size is a scaling factor
        self.platform   = platform
        Location.__init__(self, platform)
        self.width = 120/size
        self.height= 40/size

        """ position the object in the frame """
        self.alignBCentre()

    def draw(self, basis):
        self.alignBCentre()
        self.drawFrameTriange( basis, self.width, self.height, "red" )
        vol = self.platform.readVolume()
        width  = self.width * vol / 63
        height = (self.height * vol)/63
        self.drawFrameTriange( basis, width, height, "white" )

class SourceIconFrame(Location):
    """
        Displays a an Icon for the source type and animates it
    """
    def __init__(self, platform):  # size is a scaling factor
        Location.__init__(self, platform)
        self.platform       = platform
        self.files          = {}  # dictionary of files to images
        self.icons          = {}  # dictionary of images, sources as keys
        self.width          = 0

        """
        Build a dict of all the icon files to be used
        """
        sources = self.platform.sourcesAvailable()
        for s in sources:
            self.files.update( {s: self.platform.getSourceIconFiles(s)} )

        """
        Build a dict of all the images, sized, positioned, ready to go
        """
        for s in self.files:
            images = []
            for f in self.files[s]:
                img_path  = os.path.abspath(os.path.join(os.path.dirname(__file__), 'icons', f))
                img = self.scaleImage( Image.open(img_path), f )
                # img = self.scaleImage( Image.open(img_path), f )
                if img.width > self.width:
                    self.width = img.width
                images.append( img )
            self.icons.update( {s : images} )

        # print "SourceIcon.__init__> ready", self.width

    def draw(self, basis):
        # print "SourceIconFrame.draw>", self.platform.activeSource, self.platform.currentIcon
        self.drawFrameCentredImage( basis, self.icons[self.platform.activeSource][self.platform.currentIcon])

    def scaleImage(self, image, f):
        """  scales an image to fit the frame, with the height or width changing proportionally """
        """  Find out which parameter does not fit the frame """
        # print float(image.width) / self.fwidth,  float(image.height) /self.fheight
        if   float(image.width) / self.fwidth > float(image.height) / self.fheight:
            wpercent = (self.fwidth/float(image.width))
            hsize = int((float(image.height)*float(wpercent)))
            # print "SourceIcon.scaleimage> %", hsize, f
            return image.resize((self.fwidth, hsize), Image.ANTIALIAS)
        else:
            wpercent = (self.fheight/float(image.height))
            wsize = int((float(image.width)*float(wpercent)))
            # print "SourceIcon.scaleimage> %", wsize, f
            return image.resize((wsize, self.fheight), Image.ANTIALIAS)
        return image

class TextFrame(Location):
    """
    Display a simple centred set of text
    """
    def __init__(self, platform, text, size):
        Location.__init__(self, platform)
        self.fwidth = self.swidth
        self.text   = text
        self.font   = make_font("arial.ttf", size)

    def draw(self, basis):
        self.drawFrameCentredText(basis, self.text, self.font)

class MenuFrame(Location):
    """
    Display a simple the title of screen
    """
    def __init__(self, platform):
        Location.__init__(self, platform)
        self.fwidth = self.swidth
        self.font   = make_font("arial.ttf", 12)

    def draw(self, basis, text):
        self.drawFrameTopCentredText(basis, text, self.font)


class VolumeUnitsFrame(Location):
    """
    AKA : VU meter, note the peak is also displayed too
    """
    gap      = 2
    yOffset  = 0
    barWidth = 10
    text     = "  VU"

    def __init__(self, platform):
        Location.__init__(self, platform)
        self.platform = platform
        self.font     = make_font("arial.ttf", 12)
        self.fwidth   = 2*(VolumeUnitsFrame.barWidth + VolumeUnitsFrame.gap)
        self.height   = self.fheight
        self.VU       = None
        self.scale    = (self.height-VolumeUnitsFrame.yOffset)

        self.label = Label(self.x, VolumeUnitsFrame.text, self.fy )
        self.alignLeft()
        # print "VolumeUnitsFrame.__init__>", self

    def draw(self, basis):
        if self.VU is None:
            self.VU = { 'Left'  : Bar( self.x, VolumeUnitsFrame.yOffset, VolumeUnitsFrame.barWidth, self.height),
                        'Right' : Bar( self.x+ VolumeUnitsFrame.barWidth+VolumeUnitsFrame.gap, VolumeUnitsFrame.yOffset, VolumeUnitsFrame.barWidth, self.height )
                      }
        Vrms = self.platform.readVrms()
        Vpeak= self.platform.readVpeak()
        # print "VU draw> rms", Vrms, (self.height-VolumeUnitsFrame.yOffset)*Vrms['Left']*self.scale, (self.height-VolumeUnitsFrame.yOffset)*Vrms['Right']*self.scale
        # print "VU draw> peak", Vpeak, Vpeak['Left'], (self.height-VolumeUnitsFrame.yOffset)*Vpeak['Left']*self.scale
        self.VU['Left'].drawPeak( basis, Vrms['Left']*self.scale, Vpeak['Left']*self.scale)
        self.VU['Right'].drawPeak( basis, Vrms['Right']*self.scale, Vpeak['Right']*self.scale)
        # self.label.draw(basis)

class Label:
    """
    add label - deprecated ---> not used as this is not a full height frame
    """
    def __init__(self, x, text, screenHeight):
        self.x    = x
        self.text = text
        self.font = make_font("arial.ttf", 10)
        self.showing = 0
        self.h       = screenHeight

    def draw(self, basis):
        if not self.showing:
            w, h = basis.textsize(text=self.text, font=self.font)
            y = self.h-h
            basis.text((self.x, y), text=self.text, font=self.font, fill="grey")
            self.showing != self.showing
