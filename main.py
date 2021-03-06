#!/usr/bin/env python

import fire
import time
from yaml import safe_load
from thermostat import Thermostat
from mqtt import MqttThermostat
import paho.mqtt.client as mqtt

HOUR = 60*60

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("munk/etrv/#")

    for a in userdata:
        a._on_connect(client, userdata, flags, rc)


def on_message(client, userdata, msg):
    print("super" + msg.topic+" "+str(msg.payload))


def _load_settings(settings, guess_mode):
    with open(settings) as f:
        raw = safe_load(f)

        parsed = {}
        for thermo in raw["thermostats"]:
            name = thermo["name"]
            addr = thermo["address"]
            secret = bytes.fromhex(thermo["secret"])
            set_point = thermo["set_point"]
            offset = float(thermo["offset"])
            remote_topic = thermo.get("remote")

            parsed[addr] = Thermostat(name=name, addr=addr, secret=secret,
                                      set_points=set_point, offset=offset,
                                      remote_topic=remote_topic, guess_mode=guess_mode)
        return parsed


class CLI:

    def __init__(self):
        pass

    # def temp(self):
    #     for t in self.devs.values():
    #         print(t.temperature)
    #
    # def set_point(self):
    #     for t in self.devs.values():
    #         print(t.set_point)

    def mqtt(self, settings, guess_mode=True):

        devs = _load_settings(settings, guess_mode)

        handlers = [MqttThermostat(t) for t in devs.values()]

        client = mqtt.Client()
        client.user_data_set(handlers)

        client.on_connect = on_connect
        client.on_message = on_message

        client.username_pw_set("mqtt", "0Bwz3sw6ekuYvYzDrTnE")
        client.connect("192.168.1.3", 1883, 60)

        client.loop_forever()


if __name__ == "__main__":
    fire.Fire(CLI)