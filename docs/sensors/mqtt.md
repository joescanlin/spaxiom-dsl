# MQTT Sensor Onboarding

This guide shows how to connect MQTT topics to Spaxiom using the `MQTTSensor` adaptor.

## 1. Install Dependencies

```bash
pip install spaxiom
pip install paho-mqtt
```

## 2. Confirm Broker Access

You should know:

- Broker host (e.g. `localhost` or IP)
- Port (default `1883`)
- Topic (e.g. `sensors/temperature`)
- Credentials (optional)

## 3. Create a Sensor in Python

```python
from spaxiom import MQTTSensor, Condition, on

temp = MQTTSensor(
    name="temp_mqtt",
    broker_host="localhost",
    broker_port=1883,
    topic="sensors/temperature",
    username="user",
    password="pass",
)

temp_high = Condition(lambda: temp.read() > 28.0)

@on(temp_high)
def alert_high_temp():
    print("Temperature exceeded 28°C")
```

## 4. Start the Runtime

```bash
spax run ./mqtt_demo.py --poll-ms 200
```

## 5. Verify Payload Format

`MQTTSensor` expects **numeric payloads**. If you publish JSON, publish a numeric value only or convert to a number before publishing.

Example payloads that work:

```
22.4
17
0.82
```

## 6. Edge API Registration (Optional)

```bash
curl -X POST http://localhost:8080/api/sensors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "temp_mqtt",
    "sensor_type": "mqtt",
    "location": [0, 0, 0],
    "config": {
      "broker": "localhost",
      "port": 1883,
      "topic": "sensors/temperature"
    },
    "enabled": true
  }'
```

## Troubleshooting

- **ImportError**: `pip install paho-mqtt`
- **No values received**: Verify topic, broker host, and firewall
- **Non-numeric payload**: Update publisher to send numeric values
