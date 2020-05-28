#!/usr/bin/env python
"""
 Test harness for the base frame and geometry

 Part of mVista preDAC2 project

 v1.0 Baloothebear4 May 2020


"""

from framecore import Geometry, Frame
from frames import *
from platform import Platform
import time

"""
    Frame & Geometry Test code
"""

class Frame_1(Frame):
    def __init__(self, bounds, platform, display, V, H):
        Frame.__init__(self, platform=platform, bounds=bounds, display=display, scalers=(0.5,0.5), Valign='top', Halign='left')
        self.font   = make_font("arial.ttf", self.h*0.5)


    def draw(self, basis):
        self.display.outline( basis, self, outline="white")
        self.display.drawFrameLVCentredtext(basis, self, "Frame 1", self.font)
        print("Frame_1.draw>", self)

class Frame_2(Frame):
    def __init__(self, bounds, platform, display, V, H):
        Frame.__init__(self,platform=platform, bounds=bounds, display=display, scalers=(0.5,0.5), Valign='bottom', Halign='centre')
        self.font   = make_font("arial.ttf", self.h*0.5)

    def draw(self, basis):
        self.display.outline( basis, self, outline="white")
        self.display.drawFrameLVCentredtext(basis, self, "Frame 2", self.font)
        print("Frame_2.draw>", self)

class testScreen1(Frame):
    def __init__(self, platform, display):
        Frame.__init__(self, display.boundary, platform, display, scalers= (0.5,1.0), Halign="right", Valign="bottom")
        print("TestScreen>", self)
        self += Frame_1(self.abcd, platform, display, V='bottom', H='left')
        self += Frame_2(self.abcd, platform, display, V='bottom', H='left')
        self.check()

class testScreen2(Frame):
    def __init__(self, platform, display):
        Frame.__init__(self, display.boundary, platform, display)
        self += VolumeSourceFrame(display.boundary, platform, display, 0.3, 'right')

        self += VUV2chFrame(display.boundary, platform, display, 0.3, 'centre')
        self += SourceIconFrame(display.boundary, platform, display, 0.4, 'left')
        self.check()

class testScreen3(Frame):
    def __init__(self, platform, display):
        Frame.__init__(self, display.boundary, platform, display)
        self += SpectrumFrame(self.coords, platform, display, 'left', 0.3 )
        self += dbVolumeSourceFrame(display.boundary, platform, display, 0.4, 'centre')
        self += SpectrumFrame(self.coords, platform, display, 'right', 0.3 )

        self.check()

class testScreen4(Frame):
    def __init__(self, platform, display):
        Frame.__init__(self, display.boundary, platform, display)

        self += VolumeSourceFrame(display.boundary, platform, display, 0.3, 'right')
        self += Spectrum2chFrame(display.boundary, platform, display, 0.7, 'left')
        self.check()

class testScreen5(Frame):
    def __init__(self, platform, display):
        Frame.__init__(self, display.boundary, platform, display)


        self += TextFrame(display.boundary, platform, display, 'middle', 1.0, "Welcome to \npreDAC preamp")
        # self += MenuFrame(display.boundary, platform, display)

        self.check()

def frametest(display):

    # frames = (VolumeAmountFrame, TextFrame, MenuFrame, SourceIconFrame, VUFrame, SpectrumFrame)   # create a list of all screens to test one by one
    scaled_frames = (VUVFrame, SpectrumFrame)
    # frames = (VU2chFrame, VUV2chFrame, Spectrum2chFrame)
    limits = ((0.3,"white"), (0.6,"grey"), (0.8,"red"))

    p = Platform()
    if display=='int':
        d = p.internaldisplay
    else:
        d = p.frontdisplay

    geo   = Geometry(d.boundary)
    geo.scale( (1.0, 1.0) )   # make the  Screen scale width
    # for f in scaled_frames:
    # f = VUV2chFrame
    # # a = f(geo.coords, p, d, 'left', limits )
    # a = f(geo.coords, p, d, 0.3 )

    # f = SpectrumFrame
    # a = f(geo.coords, p, d, 'left', 0.4 )
    # print( "%s initialised: %s" % (type(f).__name__, a) )
    # f = Spectrum2chFrame
    # a = f(geo.coords, p, d, 1.0 )
    # print( "%s initialised: %s" % (type(f).__name__, a) )

    # f = VolumeSourceFrame
    # a = f(geo.coords, p, d, 0.2, 'right' )

    a = testScreen1(p, d)
    # print( "%s initialised: %s" % (type(f).__name__, a) )

    d.draw(a.draw)

    print( "Drawn: %s" % ( a) )
    # time.sleep(3)

    #
    #
    # a = testScreen(p, d)
    # print( "testScreen initialised: ", a, p )
    # p.internaldisplay.draw(a.draw)
    # time.sleep(3)
    #
    # a = testVUScreen(p, d, 0.6)
    # print( "VUScreen initialised: ", a, p )
    # for i in range(5):
    #     d.draw(a.draw)
    #
    #     print( "testScreen draw executed>", i)
    #     time.sleep(1)

