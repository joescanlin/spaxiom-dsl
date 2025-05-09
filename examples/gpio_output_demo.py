#!/usr/bin/env python3
"""
GPIO Output Demo for Spaxiom DSL.

This demonstrates:
1. Checking if we're on a Linux system with gpiozero available
2. Creating a GPIOOutput to control an LED or other digital output
3. Using various control methods like set_high(), set_low(), toggle(), and pulse()
4. Binding GPIO output actions to sensor conditions

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
        from spaxiom import GPIOOutput, GPIODigitalSensor

        GPIOZERO_AVAILABLE = True
    except ImportError:
        print(
            "GPIO support not available. Make sure you're on Linux with gpiozero installed."
        )
else:
    print("GPIO support is only available on Linux platforms.")


def main():
    """Run the GPIO output demo."""
    if not GPIOZERO_AVAILABLE:
        print("\nThis demo requires Linux with gpiozero installed.")
        print("To install gpiozero: pip install gpiozero")
        print(
            "On Raspberry Pi, you'll also need: pip install RPi.GPIO or pip install pigpio"
        )
        return

    print("\nSpaxiom GPIO Output Demo")
    print("=======================")
    print(
        "This demo shows how to use a GPIOOutput to control an LED or other digital output."
    )

    # Define the BCM pin numbers to use
    # For Raspberry Pi: use valid GPIO pin numbers
    led_pin = 17  # GPIO17 for LED
    button_pin = 18  # GPIO18 for button

    try:
        # Create the GPIO output for an LED
        led = GPIOOutput(
            name="status_led",
            pin=led_pin,
            active_high=True,  # LED is on when pin is HIGH
            initial_value=False,  # Start with LED off
        )

        print(f"Created {led}")
        print(f"Controlling LED on BCM pin {led_pin}")

        # Basic LED control demonstration
        print("\nDemonstrating basic LED control:")
        print("  1. Turning LED on")
        led.set_high()
        time.sleep(1)

        print("  2. Turning LED off")
        led.set_low()
        time.sleep(1)

        print("  3. Toggling LED state 3 times")
        for i in range(3):
            led.toggle()
            time.sleep(0.5)
            led.toggle()
            time.sleep(0.5)

        print("  4. Pulsing LED (press Ctrl+C to stop)")
        led.pulse(fade_in_time=0.5, fade_out_time=0.5, n=5, background=False)

        # Create a button sensor if you want to control the LED with a physical button
        try:
            button = GPIODigitalSensor(
                name="control_button",
                pin=button_pin,
                pull_up=True,  # Button connected to ground, use pull-up
                active_state=False,  # Button pressed = LOW
            )

            print(f"\nCreated {button}")
            print(f"Reading button state from BCM pin {button_pin}")

            # Define a condition based on the button state
            button_pressed = Condition(lambda: button.is_active())

            # Register event handlers to control the LED
            @on(button_pressed)
            def on_button_press():
                print("\033[1;32mButton pressed, toggling LED!\033[0m")
                led.toggle()

            # Start monitoring loop
            print("\nPress the button to toggle the LED (press Ctrl+C to exit)...")
            from spaxiom.events import process_events

            try:
                while True:
                    # Process events
                    process_events()
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n\nExiting GPIO output demo.")

        except ImportError:
            # If button sensor isn't available, just demonstrate manual control
            print("\nButton sensor not available, demonstrating manual control:")
            try:
                while True:
                    print("  - Press Enter to toggle LED (or Ctrl+C to exit)")
                    input()
                    led.toggle()
                    print(f"  LED is now {'ON' if led.is_active() else 'OFF'}")
            except KeyboardInterrupt:
                print("\n\nExiting GPIO output demo.")

    except ImportError as e:
        print(f"\nError: {e}")
    except RuntimeError as e:
        print(f"\nError: {e}")
        print(
            "This could be due to permissions, invalid pin number, or missing hardware support."
        )
        print("On Raspberry Pi, make sure you have RPi.GPIO or pigpio installed.")

    # Make sure to clean up on exit
    finally:
        if "led" in locals():
            print("Turning LED off...")
            led.set_low()


if __name__ == "__main__":
    main()
