# Z-Wave Sensor Onboarding (via MQTT Bridge)

Spaxiom does not ingest Z-Wave directly. The recommended approach is to bridge Z-Wave into MQTT using a controller like **Z-Wave JS** and then use `MQTTSensor`.

## 1. Run a Z-Wave Controller

Common options:

- Z-Wave JS UI
- Home Assistant + Z-Wave JS

Enable MQTT integration and identify the topic for sensor updates.

## 2. Normalize Payloads

Z-Wave payloads are JSON. Publish numeric values to a dedicated topic.

Example bridge script:

```python
import json
import paho.mqtt.client as mqtt

SOURCE = "zwave/+/+/value"
DEST = "zwave/temperature"

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode("utf-8"))
    value = payload.get("value")
    if isinstance(value, (int, float)):
        client.publish(DEST, str(value))

client = mqtt.Client()
client.connect("localhost", 1883)
client.subscribe(SOURCE)
client.on_message = on_message
client.loop_forever()
```

## 3. Ingest with Spaxiom

```python
from spaxiom import MQTTSensor

zwave_temp = MQTTSensor(
    name="zwave_temp",
    broker_host="localhost",
    topic="zwave/temperature",
)
```

## Notes

- Use one MQTT topic per metric (temperature, motion, door, etc.).
- If you already use Home Assistant, you can republish sensor states to MQTT.
