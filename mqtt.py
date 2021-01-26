import socket
import paho.mqtt.client as mqtt
from thermostat import Thermostat

from loguru import logger
import json


class A:
    def __init__(self, c):
        self.c = c

    def _on_connect(self, client, userdata, flags, rc):
        logger.info("{} connect", self.c)

        client.message_callback_add(
            "munk/etrv/{}".format(self.c),
            lambda client, userdata, message: self._on_message(client, userdata, message)
        )

    def _on_message(self, client, userdata, message):
        logger.info("{} topic: {} payload: {}", self.c, message.topic, message.payload)

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("munk/etrv/#")

    for a in userdata:
        a._on_connect(client, userdata, flags, rc)


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))


class MqttThermostat:

    def __init__(self, thermostat: Thermostat):
        self.thermostat = thermostat
        self.id = thermostat.addr.replace(":", "")
        self._battery = None
        self.client = None

        base = "munk/etrv/{}".format(self.id)

        self.pub = "{}/state".format(base)

        self.sub = {
            "away_command": ("away_mode/command", self._on_away_command),
            "mode_command": ("mode/command", self._on_mode_command),
            "temp_command": ("temp/command", self._on_temp_command),
            # "temp_remote":  ("temp/remote", self._on_temp_remote),
        }

        for key, (topic, f) in self.sub.items():
            self.sub[key] = ("{}/{}".format(base, topic), f)

    def _on_connect(self, client, userdata, flags, rc):
        logger.info("{} connect", self.thermostat.addr)

        self.client = client

        for topic, f in self.sub.values():
            logger.debug("Subscribing to {} {}", topic, f)
            client.message_callback_add(
                topic,
                # Note the default value capture. See https://stackoverflow.com/a/2295372
                lambda c, _, message, f=f: f(c, message)
            )

        if self.thermostat.remote_sensor_topic:
            client.message_callback_add(
                self.thermostat.remote_sensor_topic,
                lambda c, _, message: self._on_temp_remote(c, message)
            )

        self._publish_autodiscory()

    def _on_away_command(self, client, message):
        logger.debug("{}: away {}", self.thermostat.name, message.payload)

        mode = message.payload.decode('ascii').lower()

        if mode == 'on':
            self.thermostat.mode = Thermostat.AWAY
        elif mode == 'off':
            self.thermostat.mode = Thermostat.HOME

        self._publish_state()

    def _on_mode_command(self, client, message):
        logger.debug("{}: mode {}", self.thermostat.name, message.payload)

        mode = message.payload.decode('ascii').lower()

        if mode == 'heat':
            self.thermostat.mode = Thermostat.HOME
        elif mode == 'off':
            self.thermostat.mode = Thermostat.OFF

        self._publish_state()

    def _on_temp_command(self, client, message):
        logger.debug("{}: tcmd {}", self.thermostat.name, message.payload)

        t = float(message.payload.decode('ascii'))
        self.thermostat.set_point = t
        self._publish_state()

    def _on_temp_remote(self, client, message):
        logger.debug("{}: remote {}", self.thermostat.name, message.payload)

        t_str = message.payload.decode('ascii')
        try:
            t = float(t_str)
            self.thermostat.add_remote(t)
        except Exception as e:
            logger.error(e)
        finally:
            self._publish_state()

    def _publish_state(self):

        away = "ON" if self.thermostat.mode == Thermostat.AWAY else "OFF"
        mode = "off" if self.thermostat.mode == Thermostat.OFF else "heat"

        state = {
            "away_mode": away,
            "mode": mode,
            "target_temp": self.thermostat.set_point,
            "current_temp": self.thermostat.remote,
            "offset": self.thermostat.offset,
            "battery": self._battery
        }

        self._publish(self.pub, payload=json.dumps(state), retain=True)

    def _publish(self, topic, payload=None, qos=0, retain=False, properties=None):
        if self.client:
            self.client.publish(topic=topic, payload=payload, qos=qos,
                                retain=retain, properties=properties)

    def _publish_autodiscory(self):
        id = self.thermostat.addr.replace(':', '')
        # sub = "homeassistant/climate/{}/config".format(id)

        device = {
            "identifiers": id,
            "manufacturer": "Danfoss",
            "model": "Eco2",
            "name": self.thermostat.name,
            "via_device": socket.gethostname()
        }

        discover_climate = {
            "away_mode_command_topic":    self.sub["away_command"][0],
            "away_mode_state_topic":      self.pub,
            "away_mode_state_template":   '{{ value_json["away_mode"]}}',
            "curr_temp_t":                self.pub,
            "curr_temp_tpl":              '{{ value_json["current_temp"]}}',
            "initial":                    self.thermostat.set_point,
            "max_temp":                   30,
            "min_temp":                    5,
            "mode_command_topic":         self.sub["mode_command"][0],
            "mode_stat_t":                self.pub,
            "mode_stat_tpl":              '{{ value_json["mode"]}}',
            "modes":                      ["heat", "off"],
            "name":                       self.thermostat.name,
            "temperature_command_topic":  self.sub["temp_command"][0],
            "temp_stat_t":                self.pub,
            "temp_stat_tpl":              '{{ value_json["target_temp"]}}',
            "temp_step":                  0.5,
        }

        discover_battery = {
            "device_class":   "battery",
            "name":           "{} battery".format(self.thermostat.name),
            "state_topic":    self.pub,
            "value_template": '{{ value_json["battery"]}}',
            "unit_of_measurement": "%"
        }

        discover_offset = {
            "device_class":   "temperature",
            "name":           "{} offset".format(self.thermostat.name),
            "state_topic":    self.pub,
            "value_template": '{{ value_json["offset"]}}',
            "unit_of_measurement": "°C"
        }

        discoveries = (
            (discover_climate, "climate", "climate"),
            (discover_battery, "battery", "sensor"),
            (discover_offset,  "offset",  "sensor")
        )

        for specific, name, typ in discoveries:

            uid = "{}-{}".format(id, name)
            d = {
                "device": device,
                "unique_id": uid
            }
            d.update(specific)

            payload = json.dumps(d)
            sub = "homeassistant/{type}/{id}/config".format(type=typ, id=uid)
            logger.debug("Sending discovery to {}", sub)
            logger.debug("Payload {}", payload)
            #
            self.client.publish(sub, payload, retain=True)

        self._publish_state()

    def update_battery(self):
        self._battery = self.thermostat.battery
        self._publish_state()

