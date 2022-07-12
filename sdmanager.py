"""
Code erreur retourné par les getters:
-2 : settings not load
"""
from machine import SPI, Pin
import sdcard
import ujson
import os

import logger


class SDManager:
    # Prend en paramétre les numéros des pins sck, mosi,miso, chip select et sdPresent
    #
    def __init__(self, sck, mosi, miso, SDCardCS, SDPresent):
        self.settings = {
            "imat": None,
            "maxSpeed": None
        }
        self.isSettingsLoad = False
        self.isSdNeedInit = False
        self.isSdInit = False

        self.spi = SPI(1, sck=Pin(sck), mosi=Pin(mosi), miso=Pin(miso))
        self.sd = sdcard.SDCard(self.spi, Pin(SDCardCS))

        self.sdPresentPin = Pin(SDPresent, Pin.IN, Pin.PULL_UP) # Todo : vérifier la pullup
        self.sdPresentPin.irq(self.irqSdSlotChange)

        try:
            self.initSdCard()
        except OSError as err:
            logger.error(f"OSError while loading SD Card : {err}","SettingsManager")

    """
    Charge les settings enregistré dans settings.conf dans la carte sd
    Si le fichier n'existe pas, il est crée
    
    Renvoi:
     -1 si la vérification d'accès à la carte SD à échoué.
     -2 si l'accès au fichier à échoué (OSError)
    """

    def loadSettings(self):
        if not self.checkSDConnection():
            self.isSettingsLoad = False
            return -1

        try:
            if not "settings.conf" in os.listdir(
                    "sd"):  # Si le fichier de config n'existe pas alors on enregistre les settings actuellement en mémoire
                self.saveSettings()

                self.isSettingsLoad = True  # Inutile de charger les settings puisqu'ils sont déjà en mémoire
                return

            with open("/sd/settings.conf", "r") as file:
                self.settings = ujson.load(file)
                file.close()
                self.isSettingsLoad = True
                logger.info("Settings have been loaded", "SettingsManager")
        except OSError as err:
            self.isSettingsLoad = False
            logger.error("Error while accessing sd card", "SettingsManager")
            logger.error("OS error: {0}".format(err))
            return -2

    """
    Eregistre les settings en mémoire dans settings.conf dans la carte sd
    Si le fichier n'existe pas, il est crée

    Renvoi:
     -1 si la vérification d'accès à la carte SD à échoué.
     -2 si l'accès au fichier à échoué (OSError)
    """
    def saveSettings(self):
        if not self.checkSDConnection():
            return -1

        try:
            with open("/sd/settings.conf", "w") as file:
                ujson.dump(self.settings, file)
                logger.info("Settings saved", module="SettingsManager")
                file.close()
        except OSError as err:
            logger.error("Error while accessing sd card", "SettingsManager")
            logger.error("OS error: {0}".format(err))
            return -2

    def initSdCard(self):
        self.sd.init_card_from_constructor()
        os.mount(self.sd, "/sd")
        self.isSdInit = True

    def deInitSdCard(self):
        os.umount("/sd")
        self.isSdInit = False

    # Retour:
    # True: Carte accessible
    # -1: SD non physiquement présente
    # -2: SD non initialisé

    def checkSDConnection(self):
        if not self.sdPresentPin.value():  # On vérifie que la carte est inséré
            return -1
        if not self.isSdInit:  # On vérifie la bonne initialisaiton
            return -2

        return True

    def irqSdSlotChange(self):
        if self.sdPresentPin.value():
            self.initSdCard()
            self.loadSettings()
        else:
            self.deInitSdCard()

    """
    Getters
    """

    def getImat(self):
        return self.settings["imat"] if self.isSettingsLoad else -2

    def getMaxSpeed(self):
        return self.settings["maxSpeed"] if self.isSettingsLoad else -2

    """
    Setters
    """
    def setImat(self, value):
        self.settings["imat"] = value

    def setMaxSpeed(self, value):
        self.settings["maxSpeed"] = value
