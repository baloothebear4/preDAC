#!/usr/bin/env python
"""
Test file to find the input devices and match them to the KNOBS
"""
import evdev

def matchInputDevices(deviceName):
    # returns the device event channel
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for device in devices:
        if device.name == deviceName:
            return device.path
    print("RotaryEncoder2. matchInputDevices> deviceName not found>", deviceName)
    return 0

if __name__ == '__main__':
    ips = ('gpio_ir_recv', 'rotary@5', 'rotary@16', 'rubbish')

    for input in ips:
        print("device name %s --> event %s" % (input, matchInputDevices(input)))
