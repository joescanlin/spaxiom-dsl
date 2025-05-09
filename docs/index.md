# Welcome to Spaxiom DSL

<div align="center" style="margin-bottom: 2em;">
<pre style="line-height: 1.2;">
                ███████╗██████╗  █████╗ ██╗  ██╗██╗ ██████╗ ███╗   ███╗
                ██╔════╝██╔══██╗██╔══██╗╚██╗██╔╝██║██╔═══██╗████╗ ████║
                ███████╗██████╔╝███████║ ╚███╔╝ ██║██║   ██║██╔████╔██║
                ╚════██║██╔═══╝ ██╔══██║ ██╔██╗ ██║██║   ██║██║╚██╔╝██║
                ███████║██║     ██║  ██║██╔╝ ██╗██║╚██████╔╝██║ ╚═╝ ██║
                ╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝     ╚═╝
</pre>
</div>

Spaxiom is a powerful Domain-Specific Language (DSL) designed for building intelligent systems that work with:

- **Spatial Data**: Zones, sensors, and physical spaces
- **Temporal Logic**: Time-based conditions and historical analysis
- **Event Processing**: Triggering actions based on complex conditions
- **Entity Management**: Tracking and querying objects in your system
- **Physical Units**: Working with measurements in a type-safe manner

## System Architecture

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

## Key Features

- 🏠 **Spatial Zones**: Define and work with 2D spatial regions
- ⚡ **Sensors**: Interface with various sensor types and data streams
- ⏱️ **Temporal Logic**: Create conditions that must be true for specific durations
- 🔄 **Event Callbacks**: Register event handlers triggered by complex conditions
- 👥 **Entity Tracking**: Maintain collections of entities with flexible attributes
- 📏 **Physical Units**: Work with measurements and conversions seamlessly
- 🧩 **Logical Operators**: Combine conditions using intuitive &, |, and ~ operators

## Installation

```bash
pip install -e .
```

## Quick Example

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

## Documentation Sections

- [Quick Start Guide](quickstart.md): Get up and running with Spaxiom
- [API Reference](api/overview.md): Detailed documentation of all Spaxiom components
- [Temporal and Entity Operations](temporal_and_entities.md): Working with time and entities
- [CLI Usage](cli_usage.md): Using the command-line interface
- [Examples](examples/overview.md): Real-world examples and use cases

## License

Spaxiom DSL is released under the MIT License. 