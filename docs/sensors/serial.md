# Serial Sensor Onboarding (RS-232/RS-485)

Spaxiom does not include a native serial adaptor. Use a **serial bridge** to convert serial output into MQTT or CSV, then ingest with existing Spaxiom sensors.

## 1. Install Dependencies

```bash
pip install pyserial paho-mqtt
```

## 2. Serial → MQTT Bridge

```python
import serial
import paho.mqtt.client as mqtt

SERIAL_PORT = "/dev/ttyUSB0"
BAUD = 9600
MQTT_HOST = "localhost"
TOPIC = "serial/metric"

ser = serial.Serial(SERIAL_PORT, BAUD, timeout=1)
mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_HOST, 1883)

while True:
    line = ser.readline().decode("utf-8").strip()
    if not line:
        continue
    try:
        value = float(line)
        mqtt_client.publish(TOPIC, str(value))
    except ValueError:
        pass
```

## 3. Ingest with Spaxiom

```python
from spaxiom import MQTTSensor

serial_metric = MQTTSensor(
    name="serial_metric",
    broker_host="localhost",
    topic="serial/metric",
)
```

## Notes

- For RS-485 devices using Modbus RTU, prefer the Modbus guide.
- Some sensors stream CSV; use `FileSensor` for replay when needed.
