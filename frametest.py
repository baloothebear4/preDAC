#!/usr/bin/env python
"""
 Test harness for the base frame and geometry

 Part of mVista preDAC2 project

 v1.0 Baloothebear4 May 2020


"""

from framecore import Geometry, Frame

"""
    Frame & Geometry Test code
"""



class Frame_1(Frame):
    def __init__(self, device):
        Frame.__init__(self, boundswh=[64,32], scalers=(1.0,0.5), Valign='top', Halign='left')
        print("Frame_a>", self)

    def draw(self, device):
        print("Frame_a.draw> can't draw")

class Frame_2(Frame):
    def __init__(self, device):
        Frame.__init__(self,boundswh=(64,32), scalers=(1.0,0.5), Valign='bottom', Halign='left') )
        print("Frame_b>", self)

    def draw(self, device):
        print("Frame_b.draw> can't draw")

class testScreen1(Screen):
    def __init__(self):
        Screen.__init_()
        self.screen += Frame_a(V='bottom', H='left')
        self.screen += Frame_b(V='bottom', H='left')
        self.check()

class testVUScreen(Frame):
    def __init__(self, platform, display):
        Frame.__init__(self, display.boundary, platform, display)
        self += Frame_1(display.boundary, platform, display)
        # self += Frame_2(display.boundary, platform, display)
        # self += VolumeAmountFrame(display.boundary, platform, display)

        self += TextFrame(display.boundary, platform, display, "Welcome")
        # self += MenuFrame(display.boundary, platform, display)
        # self += SourceIconFrame(display.boundary, platform, display)
        self += VUScreen(platform, display)
        self.check()

def frametest(display):

    # frames = (VolumeAmountFrame, TextFrame, MenuFrame, SourceIconFrame, VUFrame, SpectrumFrame)   # create a list of all screens to test one by one
    scaled_frames = (VUVFrame, SpectrumFrame)
    # frames = (VU2chFrame, VUV2chFrame, Spectrum2chFrame)

    p = Platform()
    if display=='int':
        d = p.internaldisplay
    else:
        d = p.frontdisplay

    for f in scaled_frames:
        a = f(p, d, 1.0)
        print( "%s initialised: %s" % (type(i).__name__, a) )
        d.draw(a.draw)

        print( "%s drawn: %s" % (type(i).__name__, a) )
        time.sleep(3)

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

def screentest():

    screens = ()
    p = Platform()
    print ("Platform initialised>", p)
    if display=='int':
        d = p.internaldisplay
    else:
        d = p.frontdisplay

    for i in range(len(screens):
        a = testVUScreen(p, d, 0.6)
        print( "%s initialised: %s" % (type(i).__name__, a) )
        d.draw(a.draw)

        print( "%s drawn: %s" % (type(i).__name__, a) )
        time.sleep(3)

"""
Extensive test of geometry scenarios, including overlap tests
"""

def geometrytest():

    b = [0,0,64,32]
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
        print("Geometry exception (illegal resize)",e)


    scale=[0.8, 0.8]
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
        frametest()
    except KeyboardInterrupt:
        pass
