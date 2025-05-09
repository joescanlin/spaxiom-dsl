# Temporal and Entity Operations in Spaxiom

This document explains how to use the temporal (`within()`) and entity (`exists()`) operations in Spaxiom DSL.

## Temporal Operations

The `within()` function allows you to create conditions that must be true continuously for a specified duration before evaluating to true.

### Basic Syntax

```python
within(duration_seconds, condition)
```

### Parameters

- `duration_seconds`: The duration in seconds for which the condition must be continuously true
- `condition`: The base condition to evaluate over time

### Examples

#### Simple Temporal Condition

Check if a sensor value has been above a threshold for at least 3 seconds:

```python
from spaxiom import Condition, within
from spaxiom.sensor import Sensor

# Create a sensor
temp_sensor = Sensor("temp1", "temperature", (0, 0, 0))

# Define a basic condition
high_temp = Condition(lambda: temp_sensor.read() > 30.0)

# Create a temporal condition
high_temp_sustained = within(3.0, high_temp)

# This will only evaluate to true if temp_sensor.read() has been
# continuously > 30.0 for at least 3 seconds
if high_temp_sustained():
    print("Temperature has been high for at least 3 seconds!")
```

#### Using with Event Handlers

Register a callback that only fires after a condition has been true for 5 seconds:

```python
from spaxiom import Condition, within, on
from spaxiom.sensor import Sensor

motion_sensor = Sensor("motion1", "motion", (0, 0, 0))

# Basic condition: motion detected
motion_detected = Condition(lambda: motion_sensor.read() > 0.5)

# Temporal condition: motion sustained for 5 seconds
sustained_motion = within(5.0, motion_detected)

# This callback will only fire after 5 seconds of continuous motion
@on(sustained_motion)
def handle_sustained_motion():
    print("Sustained motion detected for 5 seconds!")
```

## Entity Operations

The `exists()` function allows you to check if any entities in an `EntitySet` satisfy a given predicate.

### Basic Syntax

```python
exists(entity_set, predicate=None)
```

### Parameters

- `entity_set`: The `EntitySet` to check
- `predicate` (optional): A function that takes an entity and returns a boolean. If not provided, the function checks if the entity set has any entities.

### Examples

#### Simple Existence Check

Check if there are any entities in a set:

```python
from spaxiom import EntitySet, Entity, exists, Condition

# Create an entity set
persons = EntitySet("Persons")

# Check if any persons exist
persons_exist = exists(persons)

# Use in a condition
if persons_exist():
    print("At least one person exists in the set")
```

#### Filtering with Predicates

Check if there are any entities matching a specific criterion:

```python
from spaxiom import EntitySet, Entity, exists, Condition

# Create an entity set
sensors = EntitySet("Sensors")

# Add some entities with attributes
sensors.add(Entity(attrs={"type": "temperature", "value": 25.0}))
sensors.add(Entity(attrs={"type": "humidity", "value": 60.0}))
sensors.add(Entity(attrs={"type": "motion", "value": 0.0}))

# Check if any temperature sensors exceed a threshold
high_temp_exists = exists(sensors, lambda s: s.attrs.get("type") == "temperature" and s.attrs.get("value", 0) > 30.0)

# Use in a condition
if high_temp_exists():
    print("At least one temperature sensor is reading high!")
```

#### Combining with Events

Using exists() with event handlers:

```python
from spaxiom import EntitySet, Entity, exists, on, Condition

# Create an entity set for detected persons
persons = EntitySet("Persons")

# Create a condition using exists()
person_detected = exists(persons, lambda p: p.attrs.get("confidence", 0) > 0.8)

# Register an event handler
@on(person_detected)
def alert_person_detected():
    print("A person with high confidence was detected!")
```

## Combining Temporal and Entity Operations

You can combine both operations for powerful temporal-entity checking:

```python
from spaxiom import EntitySet, Entity, exists, within, on, Condition

# Create an entity set
vehicles = EntitySet("Vehicles")

# Check if any vehicles exist
vehicle_exists = exists(vehicles)

# Check if a vehicle has been continuously present for 10 seconds
vehicle_stopped = within(10.0, vehicle_exists)

# Register an event handler
@on(vehicle_stopped)
def alert_stopped_vehicle():
    print("A vehicle has been stopped for 10 seconds")
```

This will only trigger the alert when a vehicle has been continuously present for 10 seconds.

## Real-World Use Case

Here's a more complex example combining multiple conditions:

```python
from spaxiom import EntitySet, Entity, Zone, exists, within, on, Condition

# Create zones and entity sets
restricted_zone = Zone(0, 0, 10, 10)
persons = EntitySet("Persons")
vehicles = EntitySet("Vehicles")

# Define conditions
person_in_zone = exists(persons, lambda p: restricted_zone.contains((p.attrs.get("x", 0), p.attrs.get("y", 0))))
vehicle_in_zone = exists(vehicles, lambda v: restricted_zone.contains((v.attrs.get("x", 0), v.attrs.get("y", 0))))

# Create a combined condition
intrusion = person_in_zone & vehicle_in_zone

# Create a temporal condition
sustained_intrusion = within(30.0, intrusion)

# Register an event handler
@on(sustained_intrusion)
def security_alert():
    print("ALERT: Person and vehicle in restricted zone for 30 seconds!")
```

This example demonstrates a security system that alerts when both a person and a vehicle have been detected in a restricted zone for at least 30 seconds. 