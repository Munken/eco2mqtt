import paho.mqtt.client as mqtt
from thermostat import Thermostat

from loguru import logger


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

        base = "munk/etrv/{}".format(thermostat.addr)
        # base = "munk/etrv"

        self.pub = {
            # "away_state":   "away_mode/state",
            # "mode_state":   "mode/state",
            # "temp_state":   "temp/state",
            # "temp_cur":     "temp/current",
        }

        self.sub = {
            "away_command": ("away_mode/command", self._on_away_command),
            "mode_command": ("mode/command", self._on_mode_command),
            "temp_command": ("temp/command", self._on_temp_command),
            "temp_remote":  ("temp/remote", self._on_temp_remote),
        }

        for key, (topic, f) in self.sub.items():
            self.sub[key] = ("{}/{}".format(base, topic), f)

        for key, val in self.pub.items():
            self.pub[key] = "{}/{}".format(base, val)

        import pprint
        print("sub")
        pprint.pprint(self.sub)
        print("pub")
        pprint.pprint(self.pub)

    def _on_connect(self, client, userdata, flags, rc):
        logger.info("{} connect", self.thermostat.addr)

        for topic, f in self.sub.values():
            logger.debug("Subscribing to {} {}", topic, f)
            client.message_callback_add(
                topic,
                # Note the default value capture. See https://stackoverflow.com/a/2295372
                lambda _, userdata, message, f=f: f(userdata, message)
            )

    def _on_away_command(self, userdata, message):
        logger.debug("away")

    def _on_mode_command(self, userdata, message):
        logger.debug("mode")

    def _on_temp_command(self, userdata, message):
        logger.debug("tcmd")

    def _on_temp_remote(self, userdata, message):
        logger.debug("remote")
