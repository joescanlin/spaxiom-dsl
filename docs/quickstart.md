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

## Creating a Custom Plugin

Spaxiom supports extending its functionality through plugins. This example shows how to create a custom CO2 sensor plugin.

### Creating a CO2Sensor Plugin

Create a file named `co2_plugin.py` with the following code:

```python
import random
import time
from typing import Optional, Dict, Any, Tuple

from spaxiom import register_plugin, Sensor

class CO2Sensor(Sensor):
    """
    A custom CO2 sensor that simulates carbon dioxide readings in parts per million (ppm).
    
    Features:
    - Baseline CO2 level with random fluctuations
    - Configurable sensor sensitivity and range
    - Simulates real-world CO2 concentration patterns
    """
    
    def __init__(
        self,
        name: str,
        location: Tuple[float, float, float],
        baseline_ppm: float = 400.0,  # Typical outdoor CO2 level
        fluctuation: float = 50.0,    # Amount of random fluctuation
        max_ppm: float = 2000.0,      # Maximum possible reading
        hz: float = 1.0,              # Polling frequency
        privacy: str = "public",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the CO2 sensor with the given parameters."""
        # Calculate sample period from frequency
        sample_period = 1.0 / hz if hz > 0 else 0.0
        
        # Set up metadata if not provided
        if metadata is None:
            metadata = {}
        metadata.update({"unit": "ppm", "type": "carbon_dioxide"})
        
        super().__init__(
            name=name,
            sensor_type="co2",
            location=location,
            privacy=privacy,
            sample_period_s=sample_period,
            metadata=metadata,
        )
        
        self.baseline_ppm = baseline_ppm
        self.fluctuation = fluctuation
        self.max_ppm = max_ppm
        self.last_reading_time = time.time()
        self.current_value = baseline_ppm
    
    def _read_raw(self) -> float:
        """
        Generate a simulated CO2 reading in parts per million (ppm).
        
        Returns:
            A CO2 concentration value in ppm
        """
        now = time.time()
        time_diff = now - self.last_reading_time
        self.last_reading_time = now
        
        # Simulate CO2 fluctuations
        drift = random.uniform(-self.fluctuation, self.fluctuation) * time_diff
        self.current_value += drift
        
        # Ensure values stay within reasonable bounds
        self.current_value = max(300.0, min(self.current_value, self.max_ppm))
        
        return self.current_value
    
    def is_high(self, threshold: float = 1000.0) -> bool:
        """
        Check if CO2 levels are above a threshold.
        
        Args:
            threshold: The CO2 concentration threshold in ppm
            
        Returns:
            True if current CO2 level exceeds the threshold
        """
        return self.read() > threshold
    
    def __repr__(self) -> str:
        """Return a string representation of the CO2 sensor."""
        return f"CO2Sensor(name='{self.name}', location={self.location}, baseline={self.baseline_ppm}ppm)"


@register_plugin
def setup_co2_sensors():
    """
    Register the CO2 sensor type with Spaxiom.
    
    This function is decorated with @register_plugin, which means it will be 
    automatically called when the Spaxiom runtime starts.
    """
    print("[Plugin] Registering CO2Sensor plugin")
    
    # Create a demonstration CO2 sensor
    CO2Sensor(
        name="living_room_co2",
        location=(1.0, 2.0, 0.0),
        baseline_ppm=450.0,  # Slightly elevated indoor level
        hz=2.0,
        metadata={"room": "living_room"},
    )
    
    # Create another CO2 sensor with different parameters
    CO2Sensor(
        name="bedroom_co2",
        location=(5.0, 3.0, 0.0),
        baseline_ppm=420.0,
        fluctuation=30.0,
        hz=1.0,
        metadata={"room": "bedroom"},
    )
    
    print("[Plugin] CO2Sensor plugin registered with 2 sensors")
```

### Using the CO2Sensor Plugin

Create a file named `co2_monitor.py` to use the plugin:

