# Zigbee Sensor Onboarding (via Zigbee2MQTT)

Spaxiom does not ingest Zigbee directly. The most reliable approach is to bridge Zigbee sensors into MQTT using Zigbee2MQTT, then subscribe with `MQTTSensor`.

## 1. Install Zigbee2MQTT

Follow the official setup for your OS and adapter:

- https://www.zigbee2mqtt.io/guide/getting-started/

You will need:

- A Zigbee USB coordinator (e.g. Sonoff, ConBee)
- Zigbee2MQTT running locally
- MQTT broker (Mosquitto recommended)

## 2. Pair Your Zigbee Sensors

- Enable pairing in Zigbee2MQTT
- Add your sensor (motion, door, temperature, etc.)
- Note the MQTT topic Zigbee2MQTT publishes to, for example:

```
zigbee2mqtt/living_room_temp
```

## 3. Normalize Payloads to Numeric

Zigbee2MQTT publishes JSON. For `MQTTSensor`, publish numeric values only.

Recommended approach:

1. Use an MQTT rule or small bridge script to publish numeric values.
2. Example bridge script (Python):

```python
import json
import paho.mqtt.client as mqtt

SOURCE = "zigbee2mqtt/living_room_temp"
DEST = "spaxiom/temperature"

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

## 4. Connect to Spaxiom

```python
from spaxiom import MQTTSensor

temp = MQTTSensor(
    name="zigbee_temp",
    broker_host="localhost",
    topic="spaxiom/temperature",
)
```

## 5. Edge API Registration (Optional)

```bash
curl -X POST http://localhost:8080/api/sensors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "zigbee_temp",
    "sensor_type": "mqtt",
    "location": [0, 0, 0],
    "config": {
      "broker": "localhost",
      "port": 1883,
      "topic": "spaxiom/temperature"
    },
    "enabled": true
  }'
```

## Troubleshooting

- **No data**: Verify Zigbee2MQTT topic spelling
- **JSON payloads**: Use a bridge to publish numeric values
- **Multiple values**: Publish one metric per MQTT topic (recommended)
