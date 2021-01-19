#!/usr/bin/env python

import fire
from yaml import safe_load
from thermostat import Thermostat

class CLI:

    def __init__(self, settings):
        with open(settings) as f:
            raw = safe_load(f)
            parsed = {}
            for thermo in raw["thermostats"]:
                name = thermo["name"]
                addr = thermo["address"]
                secret = bytes.fromhex(thermo["secret"])
                set_point = float(thermo["set_point"])
                offset = float(thermo["offset"])

                parsed[addr] = Thermostat(name=name, addr=addr, secret=secret,
                                          set_point=set_point, offset=offset)
            self.devs = parsed

    def temp(self):
        for t in self.devs.values():
            print(t.temperature)

    def set_point(self):
        for t in self.devs.values():
            print(t.set_point)

    def battery(self):
        for t in self.devs.values():
            print(t.battery)


if __name__ == "__main__":
    fire.Fire(CLI)