# Smart Building Example

The Smart Building example demonstrates how to use Spaxiom for building automation and occupancy detection. This example shows:

1. Reading historical sensor data from CSV files
2. Defining spatial zones for different building areas
3. Creating occupancy conditions using pressure and thermal sensors
4. Fusing sensor data with custom weights into a comfort index
5. Logging occupancy events at regular intervals

## Overview

The example sets up two zones (an office area and a meeting room), each with pressure and thermal sensors. It then creates a comfort index by fusing the thermal and pressure data with weights of 60% and 40% respectively. The system detects when a person is present in either zone based on the combined conditions and logs the comfort level.

## Full Example Code

```python
#!/usr/bin/env python3
"""
Smart Building Demo for Spaxiom DSL.

This example demonstrates:
1. Using FileSensors to read historical CSV data (floor pressure and thermal)
2. Defining spatial zones and occupancy conditions
3. Fusing sensors with custom weights to create a comfort index
4. Logging occupancy levels at regular intervals
"""

import os
import sys
import time
import random
import logging
from datetime import datetime

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spaxiom import Zone, Condition, on, within, Sensor
from spaxiom.adaptors.file_sensor import FileSensor
from spaxiom.fusion import WeightedFusion

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("SmartBuilding")

# A simple adaptor that generates mock values if the file doesn't exist
class SmartSensor(Sensor):
    """
    A sensor that either reads from a CSV file if it exists,
    or generates random values within a specified range.
    """
    
    def __init__(
        self,
        name: str,
        sensor_type: str,
        location: tuple,
        file_path: str = None,
        min_value: float = 0.0,
        max_value: float = 1.0,
    ):
        super().__init__(name=name, sensor_type=sensor_type, location=location)
        self.file_path = file_path
        self.min_value = min_value
        self.max_value = max_value
        self.file_sensor = None
        
        # Try to create a file sensor if the path exists
        if file_path and os.path.exists(file_path):
            try:
                # Determine which column to use based on sensor type
                column_name = "pressure" if sensor_type == "pressure" else "temperature"
                self.file_sensor = FileSensor(
                    name=f"file_{name}",
                    file_path=file_path,
                    column_name=column_name,
                    location=location,
                    loop=True,  # Loop through the file data
                )
                print(f"  - Using CSV data from {os.path.basename(file_path)}")
            except Exception as e:
                print(f"  - Error loading file sensor: {e}")
                self.file_sensor = None
        
    def _read_raw(self):
        """Read from file sensor if available, otherwise generate random value"""
        if self.file_sensor:
            value = self.file_sensor._read_raw()
            if value is not None:
                return value
                
        # Generate random value if file sensor not available or returned None
        return self.min_value + random.random() * (self.max_value - self.min_value)

def main():
    """Run the smart building demo with historical sensor data."""
    print("\nSpaxiom Smart Building Demo")
    print("===========================")
    print("This demo demonstrates:")
    print("1. Reading historical sensor data from CSV files")
    print("2. Detecting occupancy in different building zones")
    print("3. Creating a weighted comfort index from thermal and pressure data")
    print("4. Logging occupancy information at regular intervals\n")
    
    # Define zones (in square meters)
    zone_a = Zone(0, 0, 10, 10)  # 10x10m zone (e.g., office area)
    zone_b = Zone(15, 0, 25, 10)  # 10x10m zone (e.g., meeting room)
    
    print(f"Zone A: {zone_a} (Office Area)")
    print(f"Zone B: {zone_b} (Meeting Room)\n")
    
    # Create paths to CSV files (these would contain timestamp + value pairs)
    # Note: These files don't need to exist for the demo - SmartSensor will generate random data
    pressure_a_path = os.path.join(os.path.dirname(__file__), "data/pressure_a.csv")
    thermal_a_path = os.path.join(os.path.dirname(__file__), "data/thermal_a.csv")
    pressure_b_path = os.path.join(os.path.dirname(__file__), "data/pressure_b.csv")
    thermal_b_path = os.path.join(os.path.dirname(__file__), "data/thermal_b.csv")
    
    # Ensure data directory exists
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    
    print("Initializing sensors...")
    
    # Create sensors for each data source
    # If files don't exist, random values will be generated
    pressure_a = SmartSensor(
        name="pressure_A",
        sensor_type="pressure",
        location=(5, 5, 0),  # Center of Zone A
        file_path=pressure_a_path,
        min_value=0.0,  # Random values between 0-1 if file not found
        max_value=1.0,
    )
    
    thermal_a = SmartSensor(
        name="thermal_A",
        sensor_type="thermal",
        location=(5, 5, 0),  # Center of Zone A
        file_path=thermal_a_path,
        min_value=15.0,  # Random temperatures between 15-30°C if file not found
        max_value=30.0,
    )
    
    pressure_b = SmartSensor(
        name="pressure_B",
        sensor_type="pressure",
        location=(20, 5, 0),  # Center of Zone B
        file_path=pressure_b_path,
        min_value=0.0,
        max_value=1.0,
    )
    
    thermal_b = SmartSensor(
        name="thermal_B",
        sensor_type="thermal",
        location=(20, 5, 0),  # Center of Zone B
        file_path=thermal_b_path,
        min_value=15.0,
        max_value=30.0,
    )
    
    print("Sensors initialized:")
    print(f"  {pressure_a}")
    print(f"  {thermal_a}")
    print(f"  {pressure_b}")
    print(f"  {thermal_b}\n")
    
    # Create weighted fusion sensors for comfort index
    # Comfort index is 60% thermal + 40% pressure (normalized)
    comfort_a = WeightedFusion(
        name="comfort_A",
        sensors=[thermal_a, pressure_a],
        weights=[0.6, 0.4],
        location=(5, 5, 0),
    )
    
    comfort_b = WeightedFusion(
        name="comfort_B",
        sensors=[thermal_b, pressure_b],
        weights=[0.6, 0.4],
        location=(20, 5, 0),
    )
    
    print("Fusion sensors created:")
    print(f"  {comfort_a} (60% thermal, 40% pressure)")
    print(f"  {comfort_b} (60% thermal, 40% pressure)\n")
    
    # Define conditions for occupancy detection
    # Person in Zone A = pressure_a > 0.5 AND thermal_a > 22°C
    pressure_a_active = Condition(lambda: pressure_a.read() > 0.5)
    thermal_a_active = Condition(lambda: thermal_a.read() > 22.0)
    person_in_a = pressure_a_active & thermal_a_active
    
    # Person in Zone B = pressure_b > 0.5 AND thermal_b > 22°C
    pressure_b_active = Condition(lambda: pressure_b.read() > 0.5)
    thermal_b_active = Condition(lambda: thermal_b.read() > 22.0)
    person_in_b = pressure_b_active & thermal_b_active
    
    # Sustained presence (for 3 seconds) to avoid false positives
    sustained_presence_a = within(3.0, person_in_a)
    sustained_presence_b = within(3.0, person_in_b)
    
    # Register callbacks for occupancy events
    @on(sustained_presence_a)
    def notify_zone_a_occupied():
        comfort = comfort_a.read()
        logger.info(f"ZONE A OCCUPIED - Comfort Index: {comfort:.2f}")
    
    @on(sustained_presence_b)
    def notify_zone_b_occupied():
        comfort = comfort_b.read()
        logger.info(f"ZONE B OCCUPIED - Comfort Index: {comfort:.2f}")
    
    print("Starting monitoring...")
    print("Press Ctrl+C to exit\n")
    
    # Start the event loop with manual condition checking
    try:
        while True:
            # Read current sensor values
            p_a = pressure_a.read() 
            t_a = thermal_a.read()
            c_a = comfort_a.read()
            
            p_b = pressure_b.read()
            t_b = thermal_b.read()
            c_b = comfort_b.read()
            
            # Current timestamp
            now = datetime.now().strftime("%H:%M:%S")
            
            # Log occupancy level every second
            print(f"[{now}] ZONE A: Pressure: {p_a:.2f}, Temp: {t_a:.1f}°C, Comfort: {c_a:.2f}", end="")
            print(f" | ZONE B: Pressure: {p_b:.2f}, Temp: {t_b:.1f}°C, Comfort: {c_b:.2f}", end="\r")
            
            # Process events
            from spaxiom.events import process_events
            process_events()
            
            # Wait before next update
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        print("\n\nSmart Building Demo stopped by user.")
    
    # Print summary
    print("\nDemo Summary:")
    print("=============")
    print(f"Zone A final readings - Pressure: {pressure_a.read():.2f}, Temperature: {thermal_a.read():.1f}°C")
    print(f"Zone B final readings - Pressure: {pressure_b.read():.2f}, Temperature: {thermal_b.read():.1f}°C")
    print(f"Comfort A: {comfort_a.read():.2f}, Comfort B: {comfort_b.read():.2f}")

if __name__ == "__main__":
    main()
```

