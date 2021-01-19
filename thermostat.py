from libetrv.device import eTRVDevice
import statistics
import time

HOUR = 60 * 60


class Thermostat:

    def __init__(self, name, addr, secret, set_point, offset):
        self.secret = secret
        self.addr = addr
        self.name = name

        self._device = eTRVDevice(addr, secret)

        self._remote_t = []
        self._set_point = set_point
        self._offset = offset
        self._last_change = time.time()

    @property
    def set_point(self):
        t = self._device.temperature.set_point_temperature
        self._device.disconnect()
        return t

    @set_point.setter
    def set_point(self, new):
        self._last_change = time.time()
        self._set_point = new
        self._device.temperature.set_point_temperature = new + self._offset
        self._device.disconnect()

    @property
    def temperature(self):
        t = self._device.temperature.room_temperature
        self._device.disconnect()
        return t

    @property
    def battery(self):
        battery = self._device.battery
        self._device.disconnect()
        return battery

    def add_remote(self, temp):
        self._remote_t.append(temp)

        now = time.time()
        if (now - self._last_change > 1*HOUR and
                statistics.mean(self._remote_t) - self._set_point > 1):

            self._offset += 0.5
            self.set_point(self._set_point)
            self._last_change = now
            self._remote_t = []

