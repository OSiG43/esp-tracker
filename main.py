# main.py
import machine

import commanager
import constants
import sdmanager
import gpsmanager
import uasyncio as asyncio

from machine import Pin

gpsManager = gpsmanager.GPSManager(2)

comManager = commanager.comManager()

sdManager = sdmanager.SDManager(constants.PIN_SCK, constants.PIN_MOSI, constants.PIN_MISO, constants.PIN_SDCardCS, 4)
sdManager.loadSettings()

isContact = None
contactPin = None


def init():
    global isContact, contactPin
    contactPin = Pin(constants.PIN_CONTACT,Pin.IN,Pin.PULL_UP) # Todo : vérifier la pullup
    isContact = contactPin.value()
    contactPin.irq(irq_contact)


def irq_contact():
    global isContact, contactPin
    isContact = contactPin.value()

def main():
    while True:
        if not contactPin.value():
            sleepMode()
        else:
            runningMode()

def sleepMode():
    pass

def runningMode():
    pass


gpsManager.powerOn()
asyncio.run(gpsManager.run())