def screentest(display):

    p = Platform()
    if display=='int':
        d = p.internaldisplay
    else:
        d = p.frontdisplay
    print ("Platform initialised>", p)

    screens = (SourceIconFrame, VolumeSourceFrame, dbVolumeSourceFrame, VU2chFrame, VUV2chFrame)
    horz    = ('left', 'centre', 'right')
    scale   = (0.3, 0.5)
    for screen in screens:
        for h in horz:
            for s in scale:
                a = screen(d.boundary, p, d, s, h)
                print( "%s initialised: %s" % (type(screen).__name__, a) )
                d.draw(a.draw)
                print( "%s drawn: %s" % (type(screen).__name__, a) )
                time.sleep(1)

    screens = (testScreen1, testScreen2, testScreen3, testScreen4, testScreen5)
    for screen in screens:
        a = screen(p, d)
        print( "%s initialised: %s" % (type(screen).__name__, a) )
        d.draw(a.draw)

        print( "%s drawn: %s" % (type(screen).__name__, a) )
        time.sleep(3)


"""
Extensive test of geometry scenarios, including overlap tests
"""

def geometrytest():

    b = [64,0,128,32]
    g = Geometry(b)
    print("Geometry initialised>", g)

    g.a = 1
    g.b = 2
    g.c = 3
    g.d = 4
    print("Geometry coords changed>", g)

    try:
        g.a = -1
        print("Geometry coords changed>", g)
    except Exception as e:
        print("Geometry exception ",e)

    try:
        g.b = 200
        print("Geometry coords changed>", g)
    except Exception as e:
        print("Geometry exception ",e)

    try:
        g.c = 300
        print("Geometry coords changed>", g)
    except Exception as e:
        print("Geometry exception ",e)

    try:
        g.d = -3
        print("Geometry coords changed>", g)
    except Exception as e:
        print("Geometry exception ",e)


    print("Geometry: w %s, h %s, wh %s, abcd %s, xy %s > %s" % (g.w, g.h, g.wh, g.abcd, g.xy, g))


    try:
        g.resize([30,100])
        print("Geometry coords changed>", g)
    except Exception as e:
        print("Geometry exception (illegal resize) - correcgt fail",e)

    g = Geometry([0,0,100,100])

    scale=[0.5, 0.5]
    print("Scale and Resize by %s >from %s" % (scale, g))
    g.scale(scale )
    print(" to ", g)

    try:
        g.scale( [0.8, 1.3] )
        print("Geometry coords changed>", g)
    except Exception as e:
        print("Geometry exception (illegal scale)",e)

    """ move the frame relative to the top/right or bottom/left corners """
    g.resize([10,10])
    print("resize to ", g)
    xy = [0,15]
    g.move_ab(xy)
    print(" Move ab %s to %s" % (xy, g))

    xy = [20,20]
    g.move_cd(xy)
    print(" Move cd %s to %s> size %s" % (xy, g, g.wh))

    xy = [10,18]
    g.move_middle(xy[1])
    print(" Move middle %s to %s> size %s" % (xy[1], g, g.wh) )
    g.move_centre(xy[0])
    print(" Move centre %s to %s> size %s" % (xy[0], g, g.wh) )

    print("Check the geometry is still legal -- overlap test", g.check())

    g = Geometry([10,10,100,100])
    g.scale([0.5,0.5])
    print("new geometry ", g)
    print("Get the absolute coordinates, normalised to the screen>", g.coords )

    print("All Geometry tests passed\n")

# end geometry test
if __name__ == "__main__":
    try:
        geometrytest()
        # frametest('int')
        screentest('front')
    except KeyboardInterrupt:
        pass
