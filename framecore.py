#!/usr/bin/env python
"""
 Base classes for generic Frame management
    - Geometry:  manages the coordinate system used for enclosing rectangles
    - Frame: hierarchical frames, managed for overlap and alignment


 Part of mVista preDAC2 project

 v1.0 Baloothebear4 May 202

"""

""" a data type for coordinates - converts lists to dicts and back
    - initialise from a 4 point list
    - read as 4 point list
    - write to the coordinates via setters to check legimacy

"""

from oleddriver import make_font, scaleImage

import os, time
from oleddriver import internalOLED     # used for Test purposes
from platform   import Platform         # used for Test purposes

class Geometry():
    def __init__(self, bounds=[0,0,0,0]):
        self._abcd   = [0,0]
        self._abcd   = bounds.copy()
        self._bounds = bounds
        print("Geometry.init>", self.abcd)

    """ test if this will return a from the syntax Frame.a """
    @property
    def a(self):
        return self._abcd[0]

    @a.setter
    def a(self, val):
        if val >= self._bounds[0] and val <= self._bounds[2]:
            self._abcd[0] = int(val)
        else:
            raise ValueError('Coords.a > value exceed bounds ', val)

    @property
    def b(self):
        return self._abcd[1]

    @b.setter
    def b(self, val):
        if val >= self._bounds[1] and val <= self._bounds[3]:
            self._abcd[1] = int(val)
        else:
            raise ValueError('Coords.b > value exceed bounds ', val)

    @property
    def c(self):
        return self._abcd[2]

    @c.setter
    def c(self, val):
        if val >= self._bounds[0] and val <= self._bounds[2]:
            self._abcd[2] = int(val)
        else:
            raise ValueError('Coords.c > value exceed bounds ', val)

    @property
    def d(self):
        return self._abcd[3]

    @d.setter
    def d(self, val):
        if val >= self._bounds[1] and val <= self._bounds[3]:
            self._abcd[3] = int(val)
        else:
            raise ValueError('Coords.d > value exceed bounds ', val)

    @property
    def w(self):
        return self.size(self._abcd)[0]

    @property
    def h(self):
        return self.size(self._abcd)[1]

    @property
    def abcd(self):
        return self._abcd

    @property
    def coords(self):
        return self.norm()

    @property
    def wh(self):
        return self.size(self._abcd)

    @property
    def xy(self):
        return (self.a, self.b)

    @property
    def centre(self):
        return self.normxy( ( (self.c+self.a)/2, (self.d+self.b)/2) )

    def resize(self, wh):
        self.a = self._bounds[0]
        self.b = self._bounds[1]
        self.c = wh[0]
        self.d = wh[1]

    """ calculating the size will need to be more dynamic if the drawing could exceed the bounds """
    def size(self, abcd):
        w = abcd[2] - abcd[0] + 1
        h = abcd[3] - abcd[1] + 1
        return (w,h)

    """ scale the geometry according the given boundary and w, h scaling factors
        leave the bottom, left as is and change the top, right accordingly
    """
    def scale(self, scalers):
        self.resize( [ int(self._bounds[2] * scalers[0]), int(scalers[1] * self._bounds[3]) ] )

    """ move the frame relative to the top/right or bottom/left corners """
    def move_ab(self, xy):
        w = self.w-1
        h = self.h-1
        self.a = xy[0]
        self.b = xy[1]
        self.c = xy[0]+w
        self.d = xy[1]+h

    def move_cd(self, xy):
        w = self.w-1
        h = self.h-1
        self.a = xy[0]-w
        self.b = xy[1]-h
        self.c = xy[0]
        self.d = xy[1]

    def move_middle(self, y):
        #y coordinate
        h = self.h-1
        self.b = y-h/2
        self.d = y+h/2

    def move_centre(self, x):
        #x coordinate
        w = self.w-1
        self.a = x-w/2
        self.c = x+w/2


    """
        normalise the coordinate system to that of the actual display
        this assumes that the given boundary are actual coordinates on the screen
        so the relative coordinates of the geometry are added to the bounds x,y
        this is to give an absolute coordinate for drawing
    """
    def norm(self):
        return [self._bounds[0]+self.a, self._bounds[1]+self.b, self._bounds[0]+self.c, self._bounds[0]+self.d]

    def normxy(self, xy):
        return (self._bounds[0]+xy[0], self._bounds[1]+xy[1])

    def check(self):
        # check that the enclosed rectangle fits within the given boundary. Properties to test
        # 1. the area should not be greater (not needed)
        # 2. the coordinates do not exceed the boundary space
        if self.a < self._bounds[0] or self.c > self._bounds[2] or \
           self.b < self._bounds[1] or self.d > self._bounds[3]:
           raise ValueError('Geometry.check > out of bounds')
           return False
        else:
           return True

    def __str__(self):
        return( "abcd %s, bounds %s, size %s" % (self.abcd, self._bounds, self.wh))



