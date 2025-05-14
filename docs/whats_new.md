# What's New in Spaxiom 0.1.0

We're excited to announce the first beta release of Spaxiom 0.1.0! This release includes several major features that greatly enhance the capabilities of the Spaxiom DSL.

## ONNX Inference

Spaxiom now supports AI model inference using ONNX Runtime, allowing you to integrate machine learning models with your sensor network:

- Run real-time object detection directly within your Spaxiom applications
- Generate entities automatically from detection results
- Integrate with spatial and temporal reasoning

```python
from spaxiom.ai import ONNXDetector
from spaxiom import on, exists

# Initialize ONNX-based person detector
detector = ONNXDetector(
    model_path="models/person_detector.onnx",
    input_name="image",
    output_name="detection",
    confidence_threshold=0.5
)

# Create an entity set to store detected persons
persons = EntitySet("Persons")

# Define condition based on entity detection
person_detected = exists(persons, lambda p: p.attrs.get("confidence", 0) > 0.7)

# Register an event handler
@on(person_detected)
def alert_person_detected():
    print("Person detected with high confidence!")
```

See the [ONNX Person Detection example](examples/onnx_person_demo.py) for a complete implementation.

## GPIO Hardware Integration

Connect your Spaxiom applications to the physical world with our new GPIO adapters for Raspberry Pi and similar devices:

- Read sensor data from digital pins using `GPIOSensor`
- Control output devices with `GPIOOutput`
- Compatible with both RPi.GPIO and gpiozero libraries

```python
from spaxiom.gpio import GPIOSensor, GPIOOutput
from spaxiom import on, Condition, within

# Create a door sensor on GPIO pin 17
door_sensor = GPIOSensor(
    name="front_door",
    pin=17,
    sensor_type="door",
    pull_up=True,
    active_low=True
)

# Create an LED output on GPIO pin 18
led = GPIOOutput(
    name="alert_light",
    pin=18
)

# Define condition and register handler
door_open = Condition(lambda: door_sensor.read() == 1)
door_open_long = within(30.0, door_open)

@on(door_open_long)
def alert_door_left_open():
    print("Door has been open for 30 seconds!")
    led.write(1)  # Turn on the LED
```

## Privacy Controls

Enhance data protection and privacy with our new privacy tagging system:

- Mark sensors as private to control data visibility
- Automatic redaction of private sensor values in logs
- Privacy warnings when accessing restricted data

```python
from spaxiom import Sensor

# Create a sensor with privacy settings
temperature = Sensor(
    name="bedroom_temp",
    sensor_type="temperature",
    location=(10, 12, 0),
    privacy="private"  # Mark this sensor as private
)

# Private values will be redacted in logs and outputs
```

## Statistical Analysis

Perform statistical analysis on sensor data streams with the new summarization capabilities:

- Call `summary()` on Condition instances to get a RollingSummary object
- Track statistics like min, max, mean, and variance
- Monitor trends and patterns over time

```python
from spaxiom import Sensor, Condition

# Create a temperature sensor
temp_sensor = Sensor("room_temp", "temperature", (0, 0, 0))

# Create a condition that reads the temperature
temp_reading = Condition(lambda: temp_sensor.read())

# Get a summary object for statistical analysis
temp_stats = temp_reading.summary(window_size=100)

# In your event handler or elsewhere:
def print_stats():
    print(f"Min: {temp_stats.min():.1f}°C")
    print(f"Max: {temp_stats.max():.1f}°C")
    print(f"Mean: {temp_stats.mean():.1f}°C")
    print(f"Variance: {temp_stats.variance():.2f}")
```

## CLI Scaffold Tool

Quickly start new projects with the CLI scaffolding tool:

- Generate script templates with `spax-run new`
- Customize the number of sensors and zones
- Configure privacy settings
- Get a ready-to-run application structure

```bash
# Create a basic demo
spax-run new my_app

# Customize with more sensors and zones
spax-run new complex_app --sensors 5 --zones 3 

# Disable privacy features
spax-run new simple_app --no-privacy
```

## CLI Improvements

- Added `--verbose` flag to enable detailed runtime logging:

```bash
# Run with verbose logging for troubleshooting
spax-run run my_app.py --verbose
```

The verbose mode provides detailed information about sensor readings, condition evaluations, plugin loading, and internal runtime events, making it easier to debug complex applications.

## Other Improvements

- Enhanced error handling across all modules
- More comprehensive test coverage (over 60%)
- Updated documentation with privacy and hardware examples
- Various bug fixes and performance improvements

## Getting Started with 0.1.0

To upgrade to the latest version:

```bash
pip install --upgrade spaxiom
```

For new installations:

```bash
pip install spaxiom
```

Check out the [Quick Start Guide](quickstart.md) to begin using these new features! 