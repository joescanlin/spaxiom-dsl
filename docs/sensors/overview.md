# Sensor Onboarding Overview

Spaxiom supports multiple sensor ingestion paths. This guide maps the **common onboarding flows** and links to protocol-specific, step-by-step setup guides.

## Supported Sensor Paths

```
Physical Sensor ──► Protocol ──► Spaxiom Sensor ──► Pattern/Agent
               (MQTT/GPIO/CSV)    (Python class)     (INTENT events)
```

You can onboard sensors in two ways:

1. **Python Runtime (SDK-first)**
   - Use the sensor classes directly in your script.
   - Best for prototyping and local workflows.

2. **Spaxiom Edge (API/UI)**
   - Register sensors via `/api/sensors` or the web UI.
   - Best for edge deployments.

## Common Sensor Protocol Guides

- [MQTT Sensors](mqtt.md)
- [Zigbee Sensors (via Zigbee2MQTT)](zigbee.md)
- [Modbus Sensors (RTU/TCP)](modbus.md)
- [HTTP/REST Webhooks](http_webhooks.md)
- [LoRaWAN Sensors](lorawan.md)
- [Z-Wave Sensors (via MQTT bridge)](zwave.md)
- [Serial Sensors (RS-232/RS-485)](serial.md)
- [GPIO Sensors (Linux/Raspberry Pi)](gpio.md)
- [File/CSV Sensors](file_csv.md)
- [Simulated/Synthetic Sensors](simulated.md)
- [YAML Configuration](yaml_config.md)

## Minimum Dependencies

| Protocol | Package | Notes |
|----------|---------|-------|
| MQTT | `paho-mqtt` | Required for `MQTTSensor` (`spaxiom/adaptors/mqtt_sensor.py`) |
| GPIO | `gpiozero` | Linux only; required for `GPIODigitalSensor` (`spaxiom/adaptors/gpio_sensor.py`) |
| YAML config | `pyyaml` | Required for `load_sensors_from_yaml` (`spaxiom/config.py`) |

## Edge Sensor Registration (Quick Reference)

The Edge API accepts generic sensor metadata:

```bash
curl -X POST http://localhost:8080/api/sensors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sensor_name",
    "sensor_type": "random",
    "location": [0, 0, 0],
    "config": {},
    "enabled": true
  }'
```

Supported types are defined in `spaxiom/edge/sensor_registry.py` (e.g. `random`, `toggling`, `gpio_digital`, `mqtt`, `file`, `sim_analog`, `sim_binary`).
