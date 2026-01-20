# YAML Configuration Guide

Once your sensors are onboarded, you can declare them in YAML so Spaxiom can auto-load them via `spax run --config`.

> Note: The current YAML loader (`spaxiom/config.py`) supports **random**, **toggle**, and **gpio_digital** sensors. Other protocols are typically bridged to MQTT or file replay and loaded in code.

## 1. Basic YAML Structure

```yaml
sensors:
  - name: temperature_sensor
    type: random
    location: [0, 0, 0]
    hz: 1.0
    privacy: public

  - name: door_toggle
    type: toggle
    toggle_interval: 2.0
    high_value: 1.0
    low_value: 0.0
    location: [1, 0, 0]

  - name: gpio_button
    type: gpio_digital
    pin: 17
    pull_up: true
    active_state: true
    location: [2, 0, 0]
```

## 2. Load Sensors from YAML

```bash
spax run ./my_script.py --config sensors.yaml
```

Or in Python:

```python
from spaxiom import load_sensors_from_yaml

sensors = load_sensors_from_yaml("sensors.yaml")
```

## 3. Extend for Other Protocols

If you use MQTT, File, or other adaptors, register them in code until YAML support is extended.

Example (MQTT in code + YAML for GPIO):

```python
from spaxiom import MQTTSensor
from spaxiom import load_sensors_from_yaml

load_sensors_from_yaml("sensors.yaml")

temp = MQTTSensor(
    name="temp_mqtt",
    broker_host="localhost",
    topic="sensors/temperature",
)
```
