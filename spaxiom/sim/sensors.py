"""
Simulated sensors for demos and testing.
"""

from __future__ import annotations

import random
import time
from typing import Optional, Tuple

from spaxiom.core import Sensor


class SimulatedAnalogSensor(Sensor):
    """Analog sensor that produces bounded numeric values with noise and spikes."""

    def __init__(
        self,
        name: str,
        location: Tuple[float, float, float],
        base: float = 0.0,
        min_value: float = 0.0,
        max_value: float = 1.0,
        noise_std: float = 0.05,
        drift_per_s: float = 0.0,
        spike_probability: float = 0.0,
        spike_delta: float = 0.0,
        spike_duration_s: float = 1.0,
        seed: Optional[int] = None,
        privacy: str = "public",
    ) -> None:
        super().__init__(
            name=name,
            sensor_type="sim_analog",
            location=location,
            privacy=privacy,
            sample_period_s=0.0,
        )
        self._base = float(base)
        self._min_value = float(min_value)
        self._max_value = float(max_value)
        self._noise_std = float(noise_std)
        self._drift_per_s = float(drift_per_s)
        self._spike_probability = float(spike_probability)
        self._spike_delta = float(spike_delta)
        self._spike_duration_s = float(spike_duration_s)
        self._rng = random.Random(seed)
        self._last_time = time.time()
        self._spike_until: Optional[float] = None

    def _read_raw(self) -> float:
        now = time.time()
        dt = max(0.0, now - self._last_time)
        self._last_time = now

        # Drift base
        self._base += self._drift_per_s * dt

        # Spike handling
        if self._spike_probability > 0 and self._rng.random() < self._spike_probability:
            self._spike_until = now + max(0.0, self._spike_duration_s)

        spike_active = self._spike_until is not None and now <= self._spike_until

        noise = self._rng.gauss(0.0, self._noise_std) if self._noise_std > 0 else 0.0
        value = self._base + noise

        if spike_active:
            value += self._spike_delta
        if self._spike_until is not None and now > self._spike_until:
            self._spike_until = None

        # Clamp to bounds
        if value < self._min_value:
            value = self._min_value
        if value > self._max_value:
            value = self._max_value

        return float(value)


class SimulatedBinarySensor(Sensor):
    """Binary sensor that toggles between 0 and 1 with optional dwell times."""

    def __init__(
        self,
        name: str,
        location: Tuple[float, float, float],
        probability_on: float = 0.05,
        min_on_s: float = 1.0,
        min_off_s: float = 1.0,
        seed: Optional[int] = None,
        privacy: str = "public",
    ) -> None:
        super().__init__(
            name=name,
            sensor_type="sim_binary",
            location=location,
            privacy=privacy,
            sample_period_s=0.0,
        )
        self._probability_on = float(probability_on)
        self._min_on_s = float(min_on_s)
        self._min_off_s = float(min_off_s)
        self._rng = random.Random(seed)
        self._state = False
        self._last_change = time.time()

    def _read_raw(self) -> int:
        now = time.time()
        elapsed = now - self._last_change

        if self._state:
            if elapsed >= self._min_on_s and self._rng.random() < 0.1:
                self._state = False
                self._last_change = now
        else:
            if elapsed >= self._min_off_s and self._rng.random() < self._probability_on:
                self._state = True
                self._last_change = now

        return 1 if self._state else 0
