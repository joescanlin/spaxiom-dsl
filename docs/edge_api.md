# Edge API Reference

The Spaxiom Edge REST API provides programmatic access to all edge functionality. All endpoints accept and return JSON.

## Base URL

```
http://localhost:8080/api
```

## Authentication

When authentication is enabled, include the token in requests:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8080/api/sensors
```

See [Edge Security](edge_security.md) for authentication setup.

## Sensors API

### List Sensors

```http
GET /api/sensors
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `sensor_type` | string | Filter by type (motion, temperature, etc.) |
| `zone_id` | string | Filter by zone |
| `limit` | integer | Max results (default: 100) |
| `offset` | integer | Pagination offset |

**Response:**

```json
{
  "sensors": [
    {
      "id": "sensor_001",
      "name": "front_door_motion",
      "sensor_type": "motion",
      "location": {"x": 10.0, "y": 5.0, "z": 0.0},
      "zone_id": "zone_entrance",
      "created_at": "2024-01-15T10:30:00Z",
      "last_reading": {
        "value": 1,
        "timestamp": "2024-01-15T14:22:33Z"
      }
    }
  ],
  "total": 12
}
```

### Get Sensor

```http
GET /api/sensors/{sensor_id}
```

### Create Sensor

```http
POST /api/sensors
```

**Request Body:**

```json
{
  "name": "kitchen_temp",
  "sensor_type": "temperature",
  "location": {"x": 25.0, "y": 12.0, "z": 1.5},
  "zone_id": "zone_kitchen",
  "config": {
    "unit": "celsius",
    "poll_interval_ms": 1000
  }
}
```

### Update Sensor

```http
PUT /api/sensors/{sensor_id}
```

### Delete Sensor

```http
DELETE /api/sensors/{sensor_id}
```

### Get Sensor Readings

```http
GET /api/sensors/{sensor_id}/readings
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `start` | ISO datetime | Start time |
| `end` | ISO datetime | End time |
| `limit` | integer | Max results |

### Submit Sensor Reading

```http
POST /api/sensors/{sensor_id}/readings
```

**Request Body:**

```json
{
  "value": 23.5,
  "timestamp": "2024-01-15T14:30:00Z"
}
```

## Zones API

### List Zones

```http
GET /api/zones
```

### Get Zone

```http
GET /api/zones/{zone_id}
```

### Create Zone

```http
POST /api/zones
```

**Request Body:**

```json
{
  "name": "living_room",
  "zone_type": "room",
  "bounds": {
    "x1": 0,
    "y1": 0,
    "x2": 30,
    "y2": 20
  },
  "metadata": {
    "floor": 1,
    "building": "main"
  }
}
```

### Update Zone

```http
PUT /api/zones/{zone_id}
```

### Delete Zone

```http
DELETE /api/zones/{zone_id}
```

### Get Zone Sensors

```http
GET /api/zones/{zone_id}/sensors
```

### Preview Zone

```http
GET /api/zones/{zone_id}/preview
```

Returns zone visualization data for the UI canvas.

## Patterns API

### List Pattern Types

```http
GET /api/patterns/types
```

**Response:**

```json
{
  "types": [
    {
      "id": "occupancy_field",
      "name": "Occupancy Field",
      "description": "Detects occupancy using sensor fusion",
      "config_schema": {
        "threshold": {"type": "number", "default": 0.7},
        "min_sensors": {"type": "integer", "default": 2}
      }
    },
    {
      "id": "queue_flow",
      "name": "Queue Flow",
      "description": "Monitors queue dynamics"
    },
    {
      "id": "adl_tracker",
      "name": "ADL Tracker",
      "description": "Tracks activities of daily living"
    }
  ]
}
```

### Get Pattern Type Details

```http
GET /api/patterns/types/{type_id}
```

### Test Pattern

```http
POST /api/patterns/test
```

**Request Body:**

```json
{
  "pattern_type": "occupancy_field",
  "config": {
    "threshold": 0.8
  },
  "test_data": {
    "sensors": ["sensor_001", "sensor_002"],
    "readings": [
      {"sensor_id": "sensor_001", "value": 1},
      {"sensor_id": "sensor_002", "value": 1}
    ]
  }
}
```

## Agents API

### List Agents

```http
GET /api/agents
```

**Response:**

```json
{
  "agents": [
    {
      "id": "agent_001",
      "name": "entrance_monitor",
      "pattern_type": "occupancy_field",
      "status": "running",
      "zone_id": "zone_entrance",
      "stats": {
        "ticks": 15432,
        "events": 89,
        "avg_tick_ms": 2.3,
        "last_tick": "2024-01-15T14:30:00Z"
      }
    }
  ]
}
```

### Get Agent

```http
GET /api/agents/{agent_id}
```

### Create Agent

```http
POST /api/agents
```

**Request Body:**

```json
{
  "name": "kitchen_occupancy",
  "pattern_type": "occupancy_field",
  "zone_id": "zone_kitchen",
  "config": {
    "threshold": 0.7,
    "min_sensors": 2,
    "decay_rate": 0.1
  },
  "auto_start": true
}
```

### Update Agent

```http
PUT /api/agents/{agent_id}
```

### Delete Agent

```http
DELETE /api/agents/{agent_id}
```

### Start Agent

```http
POST /api/agents/{agent_id}/start
```

### Stop Agent

```http
POST /api/agents/{agent_id}/stop
```

### Restart Agent

```http
POST /api/agents/{agent_id}/restart
```

### Get Agent Events

```http
GET /api/agents/{agent_id}/events
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | integer | Max events (default: 100) |
| `since` | ISO datetime | Events after this time |