```python
from spaxiom import Condition, on, within, SensorRegistry
from spaxiom.runtime import start_blocking
import importlib

def main():
    """Run the CO2 monitoring application."""
    print("\nCO2 Monitoring with Spaxiom")
    print("===========================")
    
    # Manually import the plugin 
    # (Alternative: place it in the spaxiom_site_plugins package for auto-loading)
    importlib.import_module("co2_plugin")
    
    # Get the registry to access the CO2 sensors
    registry = SensorRegistry()
    
    try:
        # Get the CO2 sensors
        living_room_co2 = registry.get("living_room_co2")
        bedroom_co2 = registry.get("bedroom_co2")
        
        print(f"\nDetected CO2 sensors:")
        print(f"  - {living_room_co2}")
        print(f"  - {bedroom_co2}")
        
        # Define CO2 level conditions
        living_room_high = Condition(lambda: living_room_co2.read() > 800)
        bedroom_high = Condition(lambda: bedroom_co2.read() > 800)
        
        # Define sustained conditions
        sustained_high_living = within(10.0, living_room_high)
        sustained_high_bedroom = within(10.0, bedroom_high)
        
        # Define a condition for when both rooms have high CO2
        all_rooms_high = living_room_high & bedroom_high
        
        # Register event handlers
        @on(living_room_high)
        def on_living_room_high():
            value = living_room_co2.read()
            print(f"[Alert] Living room CO2 level high: {value:.0f} ppm")
        
        @on(bedroom_high)
        def on_bedroom_high():
            value = bedroom_co2.read()
            print(f"[Alert] Bedroom CO2 level high: {value:.0f} ppm")
        
        @on(all_rooms_high)
        def on_all_rooms_high():
            living = living_room_co2.read()
            bed = bedroom_co2.read()
            print(f"[Alert] All rooms have high CO2 levels! Living: {living:.0f} ppm, Bedroom: {bed:.0f} ppm")
            print(f"        You should open some windows for ventilation!")
        
        @on(sustained_high_living)
        def on_sustained_living_room_high():
            value = living_room_co2.read()
            print(f"[Warning] Living room CO2 has been high ({value:.0f} ppm) for over 10 seconds!")
        
        print("\nCO2 monitoring active. Press Ctrl+C to exit...\n")
        
        # Start the Spaxiom runtime - this will automatically poll the sensors
        # and trigger the event handlers when conditions are met
        start_blocking(poll_ms=500)
        
    except KeyError as e:
        print(f"\nError: Could not find CO2 sensor: {e}")
        print("Make sure the plugin was properly loaded.")

if __name__ == "__main__":
    main()
```

### Running the CO2 Monitoring Example

Run the example with:

```bash
python co2_monitor.py
```

You'll see output similar to this:

```
CO2 Monitoring with Spaxiom
===========================
[Plugin] Registering CO2Sensor plugin
[Plugin] CO2Sensor plugin registered with 2 sensors

Detected CO2 sensors:
  - CO2Sensor(name='living_room_co2', location=(1.0, 2.0, 0.0), baseline=450.0ppm)
  - CO2Sensor(name='bedroom_co2', location=(5.0, 3.0, 0.0), baseline=420.0ppm)

CO2 monitoring active. Press Ctrl+C to exit...

[Spaxiom] Runtime started with 2 sensor polling tasks
[Spaxiom] Press Ctrl+C to stop
[Alert] Living room CO2 level high: 803 ppm
[Alert] Bedroom CO2 level high: 832 ppm
[Alert] All rooms have high CO2 levels! Living: 803 ppm, Bedroom: 832 ppm
        You should open some windows for ventilation!
[Warning] Living room CO2 has been high (875 ppm) for over 10 seconds!
^C
[Spaxiom] Shutdown initiated, cancelling tasks...
[Spaxiom] Shutdown complete.
```

This demonstrates how Spaxiom's plugin system allows you to extend the DSL with custom sensors and functionality. 