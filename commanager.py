import machine

import sim800l
from constants import PIN_GSM_RX, PIN_GSM_TX, PIN_GSM_RST


class comManager:
    def __init__(self):
        self.uart = machine.UART(1, 38400, rx=PIN_GSM_RX, tx=PIN_GSM_TX)
        self.gsm = sim800l.Modem(self.uart, pin="1234", rst_pin=PIN_GSM_RST)

        self.gsm.initialize()