## Key Components

### SmartSensor Class

The `SmartSensor` class is a custom sensor implementation that attempts to read data from CSV files if they exist, or falls back to generating random values within a specified range if they don't. This provides flexibility and ensures the example always works.

```python
class SmartSensor(Sensor):
    """
    A sensor that either reads from a CSV file if it exists,
    or generates random values within a specified range.
    """
    # ...implementation...
```

### Spatial Zones

Two distinct zones are defined to represent different areas of the building:

```python
# Define zones (in square meters)
zone_a = Zone(0, 0, 10, 10)  # 10x10m zone (e.g., office area)
zone_b = Zone(15, 0, 25, 10)  # 10x10m zone (e.g., meeting room)
```

### Occupancy Conditions

Occupancy conditions are created by combining pressure and thermal sensor readings:

```python
# Person in Zone A = pressure_a > 0.5 AND thermal_a > 22°C
pressure_a_active = Condition(lambda: pressure_a.read() > 0.5)
thermal_a_active = Condition(lambda: thermal_a.read() > 22.0)
person_in_a = pressure_a_active & thermal_a_active
```

### Sensor Fusion

Sensors are fused with custom weights to create a comfort index:

```python
# Comfort index is 60% thermal + 40% pressure (normalized)
comfort_a = WeightedFusion(
    name="comfort_A",
    sensors=[thermal_a, pressure_a],
    weights=[0.6, 0.4],
    location=(5, 5, 0),
)
```

