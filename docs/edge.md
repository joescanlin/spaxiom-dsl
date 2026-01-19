# Edge Deployment Guide

Spaxiom Edge provides a complete deployment solution for running INTENT patterns on edge devices like Raspberry Pi. It includes persistent storage, a REST API, and a web-based management interface.

## Overview

The Edge system provides:

- **Persistent Storage**: SQLite database for sensors, zones, patterns, and agents
- **REST API**: Full HTTP API for integration and management
- **Web UI**: Browser-based interface for monitoring and configuration
- **Agent Management**: Deploy, monitor, and control pattern agents
- **Production Hardening**: Authentication, HTTPS, monitoring, and backups

## Installation

Install Spaxiom with edge dependencies:

```bash
pip install spaxiom[edge]
```

For the full experience with CLI enhancements:

```bash
pip install spaxiom[edge,cli]
```

### Hardware Requirements

**Development:**

- Raspberry Pi 5 (8GB) recommended
- Any Linux/macOS/Windows system with Python 3.9+

**Production:**

- Raspberry Pi 5 (4GB) or better
- 16GB+ microSD card (Class 10 or better)
- Stable power supply

## Quick Start

### 1. Start the Edge Server

```bash
spax edge start
```

Or with custom options:

```bash
spax edge start --port 8085 --db ./my_edge.db
```

### 2. Access the Web UI

Open your browser to `http://localhost:8080` (or your configured port).

The web UI provides:

- **Dashboard**: System overview with health metrics
- **Sensors**: Register and configure sensors
- **Zones**: Define spatial zones with visual editor
- **Patterns**: Browse and configure INTENT patterns
- **Agents**: Deploy and monitor pattern agents
- **Settings**: System configuration

### 3. Register Sensors

Via the API:

```bash
curl -X POST http://localhost:8080/api/sensors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "front_door_motion",
    "sensor_type": "motion",
    "location": {"x": 10.0, "y": 5.0, "z": 0.0}
  }'
```

Or via the web UI Sensors page.

### 4. Create Zones

Define spatial regions for pattern detection:

```bash
curl -X POST http://localhost:8080/api/zones \
  -H "Content-Type: application/json" \
  -d '{
    "name": "entrance",
    "zone_type": "room",
    "bounds": {"x1": 0, "y1": 0, "x2": 20, "y2": 15}
  }'
```

### 5. Deploy an Agent

Create an agent to run a pattern:

```bash
curl -X POST http://localhost:8080/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "entrance_occupancy",
    "pattern_type": "occupancy_field",
    "zone_id": "zone_123",
    "config": {
      "threshold": 0.7,
      "min_sensors": 2
    }
  }'
```

## Configuration

### Database Location

Default: `~/.spaxiom/edge.db`

Override with environment variable:

```bash
export SPAXIOM_DB_PATH=/var/lib/spaxiom/edge.db
```

Or command line:

```bash
spax edge start --db /path/to/database.db
```

### Server Options

| Option | Environment Variable | Default | Description |
|--------|---------------------|---------|-------------|
| `--host` | `SPAXIOM_API_HOST` | `0.0.0.0` | Bind address |
| `--port` | `SPAXIOM_API_PORT` | `8080` | Server port |
| `--db` | `SPAXIOM_DB_PATH` | `~/.spaxiom/edge.db` | Database path |
| `--reload` | - | `false` | Auto-reload on changes |

### Logging

Configure log level:

```bash
export SPAXIOM_LOG_LEVEL=DEBUG
```

Log files are stored in `~/.spaxiom/logs/` by default.

## Web UI Features

### Dashboard

The dashboard shows:

- System health status (healthy/degraded/offline)
- Active sensor count
- Running agent count
- Recent events stream
- Resource usage (CPU, memory, disk)

### Zone Editor

The visual zone editor allows you to:

- Draw rectangular zones on a canvas
- Set zone properties (name, type)
- View sensor positions overlaid on zones
- Preview zone coverage

### Pattern Configuration

Each INTENT pattern type has a configuration form with:

- Pattern-specific parameters
- Sensor bindings
- Zone assignments
- Event handlers

### Agent Monitoring

Real-time agent monitoring includes:

- Status (running/stopped/error)
- Tick count and timing
- Events generated
- Error messages
- Start/stop/restart controls

## Running as a Service

### systemd (Linux)

Create `/etc/systemd/system/spaxiom-edge.service`:

```ini
[Unit]
Description=Spaxiom Edge Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi
Environment=SPAXIOM_DB_PATH=/var/lib/spaxiom/edge.db
ExecStart=/home/pi/.local/bin/spax edge start --port 8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable spaxiom-edge
sudo systemctl start spaxiom-edge
```

### Docker

```dockerfile
FROM python:3.11-slim

RUN pip install spaxiom[edge]

EXPOSE 8080

VOLUME /data

ENV SPAXIOM_DB_PATH=/data/edge.db

CMD ["spax", "edge", "start", "--host", "0.0.0.0"]
```

Build and run:

```bash
docker build -t spaxiom-edge .
docker run -d -p 8080:8080 -v spaxiom-data:/data spaxiom-edge
```

## Next Steps

- [Edge API Reference](edge_api.md) - Complete API documentation
- [Edge Security](edge_security.md) - Authentication, HTTPS, and hardening
- [INTENT Patterns](intent.md) - Available pattern types
