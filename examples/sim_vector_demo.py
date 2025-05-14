#!/usr/bin/env python3
"""
SimVector Demo

This example demonstrates the use of SimVector to efficiently create and update
multiple simulated sensors with sinusoidal patterns.
"""

import time
import logging
from typing import List

# Try to import matplotlib, but make it optional
try:
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from spaxiom import SimVector, Condition

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def plot_demo(sim_vector: SimVector, duration: float = 20.0) -> None:
    """
    Create a real-time plot of sensor values over time.

    Args:
        sim_vector: The vector of simulated sensors
        duration: Duration of the simulation in seconds
    """
    if not HAS_MATPLOTLIB:
        print("Matplotlib is not installed. Cannot create plot.")
        return

    # Initialize data structures for plotting
    time_points: List[float] = []
    sensor_values: List[List[float]] = [[] for _ in range(len(sim_vector))]

    # Create a figure and axis
    fig, ax = plt.subplots(figsize=(10, 6))

    # Initialize lines for each sensor
    lines = []
    for i in range(len(sim_vector)):
        (line,) = ax.plot([], [], label=f"Sensor {i}")
        lines.append(line)

    # Add a legend and labels
    ax.legend(loc="upper right")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Sensor Value")
    ax.set_title("SimVector Sensor Values")
    ax.grid(True)

    # Set axis limits
    ax.set_xlim(0, duration)
    ax.set_ylim(-2, 2)

    # Store the start time
    start_time = time.time()

    # Function to update the plot
    def update(frame):
        # Get current time since start
        current_time = time.time() - start_time
        time_points.append(current_time)

        # Get and store current sensor values
        for i, sensor in enumerate(sim_vector.sensors):
            value = sensor.read()
            sensor_values[i].append(value)

        # Update the lines
        for i, line in enumerate(lines):
            line.set_data(time_points, sensor_values[i])

        # Adjust x-axis if needed
        if current_time > ax.get_xlim()[1]:
            ax.set_xlim(0, current_time + 5)

        # Stop the animation if we've reached the duration
        if current_time >= duration:
            ani.event_source.stop()

        return lines

    # Create the animation
    ani = FuncAnimation(fig, update, frames=None, interval=50, blit=True)

    # Show the plot
    plt.tight_layout()
    plt.show()


def simple_demo(sim_vector: SimVector, duration: float = 30.0) -> None:
    """
    Run a simple demo that periodically prints sensor values.

    Args:
        sim_vector: The vector of simulated sensors
        duration: Duration of the simulation in seconds
    """
    # Define conditions to check
    high_condition = Condition(lambda: sim_vector[0].read() > 0.8)
    low_condition = Condition(lambda: sim_vector[1].read() < -0.5)

    start_time = time.time()
    last_print_time = 0

    print("\nRunning simple demo (no visualization):")
    print("---------------------------------------")
    print("Press Ctrl+C to stop\n")

    try:
        while time.time() - start_time < duration:
            # Print values every second
            current_time = time.time()
            if current_time - last_print_time >= 1.0:
                print(f"Time: {current_time - start_time:.1f}s")

                # Print all sensor values
                values = [sensor.read() for sensor in sim_vector.sensors]
                print(f"Sensor values: {[f'{v:.2f}' for v in values]}")

                # Check conditions
                if high_condition():
                    print(f"HIGH CONDITION: Sensor 0 = {sim_vector[0].read():.2f}")

                if low_condition():
                    print(f"LOW CONDITION: Sensor 1 = {sim_vector[1].read():.2f}")

                print("")
                last_print_time = current_time

            # Small delay to prevent CPU hogging
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nDemo stopped by user")


def main() -> None:
    """Run the SimVector demo."""
    print("\nSimVector Demo")
    print("==============\n")

    # Create a vector of 5 simulated sensors, updating at 10Hz
    sim = SimVector(
        n=5,  # 5 sensors
        hz=10.0,  # Update at 10Hz
        name_prefix="wave",
        frequency_range=(0.1, 1.0),  # Different frequencies for variety
        amplitude_range=(0.8, 1.2),  # Similar but varied amplitudes
        phase_range=(0, 3.14),  # Different phase offsets
    )

    # Start the simulation
    sim.start()

    try:
        # If matplotlib is available, show a real-time plot
        if HAS_MATPLOTLIB:
            plot_demo(sim, duration=30.0)
        else:
            print("Matplotlib not available. Running without visualization.")
            # Run a simple text-based demo instead
            simple_demo(sim, duration=30.0)

    except KeyboardInterrupt:
        print("\nDemo stopped by user")
    finally:
        # Stop the simulation
        sim.stop()
        print("SimVector stopped")


if __name__ == "__main__":
    main()
