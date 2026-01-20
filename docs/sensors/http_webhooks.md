# HTTP/REST Webhook Onboarding

Spaxiom does not provide a native HTTP webhook sensor. The recommended path is to **accept webhook POSTs** and forward values into Spaxiom using MQTT or by calling the Edge API to register/update sensors.

## Option A: Webhook → MQTT

Use a small service (FastAPI/Flask) to receive webhooks and publish a numeric value to MQTT.

```python
from fastapi import FastAPI, Request
import paho.mqtt.client as mqtt

app = FastAPI()
mqtt_client = mqtt.Client()
mqtt_client.connect("localhost", 1883)

@app.post("/webhook")
async def webhook(req: Request):
    payload = await req.json()
    value = float(payload["value"])
    mqtt_client.publish("webhooks/metric", str(value))
    return {"ok": True}
```

Then ingest with `MQTTSensor`:

```python
from spaxiom import MQTTSensor

metric = MQTTSensor(
    name="webhook_metric",
    broker_host="localhost",
    topic="webhooks/metric",
)
```

## Option B: Webhook → Edge API

If you run the Edge server, you can register sensors and update readings through your webhook service.

```bash
curl -X POST http://localhost:8080/api/sensors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "webhook_metric",
    "sensor_type": "random",
    "location": [0, 0, 0],
    "config": {},
    "enabled": true
  }'
```

Then create a custom bridge that writes values into your runtime (MQTT is simplest, Edge API is best for deployment).

## Notes

- Webhooks are typically **event-driven**; ensure you publish a numeric value per event.
- For batched webhooks, emit one MQTT message per metric.
