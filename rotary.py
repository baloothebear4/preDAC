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





import time, threading
import evdev
from pyky040 import pyky040
import RPi.GPIO as GPIO

class RotaryEncoder2:

    NOEVENT         = 0
    CLOCKWISE       = 1
    ANTICLOCKWISE   = 2
    BUTTONDOWN      = 3
    BUTTONUP        = 4

    # Initialise rotary encoder object
    def __init__(self, knob, event_callback, minmax=(0,99,40)):
        """ knob   = (pin A, pin B, button, device)
            minmax = (min, max, initial)   """
        self.knob             = knob
        self.event_callback   = event_callback
        self.value            = minmax[2]

        self.rotenc = pyky040.Encoder(device=self.matchInputDevice(knob[3]))

        """ setup Knob button """
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.knob[2], GPIO.IN)#, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(self.knob[2], GPIO.BOTH, callback=self.button_event, bouncetime=5)

        """ set up the rotary encoder driver - NB: see /boot/config.txt for overlay parameters """
        self.rotenc.setup(scale_min=minmax[0], scale_max=minmax[1], step=1.0, inc_callback=self.inc, dec_callback=self.dec)

        # Launch the listener in a thread
        self.rotenc_thread = threading.Thread(target=self.rotenc.watch)
        self.rotenc_thread.start()
        # self.rotenc.watch()

        print("RotaryEncoder2.__init__> OK", knob, minmax)


    def inc(self, a):
        self.value = a
        # print("inc >", a)
        self.event_callback(RotaryEncoder2.CLOCKWISE) #, int(self.value))

    def dec(self, a):
        self.value = a
        # print("dec >", a)
        self.event_callback(RotaryEncoder2.ANTICLOCKWISE) #, int(self.value))

    # Push button up event
    def button_event(self,button):
        # print "RotaryEncoder2.button_event> GPIO", button
        # self.LockRotary.acquire()
        if GPIO.input(self.knob[2]):
        	event = RotaryEncoder2.BUTTONUP
        else:
        	event = RotaryEncoder2.BUTTONDOWN

        self.event_callback(event) #, int(self.value))
        # self.LockRotary.release()

    def matchInputDevice(self, deviceName):
        # returns the device event channel
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for device in devices:
            if device.name == deviceName:
                return device.path
        print("RotaryEncoder2.matchInputDevice> deviceName not found>", deviceName)
        return 0

# End of RotaryEncoder2 class

""" Test Code """

count=0
def rotevent(a, v):
    if a == RotaryEncoder2.CLOCKWISE:
        ev = 'Clockwise'
    elif a == RotaryEncoder2.ANTICLOCKWISE:
        ev = 'Anti-clockwise'
    elif a == RotaryEncoder2.BUTTONUP:
        ev = 'Button up'
    elif a == RotaryEncoder2.BUTTONDOWN:
        ev = 'Button down'
    else:
        ev = 0

    print("Rot enc event ", a , v)


def main():
    '''
    Test harness for the RotaryEncoder and Volume classes
    '''

    KNOBS        = { 'RHS': [16, 26, 13, '/dev/input/event0'], \
                     'LHS': [27, 22, 17, '/dev/input/eventTBC'] }
    # #volume knob (RHS)
    # PIN_A        = 26
    # PIN_B        = 16
    # BUTTON       = 13
    # volknob = '/dev/input/event0'

    #control knob (LHS)
    # PIN_A        = 22 	# Pin 8
    # PIN_B        = 27	# Pin 10
    # BUTTON       = 17	# Pin 7
    # r      = RotaryEncoder(volknob, buttonpress )

    r      = RotaryEncoder2(KNOBS['RHS'], rotevent, (0, 50, 25))


    loops = 0

    while(loops<1000):
        start = time.time()

        loops += 1
        time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