## Events API

### Event Stream (SSE)

```http
GET /api/events/stream
```

Server-Sent Events stream for real-time updates.

**Event Types:**

- `agent_started` - Agent started running
- `agent_stopped` - Agent stopped
- `agent_error` - Agent encountered error
- `pattern_event` - Pattern emitted event
- `sensor_reading` - New sensor reading
- `system_alert` - System alert

**Example:**

```javascript
const events = new EventSource('/api/events/stream');

events.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.type, data.payload);
};
```

### Get Recent Events

```http
GET /api/events
```

## System API

### Health Check

```http
GET /api/system/health
```

**Response:**

```json
{
  "healthy": true,
  "checks": {
    "disk": {"healthy": true, "value": 45.2, "threshold": 90},
    "memory": {"healthy": true, "value": 62.1, "threshold": 85},
    "cpu": {"healthy": true, "value": 12.5, "threshold": 90}
  },
  "uptime_seconds": 86432,
  "active_alerts": 0
}
```

### System Status

```http
GET /api/system/status
```

**Response:**

```json
{
  "version": "0.1.0",
  "uptime_seconds": 86432,
  "sensors": {"total": 12, "active": 10},
  "zones": {"total": 5},
  "agents": {"total": 3, "running": 2, "stopped": 1},
  "database": {"size_bytes": 1048576, "path": "/home/pi/.spaxiom/edge.db"}
}
```

### Get Alerts

```http
GET /api/system/alerts
```

### Acknowledge Alert

```http
POST /api/system/alerts/{alert_id}/acknowledge
```

## Authentication API

See [Edge Security](edge_security.md) for detailed authentication documentation.

### Login

```http
POST /api/auth/login
```

### Logout

```http
POST /api/auth/logout
```

### Initial Setup

```http
POST /api/auth/setup
```

## Error Responses

All errors return a consistent format:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Sensor not found",
    "details": {"sensor_id": "sensor_999"}
  }
}
```

**Common Error Codes:**

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `BAD_REQUEST` | 400 | Invalid request data |
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource already exists |
| `INTERNAL_ERROR` | 500 | Server error |

## Rate Limiting

The API implements rate limiting:

- 100 requests per minute for read operations
- 20 requests per minute for write operations

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705329600
```