### Temporal Conditions

Occupancy conditions are sustained for a minimum period to avoid false positives:

```python
# Sustained presence (for 3 seconds) to avoid false positives
sustained_presence_a = within(3.0, person_in_a)
```

### Event Registration

Callbacks are registered to respond to occupancy events:

```python
@on(sustained_presence_a)
def notify_zone_a_occupied():
    comfort = comfort_a.read()
    logger.info(f"ZONE A OCCUPIED - Comfort Index: {comfort:.2f}")
```

## Running the Example

To run this example, use:

```bash
python examples/smart_building.py
```

## Sample CSV Data

The example includes sample CSV data files for the pressure and thermal sensors. Here's an example of the data format:

**pressure_a.csv**:
```csv
timestamp,pressure
2023-11-01 08:00:00,0.1
2023-11-01 08:01:00,0.2
2023-11-01 08:02:00,0.3
# ... more entries ...
```

**thermal_a.csv**:
```csv
timestamp,temperature
2023-11-01 08:00:00,19.5
2023-11-01 08:01:00,20.2
2023-11-01 08:02:00,21.0
# ... more entries ...
```

## Extending the Example

You can extend this example in several ways:

1. Add more sensor types (humidity, light, air quality)
2. Create more complex conditions for different scenarios
3. Implement automated controls based on occupancy (e.g., adjusting HVAC)
4. Add historical data analysis and pattern recognition
5. Connect to real IoT sensors instead of CSV files

This example showcases the flexibility and power of Spaxiom for building automation and IoT applications. 