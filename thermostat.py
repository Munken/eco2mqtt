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

    def __init__(self, name, addr, secret, set_points, offset, guess_mode=True, mode=None, remote_topic=None):
        self.remote_sensor_topic = remote_topic
        self.secret = secret
        self.addr = addr
        self.name = name

        self._device = eTRVDevice(addr, secret, retry_limit=10)

        self._remote_t = []
        self._set_points = set_points
        self._offset = offset
        self._last_change = time.time()

        self._last_battery_check = 0
        self._battery = None

        if not guess_mode and mode is None:
            raise ValueError("Not guessing mode and no mode is given")

        if guess_mode:
            self._mode = self._guess_mode()
        else:
            self._mode = mode

    def _guess_mode(self):
        t = self._device.temperature.set_point_temperature
        diff = 1000.
        mode = None
        logger.debug("Guessing mode for {}. Current set point {:.1f}", self.name, t)
        for m, setp in self._set_points.items():
            d = abs(t - (setp + self._offset))
            logger.debug("  {} => {:.2f}", m, d)
            if d < diff:
                diff = d
                mode = m

        self._disconnect()

        return mode

    @property
    def set_point(self):
        return self._set_points[self._mode]

    @set_point.setter
    def set_point(self, new):
        logger.debug("{} set_point = {:.1f} offset = {:.1f} sent = {:.1f}",
                     self.name, new, self._offset, new + self._offset)

        self._remote_t = [self._remote_t[-1]] if self._has_remote() else []
        self._last_change = time.time()
        self._set_points[self._mode] = new
        self._device.temperature.set_point_temperature = new + self._offset
        self._ensure_battery_updated()
        self._disconnect()

    @property
    def temperature(self):
        t = self._device.temperature.room_temperature
        self._disconnect()
        return t

    def _disconnect(self):
        self._device.disconnect()

    @property
    def battery(self):
        self._ensure_battery_updated()
        return self._battery

    def _ensure_battery_updated(self):
        now = time.time()
        if (self._battery is None or
                now - self._last_battery_check > 12*HOUR):
            self._battery = self._device.battery
            self._last_battery_check = now
            self._disconnect()

        return self._battery

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, m):
        logger.debug("{}: mode = {}", self.name, m)

        self._mode = m
        self.set_point = self._set_points[m]

    @property
    def remote(self):
        return self._remote_t[-1] if self._has_remote() else self.set_point

    @property
    def offset(self):
        return self._offset

    def _has_remote(self):
        return len(self._remote_t) > 0

    def add_remote(self, temp):
        change = (time.time() - self._last_change) / HOUR
        logger.debug("{}: remote T={} mode={} change={:.2f}", self.name, temp, self.mode, change)
        if self.mode != Thermostat.HOME:
            self._remote_t = [temp]
        else:
            self._remote_t.append(temp)

            if change > 1:
                mean = statistics.mean(self._remote_t)
                diff = mean - self.set_point

                delta = 0
                if diff >= 1.:
                    delta = -0.5
                elif diff <= -1.:
                    delta = 0.5

                logger.debug("{}: mean={} diff={} delta={} offset={}", self.name, mean, diff, delta, self._offset)

                if delta != 0:
                    self._offset += delta
                    self.set_point = self.set_point

