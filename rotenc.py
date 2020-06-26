#!/usr/bin/env python
"""
 preDAC preamplifier project

 Rotary Encoder class

     2nd version of Rotary Encoder class
     Uses locks to ensure that timing issues do not create additional bounces

 baloothebear4
 v1 Sept  2017
 v2 April 2020 - new Audio & Volume board HW

"""

import RPi.GPIO as GPIO
import time, threading

class RotaryEncoder:

    NOEVENT         = 0
    CLOCKWISE       = 1
    ANTICLOCKWISE   = 2
    BUTTONDOWN      = 3
    BUTTONUP        = 4

    # Initialise rotary encoder object
    def __init__(self, knob, callback, minmax = (0,0,0)):
        self.pinA       = knob[0]
        self.pinB       = knob[1]
        self.button     = knob[2]
        self.callback   = callback
        self.value      = minmax[2]
        self.minmax     = minmax

        # new
        self.aState     = 0
        self.bState     = 0

        self.LockRotary = threading.Lock()		# create lock for rotary switch

        GPIO.setmode(GPIO.BCM)

        # The following lines enable the internal pull-up resistors
        # on version 2 (latest) boards
        GPIO.setwarnings(True)
        # GPIO.setup(self.pinA, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # GPIO.setup(self.pinB, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # GPIO.setup(self.button, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        GPIO.setup(self.pinA, GPIO.IN)
        GPIO.setup(self.pinB, GPIO.IN)
        GPIO.setup(self.button, GPIO.IN)#, pull_up_down=GPIO.PUD_UP)

        # Add event detection to the GPIO inputs
        GPIO.add_event_detect(self.pinA, GPIO.RISING, callback=self.switch_event, bouncetime=5)
        GPIO.add_event_detect(self.pinB, GPIO.RISING, callback=self.switch_event, bouncetime=5)
        GPIO.add_event_detect(self.button, GPIO.BOTH, callback=self.button_event, bouncetime=5)

        print("RotaryEncoder.__init__> OK", knob, minmax)


    def switch_event(self, pin):

        self.rotary_a = self.getSwitchState(self.pinA)
        self.rotary_b =	self.getSwitchState(self.pinB)
        # print "RotaryEncoder> switch_eventB", self.aState, self.bState
        self.checkRotEnc(pin)


    # Push button up event
    def button_event(self,button):
        # print "RotaryEncoder.button_event> GPIO", button
        self.LockRotary.acquire()
        if self.getSwitchState(self.button):
        	event = self.BUTTONUP
        else:
        	event = self.BUTTONDOWN

        self.callback(event) #, self.value)
        self.LockRotary.release()

    # Get a switch state
    def getSwitchState(self, switch):
        s = GPIO.input(switch)
        # print "getSwitchState>", switch, s
        return  s

    def checkRotEnc(self, pin ):
        event = RotaryEncoder.NOEVENT

        if self.aState == self.rotary_a and self.bState == self.rotary_b:		# Same interrupt as before (Bouncing)?
            # print "bounce"
            return										# ignore interrupt!

        self.aState = self.rotary_a								# remember new state
        self.bState = self.rotary_b								# remember new state

        if self.rotary_a or self.rotary_b:						# Both one active? Yes -> end of sequence
            self.LockRotary.acquire()						# get lock
            if pin == self.pinB:							# Turning direction depends on
                if self.value < self.minmax[1]: self.value +=1
                event = RotaryEncoder.CLOCKWISE
            else:										# so depending on direction either
                if self.value > self.minmax[0]: self.value -=1
                event = RotaryEncoder.ANTICLOCKWISE
            self.LockRotary.release()						# and release lock

        if event == RotaryEncoder.CLOCKWISE or event == RotaryEncoder.ANTICLOCKWISE:
            # print"Counter: ", self.counter, " Event ", event
            self.LockRotary.acquire()
            self.callback(event) #, self.value)
            self.LockRotary.release()

# End of RotaryEncoder class

count=0
def buttonpress(a, v):
    global count

    if a == RotaryEncoder.CLOCKWISE:
        # count +=1
        ev = 'Clockwise'
    elif a == RotaryEncoder.ANTICLOCKWISE:
        # count -=1
        ev = 'Anti-clockwise'
    elif a == RotaryEncoder.BUTTONUP:
        ev = 'Button up'
    elif a == RotaryEncoder.BUTTONDOWN:
        ev = 'Button down'

    print("Rot enc event ", a, ev , v)


def main():
    '''
    Test harness for the RotaryEncoder and Volume classes
    '''
    KNOBS        = { 'RHS': [16, 26, 13, '/dev/input/event0'], \
                     'LHS': [27, 22, 17, '/dev/input/eventTBC'] }
    #volume knob
    PIN_A        = 26
    PIN_B        = 16
    BUTTON       = 13

    #control knob
    # PIN_A        = 22 	# Pin 8
    # PIN_B        = 27	# Pin 10
    # BUTTON       = 17	# Pin 7
    r      = RotaryEncoder(KNOBS['LHS'], buttonpress, (0, 99, 20) )


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
