from sensor import *
import time
class Orchestrator:

    def __init__(self, verbose = False):
        self.sensors:[Sensor] = []
        self.verbose = verbose

    def add_sensor(self, sensor:Sensor):
        if not isinstance(sensor, Sensor):
            raise TypeError(
                "Sensor attendu, reçu: {}".format(type(sensor))
            )
        self.sensors.append(sensor)
        return self
        
    def read(self):
        for sensor in self.sensors:
            if self.verbose:
                print(sensor.read())
            else:
                sensor.read()
                
    def update(self, sleepDuration = 0.001):
        self.read()
        time.sleep(sleepDuration)