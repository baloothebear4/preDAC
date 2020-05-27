#!/usr/bin/env python
"""
 Test harness for geometry class

 Part of mVista preDAC2 project

 v1.0 Baloothebear4 May 2020

"""

from frametest import Geometry

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

    print("Check the geometry is still legal", g.check())

    g = Geometry([10,10,100,100])
    g.scale([0.5,0.5])
    print("new geometry ", g)
    print("Get the absolute coordinated, normalised to the screen>", g.norm() )


if __name__ == "__main__":
    try:
        print( "Geometry class test")
        geometrytest()

    except KeyboardInterrupt:
        pass
