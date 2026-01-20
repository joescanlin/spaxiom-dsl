# LoRaWAN Sensor Onboarding

Spaxiom does not ingest LoRaWAN directly. The common approach is:

**LoRaWAN Network Server → MQTT → Spaxiom**

Most networks (TTN, ChirpStack, Actility) can publish device data to MQTT.

## 1. Configure MQTT Integration

In your LoRaWAN platform, enable MQTT integration and identify:

- Broker host
- Topic (device uplink topic)
- Payload format (JSON)

## 2. Bridge JSON → Numeric

LoRaWAN payloads are usually JSON. Spaxiom’s `MQTTSensor` expects numeric payloads. Use a bridge:

```python
import json
import paho.mqtt.client as mqtt

SOURCE = "lorawan/device/+/up"
DEST = "lorawan/temperature"

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode("utf-8"))
    temp = payload.get("temperature")
    if temp is not None:
        client.publish(DEST, str(temp))

client = mqtt.Client()
client.connect("localhost", 1883)
client.subscribe(SOURCE)
client.on_message = on_message
client.loop_forever()
```

## 3. Ingest with Spaxiom

```python
from spaxiom import MQTTSensor

lorawan_temp = MQTTSensor(
    name="lorawan_temp",
    broker_host="localhost",
    topic="lorawan/temperature",
)
```

## Notes

- LoRaWAN payloads often need decoding (e.g. Cayenne LPP). Decode before publishing numeric values.
- Publish one metric per MQTT topic for cleaner conditions.
