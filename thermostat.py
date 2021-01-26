from libetrv.device import eTRVDevice
import statistics
import time

from loguru import logger

HOUR = 60 * 60


class Thermostat:

    HOME = "home"
    AWAY = "away"
    OFF = "off"

    # __MODES = (HOME, AWAY, OFF)

    def __init__(self, name, addr, secret, set_point, offset, mode=HOME, remote_topic=None):
        self.remote_sensor_topic = remote_topic
        self.secret = secret
        self.addr = addr
        self.name = name

        self._device = eTRVDevice(addr, secret)

        self._remote_t = []
        self._mode = mode
        self._set_point = set_point
        self._offset = offset
        self._last_change = time.time()

    @property
    def set_point(self):
        return self._set_point[self._mode]

    @set_point.setter
    def set_point(self, new):

        logger.debug("{} set_point = {:.1f} offset = {:.1f} sent = {:.1f}",
                     self.name, new, self._offset, new + self._offset)

        self._remote_t = [self._remote_t[-1]] if self._has_remote() else []
        self._last_change = time.time()
        self._set_point[self._mode] = new
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

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, m):
        logger.debug("{}: mode = {}", self.name, m)

        self._mode = m
        self.set_point = self._set_point[m]

    @property
    def remote(self):
        return self._remote_t[-1] if self._has_remote() else self.set_point

    @property
    def offset(self):
        return self._offset

    def _has_remote(self):
        return len(self._remote_t) > 0

    def add_remote(self, temp):
        if self.mode != Thermostat.HOME:
            self._remote_t = [temp]
        else:
            self._remote_t.append(temp)

            now = time.time()
            if now - self._last_change > 1*HOUR:
                diff = statistics.mean(self._remote_t) - self.set_point

                delta = 0
                if diff >= 1.:
                    delta = -0.5
                elif diff <= -1.:
                    delta = 0.5

                if delta != 0:
                    self._offset += delta
                    self.set_point = self.set_point

