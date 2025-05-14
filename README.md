                ███████╗██████╗  █████╗ ██╗  ██╗██╗ ██████╗ ███╗   ███╗
                ██╔════╝██╔══██╗██╔══██╗╚██╗██╔╝██║██╔═══██╗████╗ ████║
                ███████╗██████╔╝███████║ ╚███╔╝ ██║██║   ██║██╔████╔██║
                ╚════██║██╔═══╝ ██╔══██║ ██╔██╗ ██║██║   ██║██║╚██╔╝██║
                ███████║██║     ██║  ██║██╔╝ ██╗██║╚██████╔╝██║ ╚═╝ ██║
                ╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝     ╚═╝
```

# Spaxiom-DSL

[![PyPI version](https://badge.fury.io/py/spaxiom.svg)](https://pypi.org/project/spaxiom/)
[![Spaxiom CI](https://github.com/joescanlin/spaxiom-dsl/actions/workflows/ci.yml/badge.svg)](https://github.com/joescanlin/spaxiom-dsl/actions/workflows/ci.yml)
[![Project Status: Beta](https://img.shields.io/badge/Project%20Status-Beta-orange.svg)](https://github.com/joescanlin/spaxiom-dsl)

An embedded domain-specific language for spatial sensor fusion, temporal reasoning, and real-time event detection.

```
     ╔═══════════╗                   ╔═══════════╗
     ║ SENSORS   ║                   ║ DETECTION ║
     ║ ●━━━━━━━━━║═══════════════════║━━━━━━━━━● ║
     ║ ●━━━━━━━━━║═══════════════════║━━━━━━━━━● ║
     ╚═══════════╝                   ╚═══════════╝
           │                               ▲
           ▼                               │
     ╔═══════════╗     ╔═══════════╗     ╔═══════════╗
     ║           ║     ║           ║     ║           ║
     ║  SPATIAL  ║════>║ TEMPORAL  ║════>║   EVENTS  ║
     ║           ║     ║           ║     ║           ║
     ╚═══════════╝     ╚═══════════╝     ╚═══════════╝
```

## What is Spaxiom?

Spaxiom is a powerful Domain-Specific Language (DSL) designed for building intelligent systems that work with:

- **Spatial Data**: Zones, sensors, and physical spaces
- **Temporal Logic**: Time-based conditions and historical analysis
- **Event Processing**: Triggering actions based on complex conditions
- **Entity Management**: Tracking and querying objects in your system
- **Physical Units**: Working with measurements in a type-safe manner

With Spaxiom, you can easily define complex conditions that span across space and time, and connect them to real-world events.

## Key Features

- 🏠 **Spatial Zones**: Define and work with 2D spatial regions
- ⚡ **Sensors**: Interface with various sensor types and data streams
- ⏱️ **Temporal Logic**: Create conditions that must be true for specific durations
- 🔄 **Event Callbacks**: Register event handlers triggered by complex conditions
- 👥 **Entity Tracking**: Maintain collections of entities with flexible attributes
- 📏 **Physical Units**: Work with measurements and conversions seamlessly
- 🧩 **Logical Operators**: Combine conditions using intuitive &, |, and ~ operators
- 📄 **YAML Configuration**: Define sensors and system setup through YAML files

## Installation

```bash
pip install -e .
```

## Quick Examples

### Spatial & Temporal Logic

```python
from spaxiom import Sensor, Zone, Condition, on, within

# Define a zone and sensor
office_zone = Zone(0, 0, 10, 10)
motion_sensor = Sensor("motion1", "motion", (5, 5, 0))

# Create condition based on sensor data
motion_detected = Condition(lambda: motion_sensor.read() > 0.5)

# Make it temporal - must be true for 5 seconds
sustained_motion = within(5.0, motion_detected)

# Register an event handler
@on(sustained_motion)
def alert_sustained_motion():
    print("Motion has been detected for 5 seconds!")
```

### Entity Management

```python
from spaxiom import EntitySet, Entity, exists, on, Condition

# Create a collection of entities
persons = EntitySet("Persons")

# Add entities with attributes
persons.add(Entity(attrs={"type": "person", "confidence": 0.9}))

# Create condition based on entity existence
person_detected = exists(persons, lambda p: p.attrs.get("confidence", 0) > 0.8)

# Register an event handler
@on(person_detected)
def alert_person():
    print("Person detected with high confidence!")
```

### Physical Units

```python
from spaxiom import Quantity

# Create measurements with units
distance = Quantity(10, "m")
time = Quantity(2, "s")

# Automatic unit conversion
speed = distance / time  # 5 m/s

# Convert to different units
speed_kph = speed.to("km/hour")  # 18 km/h
```

### YAML Configuration

```python
from spaxiom import load_sensors_from_yaml, on, Condition, within

# Load sensors from YAML configuration file
sensors = load_sensors_from_yaml("sensors_config.yaml")

# Access sensors by name from the registry
from spaxiom import SensorRegistry
registry = SensorRegistry()
motion_sensor = registry.get("motion_sensor1")

# Create condition based on sensor from config
motion_detected = Condition(lambda: motion_sensor.read() > 0.5)

# Register event handler
@on(motion_detected)
def alert_motion():
    print("Motion detected!")
```

Example YAML configuration:

```yaml
sensors:
  - name: motion_sensor1
    type: gpio_digital
    pin: 17
    location: [0, 0, 0]
    pull_up: true
    
  - name: temperature_sensor1
    type: random
    location: [1, 2, 0]
    hz: 5.0
```

## Documentation

### Online Documentation

The full documentation is available online at: 
https://joescanlin.github.io/spaxiom-dsl/

### Local Documentation

For local development, you can build and view the documentation using MkDocs:

```bash
# Install MkDocs and required extensions
pip install mkdocs-material pymdown-extensions

# Serve the documentation locally
mkdocs serve

# Build the documentation
mkdocs build
```

The documentation source files are located in the `docs/` directory. Some key sections:

- [Temporal and Entity Operations](docs/temporal_and_entities.md)
- [Quick Start Guide](docs/quickstart.md)
- [CLI Usage](docs/cli_usage.md)

### Documentation Updates

The documentation is automatically deployed to GitHub Pages when changes are pushed to the main branch.
Changes to files in the `docs/` directory or to `mkdocs.yml` will trigger a new build and deployment.

## License

MIT 