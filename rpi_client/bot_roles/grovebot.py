import sys
from settings import SENSORS

from bot_roles.core import Core

sys.path.append("/home/pi/projects/GrovePi/Software/Python")

from grovepi import *


class GrovePiSensorValues:

    def __init__(self):
        self.sensors = SENSORS
        self.sensors_types = [sens['type'] for sens in SENSORS]

        for sensor in self.sensors:
            setattr(self, sensor['type'], sensor['default'])

    def update(self):
        # if 'temp' in self.sensors_types:
        #     try:
        #         self.temp = temp(0)
        #     except IOError:
        #         print "--"
        #     except ValueError:
        #         print self.temp
        #     except ZeroDivisionError:
        #         print "temp ZeroDivisionError"

        if 'sound' in self.sensors_types:
            try:
                self.sound = analogRead(1)
            except IOError:
                pass
            except ValueError:
                pass

        # This is the light sensor
        if 'light' in self.sensors_types:
            try:
                self.light = analogRead(2)
            except IOError:
                pass
            except ValueError:
                pass

        # This is the slider switch sensor
        if 'slider' in self.sensors_types:
            try:
                self.slider = digitalRead(3)
            except IOError:
                pass
            except ValueError:
                pass

        # This is the button
        if 'button' in self.sensors_types:
            try:
                self.button = digitalRead(2)
            except IOError:
                pass
            except ValueError:
                pass

        # This is the touch sensor
        if 'touch' in self.sensors_types:
            try:
                self.touch = digitalRead(7)
            except IOError:
                pass
            except ValueError:
                pass

        # This is the pir sensor
        if 'pir' in self.sensors_types:
            try:
                self.pir = digitalRead(3)
            except IOError:
                pass
            except ValueError:
                pass

        # This is the dht sensor port
        if 'temp' in self.sensors_types and 'humidity' in self.sensors_types:
            try:
                [self.temp, self.humidity] = dht(4, 1)
                print "temp: %s, humidity %s" % (self.temp, self.humidity)
            except IOError:
                print "dht IOError"
            except ValueError:
                print "dht ValueError"


        # This is the acc_xyy Accelerometer sensor, use port I2C-1
        if 'acc_xyz' in self.sensors_types:
            try:
                self.acc_xyz = acc_xyz()
            except IOError:
                print "acc_xyz IOError"
            except ValueError:
                print "acc_xyz ValueError"

        # This is the acc_xyy Accelerometer sensor
        if 'dist' in self.sensors_types:
            try:
                self.dist = ultrasonicRead(8)
            except IOError:
                pass
            except ValueError:
                pass

    def toDict(self):
        out = {}
        for sensor in self.sensors:
            val = getattr(self, sensor['type'])
            out.update({sensor['type']: val})

        print "toDict: ", out
        return out


grovePiSensorValues = GrovePiSensorValues()


class Grovebot(Core):

    def __init__(self):
        self.commands = []
