# Spaxiom DSL Specification Draft

## Overview
Spaxiom is an embedded domain-specific language (DSL) for spatial sensor fusion and AI, implemented in Python. It provides a concise syntax for defining sensors, zones, conditions, and event handlers.

## Core Components

### Sensors
Sensors represent data sources in physical space.

```python
# Define a sensor with name, type, and location
lidar = Sensor(name="front_lidar", sensor_type="lidar", location=(0.0, 0.0, 1.5))

# Custom sensor types can extend the base Sensor class
temp_sensor = TemperatureSensor(name="cabin_temp", location=(1.0, 0.5, 1.2))
```

### Zones
Zones define spatial areas for event triggering.

```python
# Define a rectangular zone with corners (x1, y1) and (x2, y2)
entry_zone = Zone(0.0, 0.0, 5.0, 5.0)

# Check if a point is within a zone
is_inside = entry_zone.contains((2.5, 3.0))
is_inside = entry_zone.contains(Point(2.5, 3.0))
```

### Conditions
Conditions are boolean expressions that can be combined using logical operators.

```python
# Simple condition
is_hot = Condition(lambda: temp_sensor.read() > 30.0)

# Sensor in zone condition
in_zone = Condition(lambda: entry_zone.contains(vehicle_sensor.location))

# Combine conditions with logical operators
is_actionable = is_hot & in_zone  # AND
is_alert = is_hot | in_zone       # OR
is_normal = ~is_hot               # NOT
```

### Event Handlers
Event handlers define actions triggered by conditions.

```python
# Define an event handler that runs when a condition is met
@on(in_zone)
def handle_zone_entry():
    print("Sensor entered the zone!")

# Complex conditions can be used
@on(is_hot & ~in_zone)
def handle_hot_outside_zone():
    alert("Temperature high outside monitored zone")
```

### Runtime
The runtime system polls sensors and evaluates conditions.

```python
# Start the runtime with a polling interval
start_blocking(poll_ms=100)  # Blocking call
await start_runtime(poll_ms=100)  # Async version
```

## Complete Example

```python
from spaxiom import Sensor, Zone, Condition, on, start_blocking

# Define sensors
temp_sensor = Sensor(name="temp", sensor_type="temperature", location=(0.0, 0.0, 0.0))

# Define zones
monitoring_zone = Zone(0.0, 0.0, 10.0, 10.0)

# Define conditions
is_hot = Condition(lambda: temp_sensor.read() > 30.0)
in_zone = Condition(lambda: monitoring_zone.contains(temp_sensor.location))

# Define event handlers
@on(is_hot & in_zone)
def handle_hot_in_zone():
    print("High temperature detected in monitoring zone!")

# Start the runtime
start_blocking(poll_ms=100)
```

## Out of Scope

The following features are explicitly **NOT** in scope for the current version:

- 3D spatial zones (only 2D rectangular zones are supported)
- Complex geometric shapes (polygons, circles, etc.)
- Machine learning integrations
- Distributed sensor networks
- Real-time guarantees (best-effort only)
- Persistence layer for sensor data
- User authentication/authorization
- Web/mobile interfaces
- Custom visualization tools
- External API integrations
- Time-series forecasting
- Custom query language 