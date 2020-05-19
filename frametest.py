

""" a data type for coordinates - converts lists to dicts and back
    - initialise from a 4 point list
    - read as 4 point list
    - write to the coordinates via setters to check legimacy

"""
class Geometry():
    def __init__(self, boundswh):
        self._abcd  = boundswh
        self.bounds = Geometry(boundswh)

    """ test if this will return a from the syntax Frame.a """
    @property
    def a(self):
        return self._abcd[0]

    @attribute
    def a.setter(self, val):
        if val >= self.bounds.a and val <= self.bounds.c:
            self._abcd[0] = val
            self.wh()
        else:
            raise ValueError('Coords.a > value exceed bounds ', val)

    @property
    def b(self):
        return self._abcd[1]

    @attribute
    def b.setter(self, val):
        if val >= self.bounds.b and val <= self.bounds.d:
            self._abcd[1] = val
            self.wh()
        else:
            raise ValueError('Coords.b > value exceed bounds ', val)

    @property
    def c(self):
        return self._abcd[2]

    @attribute
    def c.setter(self, val):
        if val >= self.bounds.a and val <= self.bounds.c:
            self._abcd[2] = val
            self.wh()
        else:
            raise ValueError('Coords.c > value exceed bounds ', val)

    @property
    def d(self):
        return self._abcd[3]

    @attribute
    def d.setter(self, val):
        if val >= self.bounds.b and val <= self.bounds.d:
            self._abcd[3] = val
            self.wh()
        else:
            raise ValueError('Coords.d > value exceed bounds ', val)

    @property
    def w(self):
        return self._wh[0]

    @attribute
    def w.setter(self, val):
        if val <= self.bounds.w:
            self._wh[0] = val
        else:
            raise ValueError('Coords.w > value exceed bounds ', val)

    @property
    def h(self):
        return self._wh[1]

    @attribute
    def h.setter(self, val):
        if val <= self.bounds.h:
            self._wh[1] = val
        else:
            raise ValueError('Coords.h > value exceed bounds ', val)

    @property
    def abcd(self):
        return self._abcd

    @attribute
    def abcd.setter(self, wh):
        self.a = 0
        self.b = 0
        self.c = wh[0]
        self.d = wh[1]

    @property
    def xy(self):
        return( (self.a, self.b) )

    """ calculating the size will need to be more dynamic if the drawing could exceed the bounds """
    @property
    def wh(self):
        self._wh[0] = self.c - self.a
        self._wh[1] = self.d - self.b
        return( self._wh )

    """ scale the geometry according the given boundary and w, h scaling factors
        leave the bottom, left as is and change the top, right accordingly
    """
    def __mul__(self, wh):
        self.c *= wh[0]
        self.d *= wh[1]
        return(self.wh)

    def scale(self, scalers):
        self.c *= scalers[0]
        self.d *= scalers[1]

    """ move the frame relative to the top/right or bottom/left corners """
    def move_ab(self, xy):
        self.a = xy[0]
        self.b = xy[1]
        self.c = xy[0]+self.w
        self.d = xy[1]+self.h

    def move_cd(self, xy):
        self.a = xy[0]-self.w
        self.b = xy[1]-self.h
        self.c = xy[0]
        self.d = xy[1]

    def move_middle(self, y):
        #y coordinate of the
        self.b = y-self.h/2
        self.d = y+self.h/2

    def move_centre(self, x):
        #x coordinate
        self.a = x-self.w/2
        self.c = x+self.w/2


    """ normalise the coordinate system to that of the actual display
        i.e:  (0,0) is bottom, left to (abs_h,0) is bottom left
    """
    def norm(self, abs_h):
        return( (abs_h-self._abcd.a, self._abcd.b, abs_h-self._abcd.c, self._abcd.d ))

    def check(self):
        # check that the enclosed rectangle fits within the given boundary. Properties to test
        # 1. the area should not be greater (not needed)
        # 2. the coordinates do not exceed the boundary space
        if self.a < self.bounds.a or self.c > self.bounds.c or \
           self.b < self.bounds.a or self.d > self.bounds.d:
           raise ValueError('Geometry.check > out of bounds')
           return False
        else:
           return True

    def __str__(self):
        return( "(%3.0d, %3.0d, %3.0d, %3.0d)" % (self._abcd.a, self._abcd.b, self._abcd.c, self._abcd.d))


