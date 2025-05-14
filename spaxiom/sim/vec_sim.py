"""
Vector Simulation module for Spaxiom DSL.

This module provides a SimVector class that efficiently generates multiple
virtual sensors with sinusoidal data patterns.
"""

import math
import time
import asyncio
import threading
from typing import List, Tuple, Optional, Dict, Any

import numpy as np

from spaxiom.core import Sensor


class SimSensor(Sensor):
    """
    A sensor that provides simulated sinusoidal data.

    This is a specialized sensor for use with SimVector.
    """

    def __init__(
        self,
        name: str,
        location: Tuple[float, float, float],
        frequency: float = 1.0,
        amplitude: float = 1.0,
        phase: float = 0.0,
        offset: float = 0.0,
        privacy: str = "public",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a simulated sensor.

        Args:
            name: Unique name for the sensor
            location: (x, y, z) coordinates
            frequency: Frequency of the sinusoidal pattern (cycles per second)
            amplitude: Peak amplitude of the sinusoidal wave
            phase: Phase offset in radians
            offset: Vertical offset (baseline value)
            privacy: Privacy level ('public' or 'private')
            metadata: Optional metadata dictionary
        """
        super().__init__(
            name=name,
            sensor_type="sim",
            location=location,
            privacy=privacy,
            sample_period_s=0.0,  # Don't poll individually, SimVector will update
            metadata=metadata,
        )

        self.frequency = frequency
        self.amplitude = amplitude
        self.phase = phase
        self.offset = offset
        self.current_value = offset

    def _read_raw(self) -> float:
        """
        Return the current value without updating it.
        The actual update is done by SimVector.

        Returns:
            The current sensor value
        """
        return self.current_value

    def calculate_value(self, t: float) -> float:
        """
        Calculate the sensor value at a given time.

        Args:
            t: Time in seconds

        Returns:
            Calculated value at time t
        """
        return self.offset + self.amplitude * math.sin(
            2 * math.pi * self.frequency * t + self.phase
        )

    def __repr__(self):
        return f"SimSensor(name='{self.name}', frequency={self.frequency}, amplitude={self.amplitude}, location={self.location})"


class SimVector:
    """
    A vector of simulated sensors that produce sinusoidal data patterns.

    SimVector creates multiple sensors that share a single update task
    for efficiency. All sensors are updated at the same rate.
    """

    def __init__(
        self,
        n: int,
        hz: float,
        name_prefix: str = "sim",
        base_location: Tuple[float, float, float] = (0, 0, 0),
        spacing: float = 1.0,
        frequency_range: Tuple[float, float] = (0.1, 0.5),
        amplitude_range: Tuple[float, float] = (0.5, 1.5),
        phase_range: Tuple[float, float] = (0, 2 * math.pi),
        offset_range: Tuple[float, float] = (-0.5, 0.5),
        privacy: str = "public",
    ):
        """
        Initialize a vector of simulated sensors.

        Args:
            n: Number of sensors to create
            hz: Update frequency in Hz for all sensors
            name_prefix: Prefix for sensor names
            base_location: Base location for the first sensor
            spacing: Spacing between sensors
            frequency_range: Range of random frequencies (min, max)
            amplitude_range: Range of random amplitudes (min, max)
            phase_range: Range of random phases in radians (min, max)
            offset_range: Range of random vertical offsets (min, max)
            privacy: Privacy level for all sensors ('public' or 'private')
        """
        self.n = n
        self.hz = hz
        self.update_period = 1.0 / hz if hz > 0 else 0.1
        self.sensors: List[SimSensor] = []
        self.running = False
        self._update_task = None

        # Create the sensors
        for i in range(n):
            # Generate parameters for this sensor
            freq = np.random.uniform(*frequency_range)
            amp = np.random.uniform(*amplitude_range)
            phase = np.random.uniform(*phase_range)
            offset = np.random.uniform(*offset_range)

            # Calculate position with spacing
            x, y, z = base_location
            pos = (x + i * spacing, y, z)

            # Create the sensor
            sensor = SimSensor(
                name=f"{name_prefix}_{i}",
                location=pos,
                frequency=freq,
                amplitude=amp,
                phase=phase,
                offset=offset,
                privacy=privacy,
            )

            self.sensors.append(sensor)

    def start(self) -> None:
        """
        Start the simulation update task.
        """
        if self.running:
            return

        self.running = True
        self._start_time = time.time()

        # Create and start the update thread
        self._update_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._update_thread.start()

        print(f"Started SimVector with {self.n} sensors at {self.hz}Hz")

    def stop(self) -> None:
        """
        Stop the simulation update task.
        """
        self.running = False
        if self._update_task:
            # The task will be cancelled in the next iteration of the event loop
            pass

    def _run_async_loop(self) -> None:
        """
        Run the asyncio event loop in a dedicated thread.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._update_task = loop.create_task(self._update_sensors())
        try:
            loop.run_until_complete(self._update_task)
        except asyncio.CancelledError:
            pass
        finally:
            loop.close()

    async def _update_sensors(self) -> None:
        """
        Update all sensors at the specified rate.
        """
        try:
            while self.running:
                t = time.time() - self._start_time

                # Update all sensors efficiently in a single loop
                for sensor in self.sensors:
                    sensor.current_value = sensor.calculate_value(t)

                # Wait until next update
                await asyncio.sleep(self.update_period)
        except asyncio.CancelledError:
            print("SimVector update task cancelled")

    def __len__(self) -> int:
        """Return the number of sensors."""
        return len(self.sensors)

    def __getitem__(self, idx: int) -> SimSensor:
        """Access a sensor by index."""
        return self.sensors[idx]

    def __repr__(self) -> str:
        return f"SimVector(n={self.n}, hz={self.hz}, running={self.running})"
