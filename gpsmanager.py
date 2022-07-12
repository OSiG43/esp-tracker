
import machine
import uasyncio as asyncio

import logger
import micropyGPS
from micropython import const

from constants import PIN_GPS_POWER
from machine import Pin
import utime


class GPSManager:

    UBX_BCK_MODE = const(b"\xB5\x62\x02\x41\x08\x00\x00\x00\x00\x00\x02\x00\x00\x00\x4D\x3B")
    UBX_RESTART = const(b"\xB5\x62\x02\x41\x08\x00\x00\x00\x00\x00\x01\x00\x00\x00\x4C\x37")

    def __init__(self, uartId):
        self.uart = machine.UART(uartId, 9600) # On initialise une liaison série à 9600 bauds
        self.uGPS = micropyGPS.MicropyGPS(2)  # On initialise le parser NMEA en indiquant un fuseau UTC+2
        self.powerPin = Pin(PIN_GPS_POWER, Pin.OUT)
        self.powerPin.value(0)
        self.lastDataRxTime = -1

    def update(self):
        sentence = self.uart.readline()

    async def run(self):
        while True:
            while self.uart.any():
                try:
                    self.uGPS.update(self.uart.read(1).decode(const('utf-8')))     # Parfois un caractère non présent dans l'utf-8 arrive (erreur de réception), une erreur est donc levé
                    self.lastDataRxTime = utime.ticks_ms()
                except UnicodeError:
                    logger.warn(const("Bad gps character received"), const("GPSManager"))
            print(self.uGPS.latitude)
            print(self.uGPS.satellites_visible())
            print(self.lastDataRxTime)
            # print(self.uart.read(1))

            await asyncio.sleep(0.5)
            pass

    def getCoord(self):
        return self.uGPS.latitude, self.uGPS.longitude

    def getTime(self):
        return self.uGPS.timestamp

    def setSleep(self, sleep=True):
        if sleep:
            self.uart.write(self.UBX_BCK_MODE)
        else:
            self.uart.write(self.UBX_RESTART)

    def powerOn(self):
        self.powerPin.value(1)

    def powerOff(self):
        self.powerPin.value(0)
