# Modbus Sensor Onboarding (RTU/TCP)

Spaxiom does not ship a native Modbus adaptor. The recommended pattern is to **bridge Modbus registers into MQTT or HTTP** and ingest them with existing Spaxiom sensors.

## 1. Install a Modbus Bridge

Common choices:

- **Node-RED** with Modbus + MQTT/HTTP nodes
- **Python bridge** using `pymodbus`

Install Python dependencies:

```bash
pip install pymodbus paho-mqtt
```

## 2. Bridge Modbus → MQTT (Example)

```python
from pymodbus.client import ModbusTcpClient
import paho.mqtt.client as mqtt

MODBUS_HOST = "192.168.1.50"
MQTT_HOST = "localhost"
TOPIC = "modbus/temperature"

client = ModbusTcpClient(MODBUS_HOST, port=502)
mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_HOST, 1883)

while True:
    result = client.read_holding_registers(100, count=1)
    if result and not result.isError():
        value = result.registers[0] / 10.0
        mqtt_client.publish(TOPIC, str(value))
```

## 3. Ingest with Spaxiom (MQTT)

```python
from spaxiom import MQTTSensor

modbus_temp = MQTTSensor(
    name="modbus_temp",
    broker_host="localhost",
    topic="modbus/temperature",
)
```

## 4. Edge API Registration (Optional)

```bash
curl -X POST http://localhost:8080/api/sensors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "modbus_temp",
    "sensor_type": "mqtt",
    "location": [0, 0, 0],
    "config": {
      "broker": "localhost",
      "port": 1883,
      "topic": "modbus/temperature"
    },
    "enabled": true
  }'
```

## Notes

- Use **Modbus RTU** for serial/RS-485 devices and **Modbus TCP** for Ethernet devices.
- Normalize register units in the bridge to avoid unit ambiguity.
