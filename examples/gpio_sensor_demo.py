#!/usr/bin/env python3
"""
GPIO Sensor Demo for Spaxiom DSL.

This demonstrates:
1. Checking if we're on a Linux system with gpiozero available
2. Creating a GPIODigitalSensor to read from a GPIO pin
3. Setting up conditions and events based on the GPIO state
4. Reading the sensor value in real-time

Note: This example will only work on Linux systems with gpiozero installed.
For Raspberry Pi, make sure you have RPi.GPIO or pigpio installed.
"""

import os
import sys
import time

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spaxiom import Condition, on

# Check if we're on Linux and if GPIO support is available
GPIOZERO_AVAILABLE = False
if sys.platform.startswith("linux"):
    try:
        from spaxiom import GPIODigitalSensor

        GPIOZERO_AVAILABLE = True
    except ImportError:
        print(
            "GPIODigitalSensor not available. Make sure you're on Linux with gpiozero installed."
        )
else:
    print("GPIO support is only available on Linux platforms.")


def main():
    """Run the GPIO sensor demo."""
    if not GPIOZERO_AVAILABLE:
        print("\nThis demo requires Linux with gpiozero installed.")
        print("To install gpiozero: pip install gpiozero")
        print(
            "On Raspberry Pi, you'll also need: pip install RPi.GPIO or pip install pigpio"
        )
        return

    print("\nSpaxiom GPIO Sensor Demo")
    print("=======================")
    print("This demo shows how to use a GPIODigitalSensor to read from GPIO pins.")

    # Define the BCM pin number to use
    # For Raspberry Pi: use a valid GPIO pin number
    pin = 17  # GPIO17, modify to match your hardware setup

    try:
        # Create the GPIO sensor
        # - Use pull_up=True for a button connected to ground (with internal pull-up resistor)
        # - Use pull_up=False for a button connected to 3.3V (with internal pull-down resistor)
        gpio_sensor = GPIODigitalSensor(
            name="button_sensor",
            pin=pin,
            pull_up=True,  # Use internal pull-up resistor (active low)
            active_state=False,  # Button pressed = active = LOW
            location=(0, 0, 0),
        )

        print(f"Created {gpio_sensor}")
        print(f"Reading from BCM pin {pin}")
        print("Press the button connected to the GPIO pin...")

        # Define a condition based on the GPIO state
        button_pressed = Condition(lambda: gpio_sensor.is_active())

        # Register a callback for when the button is pressed
        @on(button_pressed)
        def on_button_press():
            print("\033[1;32mButton pressed!\033[0m")

        # Process events in a loop
        from spaxiom.events import process_events

        # Start monitoring loop
        try:
            while True:
                # Read the current state
                state = gpio_sensor.read()
                print(f"Button state: {'PRESSED' if state else 'released'}", end="\r")

                # Process events
                process_events()

                # Wait before next read
                time.sleep(0.1)

        except KeyboardInterrupt:
            print("\n\nExiting GPIO demo.")

    except ImportError as e:
        print(f"\nError: {e}")
    except RuntimeError as e:
        print(f"\nError: {e}")
        print(
            "This could be due to permissions, invalid pin number, or missing hardware support."
        )
        print("On Raspberry Pi, make sure you have RPi.GPIO or pigpio installed.")


if __name__ == "__main__":
    main()
