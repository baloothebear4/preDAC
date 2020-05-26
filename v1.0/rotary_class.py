#!/usr/bin/env python
#
# Raspberry Pi Rotary Encoder Class
# $Id: rotary_class.py,v 1.2 2014/01/31 13:34:48 bob Exp $
#
# Author : Bob Rathbone
# Site   : http://www.bobrathbone.com
#
# This class uses standard rotary encoder with push switch
#
#

import RPi.GPIO as GPIO
import time

class RotaryEncoder:

    CLOCKWISE=1
    ANTICLOCKWISE=2
    BUTTONDOWN=3
    BUTTONUP=4

    # Initialise rotary encoder object
    def __init__(self,pinA,pinB,button,callback):
        self.pinA = pinA
        self.pinB = pinB
        self.button = button
        self.callback = callback

        # new
        self.counter = 0
        self.aState = 0
        self.bState = 0
        self.aLastState= 0
        self.moved = 0  #track the current state

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
        GPIO.add_event_detect(self.pinA, GPIO.FALLING, callback=self.switch_eventA)
        GPIO.add_event_detect(self.pinB, GPIO.FALLING, callback=self.switch_eventB)
        GPIO.add_event_detect(self.button, GPIO.BOTH, callback=self.button_event, bouncetime=20)

    def switch_eventA(self,switch):

        self.aState = self.getSwitchState(self.pinA)
        self.bState =	self.getSwitchState(self.pinB)
        # print "RotaryEncoder> switch_eventA", self.aState, self.bState
        self.checkRotEnc(self.pinA)

    def switch_eventB(self,switch):

        self.rotary_a = self.getSwitchState(self.pinA)
        self.rotary_b =	self.getSwitchState(self.pinB)
        # print "RotaryEncoder> switch_eventB", self.aState, self.bState
        self.checkRotEnc(self.pinB)


    # Push button up event
    def button_event(self,button):
        if GPIO.input(button):
        	event = self.BUTTONUP
        else:
        	event = self.BUTTONDOWN
        self.callback(event)


    # Get a switch state
    def getSwitchState(self, switch):
        s = GPIO.input(switch)
        # print "getSwitchState>", switch, s
        return  s

    def checkRotEnc(self, firstPin ):
        event = 0

    # // If the previous and the current state of the ROTAPIN are different, that means a Pulse has occured
    # // Only respond to falling edges
        if ( self.moved ):


            if (self.firstMoved == self.pinA ):# and self.bState == 1):
            	self.counter += 1
            	event = RotaryEncoder.CLOCKWISE
            	self.moved = 0
            elif(self.firstMoved == self.pinB): # and self.bState == 0):
            	self.counter -=1
            	event = RotaryEncoder.ANTICLOCKWISE
            	self.moved = 0
            else:
            	print "glitch state"


        else:
            # print "First move =", firstPin
            self.firstMoved = firstPin
            self.moved = 1

        if event == RotaryEncoder.CLOCKWISE or event == RotaryEncoder.ANTICLOCKWISE:
            # print"Counter: ", self.counter, " Event ", event
            self.callback(event)

# End of RotaryEncoder class