class Frame(Geometry):
    """
        - manages the alignment of a Frame within a Screen
        - a Screen is defined at the top most Frame
        - Frames can be nested within frames
        - the base coordinate system has (0,0) as bottom, left -> hence requires normalisation to actual screen coord system
        - Each Frame is a rectangle of given size (w,h)
        - each frame uses Geometry to resize within the bounds of the parent Frame
        - the geometry of a Frame is always relative to the parent
        - a Frame itself can contain other frames that can be positioned with the frame
        - checks are performed to see the coordinates given do not take the Frame outside the bounds
    """

    def __init__(self, bounds, platform=None, display=None, scalers=[1.0,1.0], Valign='bottom', Halign='left'):
        """
            scalars is a tuple (w%, h%) where % is of the bounds eg (0,0,64,32) is half the width, full height
            bounds is list of the bottom left and upper right corners eg (64,32)
        """
        Geometry.__init__(self, bounds)
        self.platform   = platform    #only needed by the top Frame or Screen, as is passed on draw()
        self.bounds     = Geometry(bounds)
        self.frames     = []         #Holds the stack of containing frames
        self.display    = display
        self.V          = Valign
        self.H          = Halign
        print("Frame.__init__> ", self)
        self.scale(scalers)
        self.align()


    def align(self):
        """
            align will use the anchors: 'top, middle, bottom', 'left, centre, right' to set the
            coordinates of the Frame within the boundary
        """
        # parse V and H alignment anchors
        # check that the frame is still in bounds
        # this is where the frame coordiantes are setup
        if self.V   == 'top':
            self.move_cd( (self.c, self.bounds.d) )
            # move so that self.d = self.bounds.d
        elif self.V == 'middle':
            self.move_middle( self.bounds.d/2 )
            # move so that middle(self) = middle(self.bounds) : middle =
        elif self.V == 'bottom':
            self.move_ab( (self.a, self.bounds.b) )
            # move so that self.b = self.bounds.b
        else:
            raise ValueError('Frame.align: unknown vertical anchor (top, middle, bottom)->', self.V)

        if self.H   == 'left':
            self.move_ab( (self.bounds.a, self.b) )
            # move so that self.a = self.bounds.a
        elif self.H == 'centre':
            self.move_centre( self.bounds.c/2)
            # move so that centre(self) = centre(self.bounds)
        elif self.H == 'right':
            self.move_cd( (self.bounds.c, self.d) )
            # move so that self.c = self.bounds.c
        else:
            raise ValueError('Frame.align: unknown horz anchor (left, centre, right)->', self.H)

    def __iadd__(self, frame):
        self.frames.append(frame)
        return self

    def draw(self, c):
        for f in self.frames:
            f.draw(c)

    def frametext(self, f):
        return "%-10s > %s" % (type(f).__name__, super(Frame, f).__str__())

    def __str__(self):
        text = '%s Frame stack>' % type(self).__name__
        for f in self.frames:
            text += "\n  " + self.frametext( f )
        return text

    """ goes through the frames to see if they overlap  """
    """ test if the frame overlaps the one given        """
    def overlaps(self, f):
        print("Frame.overlap> SRC algorithm")
        if   self.c >= f.a and f.c>= self.a and self.d >= f.b and f.d >= self.b:
            print('Frame.overlap> detected')
            return True
        else:
            return False

    # def overlaps(self, f):  #l1, r1, l2, r2):
    #        print("Frame.overlap> import algorithm")
    #     # If one rectangle is on left side of other
    #     if(self.a >= f.c or f.a >= self.c):
    #         print("left/right overlap")
    #         return True
    #
    #     # If one rectangle is above other
    #     if(self.d <= f.b or f.d <= self.b):
    #         print("top/bottom overlap")
    #         return True
    #
    #     return False

    # alternative algorithm that uses heavy lifting and shows the exact coordinates that overlap
    # def overlaps(self, f):
            # print("Frame.overlap> SRC brute force algorithm")
    #     a = [[x, y] for x in [x1 for x1 in range(self.a , self.c )] for y in [y1 for y1 in range(self.b , self.d )]]
    #     b = [[x, y] for x in [x for x in range(f.a , f.c )] for y in [y for y in range(f.b , f.d )]]
    #
    #     # print ("%s =%s\n%s =%s" %(self, a, f, b))
    #
    #     overlaps = [ bcoords for bcoords in b if bcoords in a]
    #
    #     if len(overlaps) > 0:
    #         print('Frame.overlap: at ',overlaps)
    #         return True
    #     else:
    #         return False

    def check(self):
        print("%s Frame overlap check - takes time...>" % type(self).__name__)
        ok = True
        for f1 in self.frames:
            if f1 == self: continue
            if f1 != f2:
                if f1.overlaps(f2):
                    print('Frame.check> frame %s overlaps %s' %(type(f1).__name__, type(f2).__name__) )
                    ok = False
        return ok

#End of Frame class