"""
    - manages the alignment of a Frame within a Screen
    - establishes the actual size based on the bounds given
    - checks to see the coordinates given do not take the Frame outside the bounds
    - assumes a Frame is a rectangle and sits in a Screen
    - bounds and scale are ordered pairs ie tuples (x, y)
"""
class Frame(Geometry):
    """ scalars is a tuple (w%, h%) where % is of the bounds eg (0.5, 1.0) is half the width, full height
        bounds is list of the bottom left and upper right corners eg (64,32)
    """
    def __init__(self, boundswh, scalers, Valign='bottom', Halign='left'):
        Geometry.__init__(self, boundswh)
        self.scale(scalars)
        self.V = Valign
        self.H = Halign

    """ align will use the anchors: 'top, middle, bottom', 'left, centre, right' to set the
        coordinates of the Frame within the boundary """
    def align(self):
        # parse V and H alignment anchors
        # check that the frame is still in bounds
        # this is where the frame coordiantes are setup
        if V   == 'top':
            self.move_cd( self.c, self.bounds.d)
            # move so that self.d = self.bounds.d
        elif V == 'middle':
            self.move_middle( self.bounds.d/2 )
            # move so that middle(self) = middle(self.bounds) : middle =
        elif V == 'bottom':
            self.move_ab( self.a, self.bounds.b)
            # move so that self.b = self.bounds.b
        else:
            raise ValueError('Frame.align: unknown vertical anchor->', V)

        if H   == 'left':
            self.move_ab( self.bounds.a, self.b)
            # move so that self.a = self.bounds.a
        elif H == 'centre':
            self.move_centre( self.bounds.c/2)
            # move so that centre(self) = centre(self.bounds)
        elif H == 'right':
            self.move_cd( self.bounds.c, self.d)
            # move so that self.c = self.bounds.c
        else:
            raise ValueError('Frame.align: unknown horz anchor->', H)

    """ test if the frame overlaps the one given """
    def overlaps(self, f):
        if   self.a < f.c:
            print('Frame.overlap: left side overlap')
            return True
        elif self.c > f.a:
            print('Frame.overlap: right side overlap')
            return True
        elif self.b < f.d:
            print('Frame.overlap: bottom side overlap')
            return True
        elif self.d > f.b:
            print('Frame.overlap: top side overlap')
            return True
        else:
            return False

    """ *** Each frame should have draw method """
    def draw(self, device):
        print("Frame.draw> not implemented")

class Frame_a(Frame):
    def __init__(self, device):
        Frame.__init__(self, boundswh=[64,32], scalers=(1.0,0.5), Valign='top', Halign='left')
        print("Frame_a>", self)

    def draw(self, device):
        print("Frame_a.draw> can't draw")

class Frame_b(Frame):
    def __init__(self, device):
        Frame.__init__(self,boundswh=(64,32), scalers=(1.0,0.5), Valign='bottom', Halign='left') )
        print("Frame_b>", self)

    def draw(self, device):
        print("Frame_b.draw> can't draw")


""" Screens collates a set of frames which can be positioned and then drawn
    using += operation makes this simpler to build a list of frames
    which is used for the alignment and drawing operations """

class Screen(Frame):
    def __init__(self, device):
        self.frames = []
        self.device = device

    def __iadd__(self, frame):
        self.frames.append(frame)
        return self

    def align(self):
        for f in self.frames:
            f.align()
        self.check()

    def draw(self):
        for f in self.frames:
            f.draw(device)

    def __str__(self):
        text = ''
        for f in self.frames:
            text += "Frame %s > %s" % (f.__name__, f)
        return( text )

    """ goes through the frames to see if they overlap """
    def check(self):
        for f1 in self.frames:
            for f2 in self.frames:
                if f1 != f2:
                    if f1.overlaps(f2):
                        raise ValueError('Screen.check> frame %s overlaps %s' %(f1.__name__, f2.__name__) )

class testScreen(Screen):
    def __init__(self):
        Screen.__init_()

        self.screen += Frame_a(V='bottom', H='left')
        self.screen += Frame_b(V='bottom', H='left')


if __name__ == "main":
    a = testScreen(device=None)
    print( a )
