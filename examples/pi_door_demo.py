#!/usr/bin/env python3
"""
Door Monitoring System Demo for Raspberry Pi using Spaxiom DSL

This example demonstrates:
1. Using GPIODigitalSensor to detect a door switch connected to GPIO pin 17
2. Triggering an action when the door is open for at least 1 second
3. Activating an output (LED/buzzer) on GPIO pin 27 for 3 seconds

Hardware setup:
- Connect a door magnetic switch to BCM pin 17 and GND
  (When door is closed, switch is closed; when door opens, switch opens)
- Connect an LED or buzzer to BCM pin 27 with appropriate resistor

Note: This example will only work on Raspberry Pi or similar Linux systems with gpiozero installed.
"""

import os
import sys
import time
import signal
import threading

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import required Spaxiom components
from spaxiom import Condition, on, within

# Check if we're on Linux and if GPIO support is available
GPIOZERO_AVAILABLE = False
if sys.platform.startswith("linux"):
    try:
        from spaxiom import GPIODigitalSensor, GPIOOutput

        GPIOZERO_AVAILABLE = True
    except ImportError:
        print(
            "GPIO support not available. Make sure you're on Linux with gpiozero installed."
        )
else:
    print("This demo requires a Raspberry Pi or similar Linux system.")
    sys.exit(1)


# Define pin numbers
DOOR_SENSOR_PIN = 17  # BCM pin for door sensor
ALERT_OUTPUT_PIN = 27  # BCM pin for LED/buzzer output


def main():
    """Run the door monitoring system demo."""
    print("\nDoor Monitoring System Demo")
    print("===========================")
    print(
        f"Door sensor on pin {DOOR_SENSOR_PIN}, Alert output on pin {ALERT_OUTPUT_PIN}"
    )

    # Set up graceful exit
    running = True

    def signal_handler(sig, frame):
        nonlocal running
        print("\nShutting down...")
        running = False

    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Initialize the door sensor
        door_sensor = GPIODigitalSensor(
            name="door_switch",
            pin=DOOR_SENSOR_PIN,
            pull_up=True,  # Use internal pull-up resistor
            active_state=False,  # When door is open, switch opens, reading LOW (False)
        )
        print(f"Initialized door sensor on pin {DOOR_SENSOR_PIN}")

        # Initialize the alert output (LED/buzzer)
        alert_output = GPIOOutput(
            name="door_alert",
            pin=ALERT_OUTPUT_PIN,
            active_high=True,  # Output is active HIGH
            initial_value=False,  # Start with output OFF
        )
        print(f"Initialized alert output on pin {ALERT_OUTPUT_PIN}")

        # Define a condition for when the door is open
        door_open = Condition(lambda: not door_sensor.is_active())

        # Create a temporal condition that is true when the door has been open for at least 1 second
        door_open_sustained = within(1.0, door_open)

        # Function to turn off the alert after 3 seconds
        def turn_off_alert_after_delay(seconds=3.0):
            time.sleep(seconds)
            alert_output.set_low()
            print("Alert deactivated")

        # Register the callback for when the door is open for more than 1 second
        @on(door_open_sustained)
        def handle_door_open():
            print("\033[1;31mALERT: Door has been open for more than 1 second!\033[0m")

            # Activate the alert output
            alert_output.set_high()
            print("Alert activated")

            # Set a timer to turn off the alert after 3 seconds
            threading.Thread(
                target=turn_off_alert_after_delay, args=(3.0,), daemon=True
            ).start()

        # Start monitoring
        print("\nMonitoring door state...")
        print("Press Ctrl+C to exit")

        # Import the events module for processing callbacks
        from spaxiom.events import process_events

        # Main loop
        last_state = None
        while running:
            # Get current door state
            current_state = not door_sensor.is_active()

            # Print state changes
            if current_state != last_state:
                if current_state:
                    print("\033[1;33mDoor OPENED\033[0m")
                else:
                    print("\033[1;32mDoor CLOSED\033[0m")
                last_state = current_state

            # Process any events
            process_events()

            # Small delay to prevent CPU hogging
            time.sleep(0.1)

    except Exception as e:
        print(f"Error: {str(e)}")

    finally:
        # Clean up
        if "alert_output" in locals():
            alert_output.set_low()
            print("Alert output turned off")


if __name__ == "__main__":
    main()
