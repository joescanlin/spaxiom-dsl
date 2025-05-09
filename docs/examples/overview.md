# Examples Overview

Spaxiom comes with a variety of examples that demonstrate its capabilities and provide starting points for your own applications. Below is a summary of the available examples.

## Smart Building Example

The [Smart Building](smart_building.md) example demonstrates how to use Spaxiom for building automation and occupancy detection:

- Reading historical sensor data from CSV files
- Defining multiple zones (office area, meeting room)
- Detecting occupancy using pressure and thermal sensors
- Creating a comfort index by fusing sensor data with custom weights
- Logging occupancy events in real-time

```python
# Define occupancy conditions
pressure_a_active = Condition(lambda: pressure_a.read() > 0.5)
thermal_a_active = Condition(lambda: thermal_a.read() > 22.0)
person_in_a = pressure_a_active & thermal_a_active

# Add temporal constraint - must be true for 3 seconds
sustained_presence_a = within(3.0, person_in_a)

# Register callback for occupancy events
@on(sustained_presence_a)
def notify_zone_a_occupied():
    comfort = comfort_a.read()
    logger.info(f"ZONE A OCCUPIED - Comfort Index: {comfort:.2f}")
```

## Sensor Fusion Example

Sensor fusion allows combining multiple sensor inputs:

- Creating different types of sensors (pressure, thermal, motion)
- Combining sensor outputs using various fusion strategies
- Using weighted averages for data fusion
- Creating derived sensors with custom transformations

```python
# Create fusion sensor with custom weights
fusion_sensor = WeightedFusion(
    name="fusion_sensor",
    sensors=[pressure_sensor, thermal_sensor],
    weights=[0.7, 0.3],
    location=(0, 0, 0)
)

# Read the fused value
fused_value = fusion_sensor.read()
```

## Temporal Sequences Example

Temporal sequences allow detecting ordered events:

- Creating event sensors for different steps in a sequence
- Defining a temporal sequence pattern with the `sequence()` function
- Adding time constraints with the `within_s` parameter
- Triggering callbacks when sequences are detected

```python
# Create a sequence pattern
entry_sequence = sequence(
    motion_outside_detected,
    door_opened,
    motion_inside_detected,
    lights_on,
    within_s=15.0
)

# Register callback for the sequence
@on(entry_sequence)
def welcome_home():
    print("Welcome home sequence detected!")
```

## Running the Examples

To run any of the examples, use the following command from the project root directory:

```bash
python examples/example_name.py
```

For example:

```bash
python examples/smart_building.py
```

You can modify the examples to experiment with different parameters, conditions, and callback functions to suit your specific use case. 