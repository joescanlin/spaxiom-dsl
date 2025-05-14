# Temporal and Entity Operations in Spaxiom

This document explains how to use the temporal (`within()`), entity (`exists()`), and privacy operations in Spaxiom DSL.

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

## Privacy Operations

Spaxiom supports privacy tags for sensors, allowing you to control how sensitive data is handled in your applications.

### Privacy Levels

Sensors can be tagged with one of two privacy levels:
- `"public"`: Default level, sensor values are displayed normally
- `"private"`: Sensitive data, values are redacted in logs and outputs

### Basic Syntax

When creating a sensor, you can specify its privacy level:

```python
Sensor(name, sensor_type, location, privacy="public"|"private")
```

### Examples

#### Creating Sensors with Privacy Levels

```python
from spaxiom import Sensor

# Public sensor (default)
public_sensor = Sensor("living_room_temp", "temperature", (0, 0, 0))

# Private sensor (explicitly set)
private_sensor = Sensor("bedroom_occupancy", "presence", (5, 5, 0), privacy="private")
```

#### Privacy Inheritance in Fusion Sensors

Privacy settings are automatically inherited in fusion sensors. If any component sensor is private, the fusion result is also treated as private:

```python
from spaxiom import Sensor, RandomSensor

# Create sensors with different privacy settings
public_sensor = RandomSensor("public_temperature", (0, 0, 0))
private_sensor = RandomSensor("private_humidity", (0, 0, 0), privacy="private")

# Public + Public = Public
public_fusion = public_sensor.fuse_with(
    public_sensor,
    strategy="average",
    name="public_fusion"
)

# Public + Private = Private (automatically)
mixed_fusion = public_sensor.fuse_with(
    private_sensor,
    strategy="average",
    name="mixed_fusion"
)

# Check privacy levels
print(f"Public fusion privacy: {public_fusion.privacy}")  # "public"
print(f"Mixed fusion privacy: {mixed_fusion.privacy}")    # "private"
```

#### Runtime Handling of Private Sensors

The runtime automatically redacts values from private sensors in logs and console output:

```python
from spaxiom import RandomSensor, SensorRegistry, Condition, on
from spaxiom.runtime import format_sensor_value

# Create sensors with different privacy levels
public_sensor = RandomSensor("living_room_temp", (0, 0, 0))
private_sensor = RandomSensor("bedroom_motion", (5, 0, 0), privacy="private")

# Using the format_sensor_value function respects privacy
public_value = public_sensor.read()
private_value = private_sensor.read()

print(f"Public sensor value: {format_sensor_value(public_sensor, public_value)}")   # Shows actual value
print(f"Private sensor value: {format_sensor_value(private_sensor, private_value)}") # Shows "***"

# When using the runtime, private values are automatically redacted
# and a warning is logged once per run per private sensor
```

#### SensorRegistry Privacy Methods

You can use `SensorRegistry` to get sensors based on their privacy level:

```python
from spaxiom import SensorRegistry

# Get all sensors
registry = SensorRegistry()
all_sensors = registry.list_all()

# Get only public sensors
public_sensors = registry.list_public()

# Get only private sensors
private_sensors = registry.list_private()
```

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

### Privacy-Aware Real-World Example

Here's an example of a smart home system that respects privacy:

```python
from spaxiom import Sensor, Zone, Condition, on, within, SensorRegistry
from spaxiom.runtime import format_sensor_value
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Create zones for different areas
living_room = Zone(0, 0, 5, 5)
bedroom = Zone(6, 0, 10, 5)
bathroom = Zone(6, 6, 10, 10)

# Create sensors with appropriate privacy levels
living_room_temp = Sensor("living_temp", "temperature", (2.5, 2.5, 0))  # public by default
bedroom_motion = Sensor("bedroom_motion", "motion", (8, 2.5, 0), privacy="private")
bathroom_presence = Sensor("bathroom_presence", "presence", (8, 8, 0), privacy="private")

# Define conditions
high_temp = Condition(lambda: living_room_temp.read() > 25.0)
bedroom_movement = Condition(lambda: bedroom_motion.read() > 0.5)
bathroom_occupied = Condition(lambda: bathroom_presence.read() > 0.5)

# Create temporal conditions
sustained_high_temp = within(60.0, high_temp)
sustained_bedroom_motion = within(5.0, bedroom_movement)
sustained_bathroom_presence = within(2.0, bathroom_occupied)

# Register event handlers
@on(sustained_high_temp)
def adjust_temperature():
    temp = living_room_temp.read()
    # Public sensor, so we can log the actual value
    logging.info(f"Adjusting temperature - current value: {temp}°C")
    # Set up temperature adjustment...

@on(sustained_bedroom_motion)
def bedroom_occupied():
    # Private sensor, so we respect privacy in our logs
    value = bedroom_motion.read()
    formatted = format_sensor_value(bedroom_motion, value)
    logging.info(f"Bedroom motion detected: {formatted}")
    # Adjust bedroom settings...

@on(sustained_bathroom_presence)
def bathroom_occupied():
    # Private sensor, so we respect privacy in our logs
    value = bathroom_presence.read()
    formatted = format_sensor_value(bathroom_presence, value)
    logging.info(f"Bathroom presence detected: {formatted}")
    # Turn on fan and lights...

# Start the runtime
from spaxiom.runtime import start_blocking
start_blocking()
```

This example showcases a privacy-aware smart home system where:
1. Public environmental sensors (like temperature) show their actual values
2. Private occupancy sensors (in bedrooms and bathrooms) have their values redacted in logs
3. The system still functions correctly with all sensors, but respects privacy in its outputs 