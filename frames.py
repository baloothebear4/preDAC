#!/usr/bin/env python
"""
 Display classes:
    - base screens
    - screen frames
    - sub-frames

 Part of mVista preDAC

 v1.0 Baloothebear4 Sept 17 - Original
 v2.0 Baloothebear4  May 20 - Re-factored to use Frame class, simplifying & cleaning up

"""

from oleddriver import make_font, scaleImage
from framecore import Frame, Geometry

class depVolumeSourceFrame(Frame):
    """
    *** Deprecated ***

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

class VolumeSourceFrame(Frame):
    """
        Displays the volume as a percentage with the source underneath
        - has a width determined by the scale
    """
    def __init__(self, bounds, platform, display, scale, Halign='right'):
        geo   = Geometry(display.boundary)
        geo.scale( (scale, 1.0) )
        Frame.__init__(self, display.boundary, platform, display, (0.5,1.0), 'bottom', Halign)
        # self += TextFrame(self.coords, platform, display, "top", "22")        # this are the widest number
        # self += SourceTextFrame(self.coords, platform, display, 'bottom', "streamer") # this are the widest source text
        self += OutlineFrame(self.coords, platform, display)
        self.check()

    @property
    def width(self):
        return

class dBVolumeSourceFrame(Frame):
    """
        Displays the volume as a percentage with the source underneath
        - has a width determined by the scale
    """
    def __init__(self, bounds, platform, display, scale, Halign='right'):
        geo   = Geometry(display.boundary)
        geo.scale( (scale, 1.0) )
        Frame.__init__(self, display.boundary, platform, display, Halign=Halign)
        self += dbVolumeTextFrame(self.coords, platform, display, V='top', text='-64.0dB')        # this are the widest number
        self += SourceTextFrame(self.coords, platform, display, V='bottom', text='streamer') # this are the widest source text
        self += OutlineFrame(self.coords, platform, display)
        self.check()

    @property
    def width(self):
        return

class VolumeAmountFrame(Frame):
    """
        Displays a triangle filled proportional to the Volume level
    """
    def __init__(self, bounds, platform, display):
        Frame.__init__(self, platform=platform, bounds=bounds, scalers=(0.5,0.5), Valign='middle', Halign='right')

    def draw(self, device):
        self.display.drawFrameTriange( device, self, 1.0, fill="black" )
        vol = self.platform.volume_percent
        self.display.drawFrameTriange( device, self, vol, fill="white" )

class TextFrame(Frame):
    """
        Display a simple centred set of text
    """
    def __init__(self, bounds, platform, display, V, text=''):
        Frame.__init__(self, bounds=bounds, platform=platform, display=display, scalers=(1.0,0.5), Valign=V, Halign='centre')
        self.font   = make_font("arial.ttf", self.h)
        self.text   = text
        self._width, self._height = display.textsize(self.text, self.font)

    def draw(self, basis):
        self.display.drawFrameCentredText(basis, self, self.text, self.font)

    @property
    def width(self):
        return self._width

class VolumeTextFrame(TextFrame):
    def draw(self, basis):
        vol = self.platform.volume_percent * 100
        self.display.drawFrameCentredText(basis, self, "%2d" % vol, self.font)

class SourceTextFrame(TextFrame):
    def draw(self, basis):
        self.display.drawFrameCentredText(basis, self, self.platform.activeSource, self.font)

class dbVolumeTextFrame(TextFrame):
    def draw(self, basis):
        self.display.drawFrameCentredText(basis, self, "%3.1fdB" % self.platform.volume_db, self.font)

class MenuFrame(Frame):
    """
        Display a simple the title of screen, as an overlay
    """
    def __init__(self, bounds, platform, display):
        Frame.__init__(self, platform=platform, bounds=bounds, display=display, scalers=(1.0,0.4), Valign='top', Halign='centre')
        self.font   = make_font("arial.ttf", self.h)

    def draw(self, basis):
        text = self.platform.screenname
        self.display.drawFrameCentredText(basis, self, text, self.font)

class SourceIconFrame(Frame):
    """
        Displays a an Icon for the source type and animates it
    """
    def __init__(self, bounds, platform, display, scale):  # size is a scaling factor
        Frame.__init__(self, platform=platform, bounds=bounds, display=display, scalers=(scale,1.0), Valign='bottom', Halign='left')
        self.files          = {}  # dictionary of files to images
        self.icons          = {}  # dictionary of images, sources as keys

        #Build a dict of all the icon files to be used
        sources = self.platform.sourcesAvailable()
        for s in sources:
            self.files.update( {s: self.platform.getSourceIconFiles(s)} )

        print("source files>", self.files)
        #Build a dict of all the images, sized, positioned, ready to go
        for s in self.files:
            images = []
            for f in self.files[s]:
                img_path  = os.path.abspath(os.path.join(os.path.dirname(__file__), 'icons', f))
                img = scaleImage( img_path, self )
                # if img.width > self.w:
                #     self.w = img.width
                images.append( img )
            self.icons.update( {s : images} )

        # print( "SourceIcon.__init__> ready", self.icons)

    def draw(self, basis):
        print ("SourceIconFrame.draw>", self.platform.activeSource, self.platform.currentIcon)
        self.display.drawFrameCentredImage( basis, self, self.icons[self.platform.activeSource][self.platform.currentIcon])

class VUFrame(Frame):
    """
        Displays a horizontal bar with changing colours at the top
        - side is str 'left' or 'right'
        - limits is an array of points where colour changes occur: [level (%), colour] eg [[0, 'grey'], [0.8,'red'], [0.9],'purple']
    """
    BARHEIGHT    = 0.6  # % of frame height
    TEXTGAP      = 1.5   # % of text width left bar starts
    PEAKBARWIDTH = 1  # pixels

    def __init__(self, bounds, platform, display, channel, limits):  # size is a scaling factor
        self.limits  = limits
        self.channel = channel
        if channel == 'left':
            self.ch_text = 'L'
            V    = 'top'
        elif channel == 'right':
            self.ch_text = 'R'
            V    = 'bottom'
        else:
            raise ValueError('VUFrame.__init__> unknown channel', channel)

        Frame.__init__(self, platform=platform, bounds=bounds, display=display, scalers=(1.0, 0.5), Valign=V, Halign='left')
        self.font   = make_font("arial.ttf", self.h*VUFrame.BARHEIGHT)

    def draw(self, basis):
        # self.display.outline( basis, self, outline="white")
        self.display.drawFrameLVCentredtext(basis, self, self.ch_text, self.font)
        vu      = self.platform.vu[self.channel]
        w, h    = basis.textsize(self.ch_text, self.font)
        xoffset = w*VUFrame.TEXTGAP
        maxw    = self.w-xoffset
        wh      = [vu*maxw, self.h*VUFrame.BARHEIGHT]

        for limit in self.limits:
            self.display.drawFrameMiddlerect(basis, self, limit[1], wh, xoffset)
            if vu < limit[0]: break  #otherwise do the next colour
            xoffset = w*VUFrame.TEXTGAP + maxw * limit[0]
            wh[0]   = maxw * (vu - limit[0])

        xoffset = w*VUFrame.TEXTGAP + maxw * self.platform.peak[self.channel]
        wh      = [VUFrame.PEAKBARWIDTH, self.h*VUFrame.BARHEIGHT]
        self.display.drawFrameMiddlerect(basis, self, 'white', wh, xoffset)

class VUVFrame(Frame):
    """
        Displays a vertical bar with changing colours at the top
        - limits is an array of points where colour changes occur: [level (%), colour] eg [[0, 'grey'], [0.8,'red'], [0.9],'purple']
        - sits within a screen to compile two together
        - uses full screen height
    """
    BARWIDTH     = 0.4  # % of frame width
    XSCALE       = 0.5  # width of the frame in the parent
    BARHEIGHT    = 1.0  # % of frame height
    PEAKBARHEIGHT= 1

    def __init__(self, bounds, platform, display, channel, limits):  # size is a scaling factor
        self.limits  = limits
        self.channel = channel

        Frame.__init__(self, platform=platform, bounds=bounds, display=display, scalers=(VUVFrame.XSCALE, 1.0), Valign='bottom', Halign=channel)
        self.barwidth = int(self.w * VUVFrame.BARWIDTH)
        self.maxh     = self.h * VUVFrame.BARHEIGHT

    def draw(self, basis):
        # self.display.outline( basis, self, outline="white")
        vu      = self.platform.vu[self.channel]
        wh      = [self.barwidth, self.maxh*vu]
        yoffset = 0

        for limit in self.limits:
            self.display.drawFrameCentrerect(basis, self, limit[1], wh, yoffset)
            if vu < limit[0]: break  #otherwise do the next colour
            yoffset = self.maxh * limit[0]
            wh[1]   = self.maxh * (vu - limit[0])

        # add the peak bar
        yoffset = self.maxh * self.platform.peak[self.channel]
        wh      = [self.barwidth, VUVFrame.PEAKBARHEIGHT]
        self.display.drawFrameCentrerect( basis, self, 'white', wh, yoffset)

class OutlineFrame(Frame):
    """
        Draws a box around the edge of the frame
    """
    def __init__(self, bounds, platform, display):  # size is a scaling factor
        Frame.__init__(self, platform=platform, bounds=bounds, display=display)

    def draw(self, basis):
        self.display.outline( basis, self, outline="white")

class SpectrumFrame(Frame):
    """
    Creates a spectrum analyser of the width and octave interval specified
    intervals are 1, 3 or 6
    widths    are really half or whole screen
    - scale is used to determine how wide the frame is as a % of the parent frame
    - channel 'left' or 'right' selects the audio channel and screen alignment
    """
    BARGAP    = 2  # between bars
    BARWMIN   = 1
    BARWMAX   = 5

    def __init__(self, bounds, platform, display, channel, scale):
        self.channel = channel
        if channel == 'left':
            self.ch_text = 'L'
        elif channel == 'right':
            self.ch_text = 'R'
        else:
            raise ValueError('SpectrumFrame.__init__> unknown channel', channel)

        Frame.__init__(self, platform=platform, bounds=bounds, display=display, scalers=(scale, 1.0), Valign="top", Halign=channel)

        # Calculate how many bars can be drawn in the width available
        # Go down the bar widths to see what will fit
        # Determine the max octave fraction that can be accomodated
        # Set up the number function to pack the samples

        for spacing in (6, 3, 2, 1): #go down from the finest to the coarsest to find one that fits
            self.bar_freqs = platform.createBands(spacing)
            self.bars      = len(self.bar_freqs)
            for barw in range(SpectrumFrame.BARWMAX, SpectrumFrame.BARWMIN, -1):
                self.max_bars   = int(self.w/(SpectrumFrame.BARGAP+barw))
                if  self.bars <= self.max_bars: break
            if  self.bars <= self.max_bars: break
        self.barw = barw
        print("SpectrumFrame.__init__> max bars=%d, octave spacing=1/%d, num bars=%d, width=%d" % (self.max_bars, spacing, self.bars, self.barw))

    def draw(self, basis):
        x = 0
        for i in range(0, self.bars):
            self.display.drawFrameBar(basis, self, x, self.platform.spectrum[self.channel][i], self.barw, "white" )
            x += SpectrumFrame.BARGAP+self.barw

    @property
    def width(self):
        return self.bars * (SpectrumFrame.BARGAP+self.barw)

class VU2chFrame(Frame):
    def __init__(self, bounds, platform, display, scale):
        geo   = Geometry(display.boundary)
        geo.scale( (scale, 1.0) )   # make the VU Screen scale width
        Frame.__init__(self, geo.coords, platform, display)
        limits = ((0.3,"white"), (0.6,"grey"), (0.8,"red"))
        self += VUFrame(geo.coords, platform, display, 'left', limits )
        self += VUFrame(geo.coords, platform, display, 'right', limits )
        self += TextFrame(display.boundary, platform, display, 'top', "45")
        self += OutlineFrame(geo.coords, platform, display)
        self.check()

class VUV2chFrame(Frame):
    def __init__(self, bounds, platform, display, scale):
        geo   = Geometry(display.boundary)
        geo.scale( (scale, 1.0) )   # make the VU Screen scale width
        Frame.__init__(self, geo.coords, platform, display)
        limits = ((0.3,"white"), (0.6,"grey"), (0.8,"red"))
        self += VUVFrame(geo.coords, platform, display, 'left', limits )
        self += VUVFrame(geo.coords, platform, display, 'right', limits )
        self += TextFrame(display.boundary, platform, display, 'top',"45")
        self += OutlineFrame(geo.coords, platform, display)
        self.check()

class Spectrum2chFrame(Frame):
    def __init__(self, bounds, platform, display, scale):
        geo   = Geometry(display.boundary)
        geo.scale( (scale, 1.0) )   # make the VU Screen scale width
        Frame.__init__(self, geo.coords, platform, display)
        self += SpectrumFrame(geo.coords, platform, display, 'left', 0.5 )
        self += SpectrumFrame(geo.coords, platform, display, 'right', 0.5 )
        # self += TextFrame(display.boundary, platform, display, "45")
        self.check()

""" Screen classes - these are top level frames comprising frames of frames at full display size """
