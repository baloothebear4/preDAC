#!/usr/bin/env python
"""
 2nd version of Rotary Encoder class

 Uses locks to ensure that timing issues do not create additional bounces

 Baloothebear4 April 2020


"""

import RPi.GPIO as GPIO
import time, threading
from   pcf8574 import PCF8574

class Volume(PCF8574):
    i2c_port = 1
    address  = 0x20
    mute_in  = 0
    dBout32  = 1
    dBout16  = 2
    dBout8   = 3
    dBout4   = 4
    dBout2   = 5
    dBout1   = 6
    testLEDout = 0
    interuptPin = 24 #pin 18
    Button      = 2

    def __init__(self):
        PCF8574.__init__(self, Volume.i2c_port, Volume.address)
        for i in range (0,8):
            print " port ", i , ' reads ', self.port[i]
            # time.sleep(0.1)

    def printPorts(self):
        print "Volume.printPorts> ", self.port


class RotaryEncoder:

    CLOCKWISE=1
    ANTICLOCKWISE=2
    BUTTONDOWN=3
    BUTTONUP=4

    # Initialise rotary encoder object
    def __init__(self,callback):
        self.pinA = 16
        self.pinB = 16
        self.button = 16
        self.callback = callback

        # new
        self.counter = 0
        self.aState = 0
        self.bState = 0
        self.aLastState= 0
        self.moved = 0  #track the current state

        self.LockRotary = threading.Lock()		# create lock for rotary switch
        self.vol = Volume()
        self.vol.printPorts()



        GPIO.setmode(GPIO.BCM)

        # The following lines enable the internal pull-up resistors
        # on version 2 (latest) boards
        GPIO.setwarnings(True)
        # GPIO.setup(self.pinA, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # GPIO.setup(self.pinB, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # GPIO.setup(self.button, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # GPIO.setup(self.pinA, GPIO.IN)
        # GPIO.setup(self.pinB, GPIO.IN)
        # GPIO.setup(self.button, GPIO.IN)

        GPIO.setup(self.vol.interuptPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # # Add event detection to the GPIO inputs
        # GPIO.add_event_detect(self.pinA, GPIO.FALLING, callback=self.switch_event)
        # GPIO.add_event_detect(self.pinB, GPIO.FALLING, callback=self.switch_event)
        # GPIO.add_event_detect(self.button, GPIO.BOTH, callback=self.button_event) #, bouncetime=0)

        GPIO.add_event_detect(self.vol.interuptPin, GPIO.BOTH, callback=self.button_event) #, bouncetime=0)


    def switch_event(self, pin):

        self.rotary_a = self.getSwitchState(self.pinA)
        self.rotary_b =	self.getSwitchState(self.pinB)
        # print "RotaryEncoder> switch_eventB", self.aState, self.bState
        self.checkRotEnc(pin)


    # Push button up event
    def button_event(self,button):
        print "RotaryEncoder.button_event> pin", button
        if self.vol.port[self.vol.Button]:
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
        event = 0

        if self.aState == self.rotary_a and self.bState == self.rotary_b:		# Same interrupt as before (Bouncing)?
            # print "bounce"
            return										# ignore interrupt!

        self.aState = self.rotary_a								# remember new state
        self.bState = self.rotary_b								# remember new state

        if self.rotary_a or self.rotary_b:						# Both one active? Yes -> end of sequence
            self.LockRotary.acquire()						# get lock
            if pin == self.pinB:							# Turning direction depends on
                # Rotary_counter += 1						# which input gave last interrupt
                event = RotaryEncoder.CLOCKWISE
            else:										# so depending on direction either
                # Rotary_counter -= 1						# increase or decrease counter
                event = RotaryEncoder.ANTICLOCKWISE
            self.LockRotary.release()						# and release lock

        if event == RotaryEncoder.CLOCKWISE or event == RotaryEncoder.ANTICLOCKWISE:
            # print"Counter: ", self.counter, " Event ", event
            self.LockRotary.acquire()
            self.callback(event)
            self.LockRotary.release()

# End of RotaryEncoder class

def buttonpress(a):
    print "Buttonpress ", a

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
