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
    def __init__(self, pinA, pinB, button, callback):
        self.pinA       = pinA
        self.pinB       = pinB
        self.button     = button
        self.callback   = callback

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
        GPIO.setup(self.button, GPIO.IN)

        # Add event detection to the GPIO inputs
        GPIO.add_event_detect(self.pinA, GPIO.FALLING, callback=self.switch_event)
        GPIO.add_event_detect(self.pinB, GPIO.FALLING, callback=self.switch_event)
        GPIO.add_event_detect(self.button, GPIO.BOTH, callback=self.button_event) #, bouncetime=0)


    def switch_event(self, pin):

        self.rotary_a = self.getSwitchState(self.pinA)
        self.rotary_b =	self.getSwitchState(self.pinB)
        # print "RotaryEncoder> switch_eventB", self.aState, self.bState
        self.checkRotEnc(pin)


    # Push button up event
    def button_event(self,button):
        # print "RotaryEncoder.button_event> GPIO", button
        if self.getSwitchState(self.button):
        	event = self.BUTTONUP
        else:
        	event = self.BUTTONDOWN
        self.callback(event)


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
                event = RotaryEncoder.CLOCKWISE
            else:										# so depending on direction either
                event = RotaryEncoder.ANTICLOCKWISE
            self.LockRotary.release()						# and release lock

        if event == RotaryEncoder.CLOCKWISE or event == RotaryEncoder.ANTICLOCKWISE:
            # print"Counter: ", self.counter, " Event ", event
            self.LockRotary.acquire()
            self.callback(event)
            self.LockRotary.release()

# End of RotaryEncoder class

count=0
def buttonpress(a):
    global count

    if a == RotaryEncoder.CLOCKWISE:
        count +=1
        ev = 'Clockwise'
    elif a == RotaryEncoder.ANTICLOCKWISE:
        count -=1
        ev = 'Anti-clockwise'
    elif a == RotaryEncoder.BUTTONUP:
        ev = 'Button up'
    elif a == RotaryEncoder.BUTTONDOWN:
        ev = 'Button down'

    print "Rot enc event ", ev , count

def main():
    '''
    Test harness for the RotaryEncoder and Volume classes
    '''

    r = RotaryEncoder(buttonpress)

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
