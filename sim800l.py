# Imports
import time
import json

import utime
from machine import Pin

import logger as log
from micropython import const


# Setup logging.
class Logger(object):
    level = 'INFO'

    @classmethod
    def debug(cls, text):
        log.debug(text, const("Sim800"))

    @classmethod
    def info(cls, text):
        log.info(text, const("Sim800"))

    @classmethod
    def warning(cls, text):
        log.warn(text, const("Sim800"))


logger = Logger()


class GenericATError(Exception):
    pass


class Response(object):

    def __init__(self, status_code, content):
        self.status_code = int(status_code)
        self.content = content


class Modem(object):

    def __init__(self, uart,  pin = None, rst_pin=None):

        # Pins
        self.sim_pin = pin

        self.resetPin = Pin(rst_pin, Pin.OUT)
        self.resetPin.value(1)

        # Uart
        self.uart = uart
        self.ssl_available = None

        self.initialized = False
        self.modem_info = None

    # ----------------------
    #  Modem initializer
    # ----------------------

    def initialize(self):

        logger.debug('Resetting modem...')
        self.resetPin.value(0)
        utime.sleep_ms(100)
        self.resetPin.value(1)

        logger.debug('Initializing modem...')


        # Test AT commands
        retries = 0
        while True:
            try:
                self.modem_info = self.execute_at_command('modeminfo')
            except:
                retries += 1
                if retries < 3:
                    logger.debug('Error in getting modem info, retrying.. (#{})'.format(retries))
                    time.sleep(3)
                else:
                    raise
            else:
                break

        logger.debug('Ok, modem "{}" is ready and accepting commands'.format(self.modem_info))
        self.execute_at_command('seterrorlog')

        if self.sim_pin is not None:
            logger.debug("Unlocking pin with pin {}".format(self.sim_pin))
            self.unlockSim(self.sim_pin)


        # Set initialized flag and support vars
        self.initialized = True

        # Check if SSL is supported
        # self.ssl_available = self.execute_at_command('checkssl') == '+CIPSSL: (0-1)'
        self.ssl_available = False

    # ----------------------
    # Execute AT commands
    # ----------------------
    def execute_at_command(self, command, data=None, clean_output=True):
        while self.uart.any():
            self.uart.read()

        # Commands dictionary. Not the best approach ever, but works nicely.
        commands = {
            'modeminfo': {'string': 'ATI', 'timeout': 3, 'end': 'OK'},
            'fwrevision': {'string': 'AT+CGMR', 'timeout': 3, 'end': 'OK'},
            'battery': {'string': 'AT+CBC', 'timeout': 3, 'end': 'OK'},
            'scan': {'string': 'AT+COPS=?', 'timeout': 60, 'end': 'OK'},
            'network': {'string': 'AT+COPS?', 'timeout': 3, 'end': 'OK'},
            'signal': {'string': 'AT+CSQ', 'timeout': 3, 'end': 'OK'},
            'checkreg': {'string': 'AT+CREG?', 'timeout': 3, 'end': None},
            'setapn': {'string': 'AT+SAPBR=3,1,"APN","{}"'.format(data), 'timeout': 3, 'end': 'OK'},
            'setuser': {'string': 'AT+SAPBR=3,1,"USER","{}"'.format(data), 'timeout': 3, 'end': 'OK'},
            'setpwd': {'string': 'AT+SAPBR=3,1,"PWD","{}"'.format(data), 'timeout': 3, 'end': 'OK'},
            'initgprs': {'string': 'AT+SAPBR=3,1,"Contype","GPRS"', 'timeout': 3, 'end': 'OK'},
            'setpin' : {'string': 'AT+CPIN=\"{}\"'.format(data), 'timeout': 3, 'end': 'OK'},
            'checksim': {'string': 'AT+CPIN?', 'timeout': 3, 'end': 'OK'},
            'seterrorlog': {'string': 'AT+CMEE=1', 'timeout': 3, 'end': 'OK'},
            'setsmstextmode': {'string': 'AT+CMGF=1', 'timeout': 3, 'end': 'OK'},
            # Appeared on hologram net here or below

            'opengprs': {'string': 'AT+SAPBR=1,1', 'timeout': 3, 'end': 'OK'},
            'getbear': {'string': 'AT+SAPBR=2,1', 'timeout': 3, 'end': 'OK'},
            'inithttp': {'string': 'AT+HTTPINIT', 'timeout': 3, 'end': 'OK'},
            'sethttp': {'string': 'AT+HTTPPARA="CID",1', 'timeout': 3, 'end': 'OK'},
            'checkssl': {'string': 'AT+CIPSSL=?', 'timeout': 3, 'end': 'OK'},
            'enablessl': {'string': 'AT+HTTPSSL=1', 'timeout': 3, 'end': 'OK'},
            'disablessl': {'string': 'AT+HTTPSSL=0', 'timeout': 3, 'end': 'OK'},
            'initurl': {'string': 'AT+HTTPPARA="URL","{}"'.format(data), 'timeout': 3, 'end': 'OK'},
            'doget': {'string': 'AT+HTTPACTION=0', 'timeout': 3, 'end': '+HTTPACTION'},
            'setcontent': {'string': 'AT+HTTPPARA="CONTENT","{}"'.format(data), 'timeout': 3, 'end': 'OK'},
            'postlen': {'string': 'AT+HTTPDATA={},5000'.format(data), 'timeout': 3, 'end': 'DOWNLOAD'},
            # "data" is data_lenght in this context, while 5000 is the timeout
            'dumpdata': {'string': data, 'timeout': 1, 'end': 'OK'},
            'dopost': {'string': 'AT+HTTPACTION=1', 'timeout': 3, 'end': '+HTTPACTION'},
            'getdata': {'string': 'AT+HTTPREAD', 'timeout': 3, 'end': 'OK'},
            'closehttp': {'string': 'AT+HTTPTERM', 'timeout': 3, 'end': 'OK'},
            'closebear': {'string': 'AT+SAPBR=0,1', 'timeout': 3, 'end': 'OK'}
        }

        # References:
        # https://github.com/olablt/micropython-sim800/blob/4d181f0c5d678143801d191fdd8a60996211ef03/app_sim.py
        # https://arduino.stackexchange.com/questions/23878/what-is-the-proper-way-to-send-data-through-http-using-sim908
        # https://stackoverflow.com/questions/35781962/post-api-rest-with-at-commands-sim800
        # https://arduino.stackexchange.com/questions/34901/http-post-request-in-json-format-using-sim900-module (full post example)

        # Sanity checks
        if command not in commands:
            raise Exception('Unknown command "{}"'.format(command))

        # Support vars
        command_string = commands[command]['string']
        excpected_end = commands[command]['end']
        timeout = commands[command]['timeout']
        processed_lines = 0

        # Execute the AT command
        command_string_for_at = "{}\r\n".format(command_string)
        logger.debug('Writing AT command "{}"'.format(command_string_for_at.encode('utf-8')))
        self.uart.write(command_string_for_at)

        # Support vars
        pre_end = True
        output = ''
        empty_reads = 0

        while True:

            line = self.uart.readline()
            if not line:
                time.sleep(1)
                empty_reads += 1
                if empty_reads > timeout:
                    raise Exception('Timeout for command "{}" (timeout={})'.format(command, timeout))
                    # logger.warning('Timeout for command "{}" (timeout={})'.format(command, timeout))
                    # break
            else:
                logger.debug('Read "{}"'.format(line))

                # Convert line to string
                line_str = line.decode('utf-8')

                # Do we have an error?
                if line_str == 'ERROR\r\n':
                    raise GenericATError('Got generic AT error')

                # If we had a pre-end, do we have the expected end?
                if line_str == '{}\r\n'.format(excpected_end):
                    logger.debug('Detected exact end')
                    break
                if pre_end and line_str.startswith('{}'.format(excpected_end)):
                    logger.debug('Detected startwith end (and adding this line to the output too)')
                    output += line_str
                    break

                # Do we have a pre-end?
                if line_str == '\r\n':
                    pre_end = True
                    logger.debug('Detected pre-end')
                else:
                    pre_end = False

                # Keep track of processed lines and stop if exceeded
                processed_lines += 1

                # Save this line unless in particular conditions
                if command == 'getdata' and line_str.startswith('+HTTPREAD:'):
                    pass
                else:
                    output += line_str

        # Remove the command string from the output
        output = output.replace(command_string + '\r\r\n', '')

        # ..and remove the last \r\n added by the AT protocol
        if output.endswith('\r\n'):
            output = output[:-2]

        # Also, clean output if needed
        if clean_output:
            output = output.replace('\r', '')
            output = output.replace('\n\n', '')
            if output.startswith('\n'):
                output = output[1:]
            if output.endswith('\n'):
                output = output[:-1]

        logger.debug('Returning "{}"'.format(output.encode('utf8')))

        # Return
        return output

    # ----------------------
    #  Function commands
    # ----------------------

    def get_info(self):
        output = self.execute_at_command('modeminfo')
        return output

    def checkSimState(self):
        output = self.execute_at_command('checksim')
        if output == "+CPIN: READY":
            return True
        return False

    # pin doit ??tre un string
    def unlockSim(self, pin):
        output = self.execute_at_command('setpin', pin)
        return output

    def battery_status(self):
        output = self.execute_at_command('battery')
        return output

    def scan_networks(self):
        networks = []
        output = self.execute_at_command('scan')
        pieces = output.split('(', 1)[1].split(')')
        for piece in pieces:
            piece = piece.replace(',(', '')
            subpieces = piece.split(',')
            if len(subpieces) != 4:
                continue
            networks.append({'name': json.loads(subpieces[1]), 'shortname': json.loads(subpieces[2]),
                             'id': json.loads(subpieces[3])})
        return networks

    def get_current_network(self):
        output = self.execute_at_command('network')
        network = output.split(',')[-1]
        if network.startswith('"'):
            network = network[1:]
        if network.endswith('"'):
            network = network[:-1]
        # If after filtering we did not filter anything: there was no network
        if network.startswith('+COPS'):
            return None
        return network

    def get_signal_strength(self):
        # See more at https://m2msupport.net/m2msupport/atcsq-signal-quality/
        output = self.execute_at_command('signal')
        signal = int(output.split(':')[1].split(',')[0])
        signal_ratio = float(signal) / float(30)  # 30 is the maximum value (2 is the minimum)
        return signal_ratio

    def get_ip_addr(self):
        output = self.execute_at_command('getbear')
        output = output.split('+')[-1]  # Remove potential leftovers in the buffer before the "+SAPBR:" response
        pieces = output.split(',')
        if len(pieces) != 3:
            raise Exception('Cannot parse "{}" to get an IP address'.format(output))
        ip_addr = pieces[2].replace('"', '')
        if len(ip_addr.split('.')) != 4:
            raise Exception('Cannot parse "{}" to get an IP address'.format(output))
        if ip_addr == '0.0.0.0':
            return None
        return ip_addr

    def connect(self, apn, user='', pwd=''):
        if not self.initialized:
            raise Exception('Modem is not initialized, cannot connect')

        # Are we already connected?
        if self.get_ip_addr():
            logger.debug('Modem is already connected, not reconnecting.')
            return

        # Closing bearer if left opened from a previous connect gone wrong:
        logger.debug('Trying to close the bearer in case it was left open somehow..')
        try:
            self.execute_at_command('closebear')
        except GenericATError:
            pass

        # First, init gprs
        logger.debug('Connect step #1 (initgprs)')
        self.execute_at_command('initgprs')

        # Second, set the APN
        logger.debug('Connect step #2 (setapn)')
        self.execute_at_command('setapn', apn)
        self.execute_at_command('setuser', user)
        self.execute_at_command('setpwd', pwd)

        # Then, open the GPRS connection.
        logger.debug('Connect step #3 (opengprs)')
        self.execute_at_command('opengprs')

        # Ok, now wait until we get a valid IP address
        retries = 0
        max_retries = 5
        while True:
            retries += 1
            ip_addr = self.get_ip_addr()
            if not ip_addr:
                retries += 1
                if retries > max_retries:
                    raise Exception('Cannot connect modem as could not get a valid IP address')
                logger.debug('No valid IP address yet, retrying... (#')
                time.sleep(1)
            else:
                break

    def disconnect(self):

        # Close bearer
        try:
            self.execute_at_command('closebear')
        except GenericATError:
            pass

        # Check that we are actually disconnected
        ip_addr = self.get_ip_addr()
        if ip_addr:
            raise Exception('Error, we should be disconnected but we still have an IP address ({})'.format(ip_addr))

    def http_request(self, url, mode='GET', data=None, content_type='application/json'):

        # Protocol check.
        assert url.startswith('http'), 'Unable to handle communication protocol for URL "{}"'.format(url)

        # Are we  connected?
        if not self.get_ip_addr():
            raise Exception('Error, modem is not connected')

        # Close the http context if left open somehow
        logger.debug('Close the http context if left open somehow...')
        try:
            self.execute_at_command('closehttp')
        except GenericATError:
            pass

        # First, init and set http
        logger.debug('Http request step #1.1 (inithttp)')
        self.execute_at_command('inithttp')
        logger.debug('Http request step #1.2 (sethttp)')
        self.execute_at_command('sethttp')

        # Do we have to enable ssl as well?
        if self.ssl_available:
            if url.startswith('https://'):
                logger.debug('Http request step #1.3 (enablessl)')
                self.execute_at_command('enablessl')
            elif url.startswith('http://'):
                logger.debug('Http request step #1.3 (disablessl)')
                self.execute_at_command('disablessl')
        else:
            if url.startswith('https://'):
                raise NotImplementedError("SSL is only supported by firmware revisions >= R14.00")

        # Second, init and execute the request
        logger.debug('Http request step #2.1 (initurl)')
        self.execute_at_command('initurl', data=url)

        if mode == 'GET':

            logger.debug('Http request step #2.2 (doget)')
            output = self.execute_at_command('doget')
            response_status_code = output.split(',')[1]
            logger.debug('Response status code: "{}"'.format(response_status_code))

        elif mode == 'POST':

            logger.debug('Http request step #2.2 (setcontent)')
            self.execute_at_command('setcontent', content_type)

            logger.debug('Http request step #2.3 (postlen)')
            self.execute_at_command('postlen', len(data))

            logger.debug('Http request step #2.4 (dumpdata)')
            self.execute_at_command('dumpdata', data)

            logger.debug('Http request step #2.5 (dopost)')
            output = self.execute_at_command('dopost')
            response_status_code = output.split(',')[1]
            logger.debug('Response status code: "{}"'.format(response_status_code))


        else:
            raise Exception('Unknown mode "{}'.format(mode))

        # Third, get data
        logger.debug('Http request step #4 (getdata)')
        response_content = self.execute_at_command('getdata', clean_output=False)

        logger.debug(response_content)

        # Then, close the http context
        logger.debug('Http request step #4 (closehttp)')
        self.execute_at_command('closehttp')

        return Response(status_code=response_status_code, content=response_content)

    def sendSms(self,num,text):
        logger.debug("Set sms in text mode")
        self.execute_at_command('setsmstextmode')
        utime.sleep_ms(50)
        self.uart.write("AT+CMGS=\"{}\"\r\n".format(num))
        utime.sleep_ms(50)
        self.uart.write("{}".format(text))
        utime.sleep_ms(50)
        self.uart.write("\x1a")
        utime.sleep_ms(50)
        self.uart.write("\r\n")
        utime.sleep_ms(50)
        logger.debug(self.uart.read())

    def reset(self):
        self.resetPin.value(0)
        utime.sleep_ms(100)
        self.resetPin.value(1)
        utime.sleep_ms(700)
