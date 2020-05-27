#!/usr/bin/env python
"""
 Test harness for the oled screens

 Part of mVista preDAC2 project

 v1.0 Baloothebear4 May 2020


"""

from framecore import Geometry, Frame

oled_height = 32
oled_width  = 128
bottom      = oled_height
top         = 0
bar_width   = 3
bar_gap     = 2
bar_space   = bar_gap + bar_width
bars        = int(oled_width / bar_space)


""" test code """
def draw_bar(self,col, h):
    with canvas(self.device) as draw:
        draw.rectangle((col, oled_height-h, col + bar_width, bottom), outline="blue", fill="white")
    # print "draw_bar at ", col," ",h
def draw_line(self,col, h):
    with canvas(self.device) as draw:
        draw.line((col, oled_height-h, col + bar_width, bottom), fill="white")

def draw_bar2(self,draw, col, h):
    ''' draws up to 32 pixels high, OLED.bar wide '''
    x = col * bar_space
    draw.rectangle((x, oled_height-h, x + bar_width, bottom), outline="blue", fill="blue")

def draw_screen(self,data):
    self.calcDisplaytime()
    # print("draw_screen> ", data)
    bars = bars
    if len(data)< bars: bars = len(data)

    with self.regulator:
        with canvas(self.device) as c:
            for i in range(bars):
                self.draw_bar2(c, i, 32*(35+data[i])/110 )
    self.calcDisplaytime(False)


if __name__ == "__main__":
    try:
        draw_screen
    except KeyboardInterrupt:
        pass
