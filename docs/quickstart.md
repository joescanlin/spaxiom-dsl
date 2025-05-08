# Spaxiom DSL Quick Start Guide

This guide will help you get started with Spaxiom DSL, a Python library for spatial sensor fusion and AI.

## Installation

You can install Spaxiom directly from the repository:

```bash
# Clone the repository
git clone https://github.com/username/spaxiom-dsl.git
cd spaxiom-dsl

# Install in development mode
pip install -e .

# To install with development dependencies
pip install -e .[dev]
```

## Hello Runtime Example

Create a file named `hello_runtime.py` with the following code:

```python
from spaxiom import Sensor, Zone, Condition, on
from spaxiom.sensor import RandomSensor
from spaxiom.runtime import start_blocking
import time

# Create a random sensor at location (0, 0, 0)
rs = RandomSensor('random1', location=(0.0, 0.0, 0.0))

# Define a zone for detection
detection_zone = Zone(0.0, 0.0, 1.0, 1.0)

# Define conditions
high_value = Condition(lambda: rs.read() > 0.7)
in_zone = Condition(lambda: detection_zone.contains((rs.read(), rs.read())))

# Register event handlers
@on(high_value)
def alert_high_value():
    print(f"HIGH VALUE DETECTED: {rs.read():.3f}")

@on(in_zone)
def alert_in_zone():
    print(f"POINT IN ZONE: ({rs.read():.3f}, {rs.read():.3f})")

@on(high_value & in_zone)
def alert_high_in_zone():
    print("HIGH VALUE AND IN ZONE!")

# Start the runtime with a 500ms polling interval
if __name__ == "__main__":
    print("Starting Spaxiom Runtime...")
    print("Press Ctrl+C to exit")
    start_blocking(poll_ms=500)
```

## Running the Example

Run the example with:

```bash
python hello_runtime.py
```

## Example Output

When you run the example, you'll see output similar to this:

```
Starting Spaxiom Runtime...
Press Ctrl+C to exit
[Spaxiom] Runtime started with poll interval of 500ms
[Spaxiom] Fired alert_high_value
HIGH VALUE DETECTED: 0.781
[Spaxiom] Fired alert_in_zone
POINT IN ZONE: (0.345, 0.567)
[Spaxiom] Fired alert_high_value
HIGH VALUE DETECTED: 0.892
[Spaxiom] Fired alert_high_in_zone
HIGH VALUE AND IN ZONE!
[Spaxiom] Fired alert_in_zone
POINT IN ZONE: (0.456, 0.234)
[Spaxiom] Fired alert_high_value
HIGH VALUE DETECTED: 0.723
^C
[Spaxiom] Runtime stopped by user
```

The output shows:
1. The runtime starting with a 500ms polling interval
2. Event handlers being triggered when their conditions are met
3. The runtime stopping when you press Ctrl+C

## Next Steps

- Check out the [Specification](spec_draft.md) for more details on the DSL syntax
- Explore the examples in the `examples/` directory
- Read the API documentation for more advanced usage 