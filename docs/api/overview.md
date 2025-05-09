# API Overview

Spaxiom DSL provides a comprehensive API for working with spatial sensor fusion, temporal reasoning, and event detection. This section documents the core components of the API.

## Core Components

### Sensors

The `Sensor` class is the foundation for all data acquisition in Spaxiom. Sensors provide readings from the physical or virtual world that can be processed and analyzed.

```python
from spaxiom import Sensor

# Create a sensor
temp_sensor = Sensor("temp1", "temperature", (0, 0, 0))

# Read a value from the sensor
value = temp_sensor.read()
```

### Zones

The `Zone` class defines spatial regions that can contain sensors, entities, or other objects. Zones are used for spatial reasoning and containment checks.

```python
from spaxiom import Zone

# Define a rectangular zone
office_zone = Zone(0, 0, 10, 10)

# Check if a point is in the zone
is_in_zone = office_zone.contains((5, 5))
```

### Conditions

The `Condition` class wraps boolean functions that can be combined with logical operators to create complex conditions for event triggering.

```python
from spaxiom import Condition

# Create a condition
is_hot = Condition(lambda: temp_sensor.read() > 30.0)

# Combine conditions
is_occupied = Condition(lambda: motion_sensor.read() > 0.5)
hot_and_occupied = is_hot & is_occupied
```

### Events

The `on` decorator registers callbacks that are triggered when specific conditions are met.

```python
from spaxiom import on

@on(hot_and_occupied)
def alert_hot_and_occupied():
    print("Room is hot and occupied!")
```

### Entities

The `Entity` and `EntitySet` classes provide a way to track and query collections of objects with arbitrary attributes.

```python
from spaxiom import Entity, EntitySet

# Create a collection of entities
persons = EntitySet("Persons")

# Add an entity
persons.add(Entity(attrs={"type": "person", "name": "Alice"}))

# Query entities
for person in persons:
    print(person.attrs.get("name"))
```

### Fusion

The `WeightedFusion` class allows combining multiple sensor inputs with specified weights to create derived sensors.

```python
from spaxiom import WeightedFusion

# Create a fusion sensor
comfort_index = WeightedFusion(
    name="comfort",
    sensors=[temp_sensor, humidity_sensor],
    weights=[0.6, 0.4],
    location=(0, 0, 0)
)

# Read the fused value
comfort = comfort_index.read()
```

## Utility Functions

In addition to the core classes, Spaxiom provides several utility functions for temporal reasoning and other operations:

- `within(seconds, condition)`: Creates a temporal condition that must be true for a specific duration
- `sequence(*conditions, within_s=seconds)`: Detects ordered sequences of events within a time window
- `exists(entity_set, predicate)`: Checks if entities matching a predicate exist in an entity set
- `transitioned_to_true(condition)`: Detects when a condition transitions from false to true

These functions are documented in detail in their respective sections. 