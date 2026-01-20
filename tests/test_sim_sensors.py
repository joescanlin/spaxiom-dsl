"""Tests for simulated sensors."""

import time

from spaxiom.sim.sensors import SimulatedAnalogSensor, SimulatedBinarySensor


def test_simulated_analog_sensor_clamps_with_spike() -> None:
    sensor = SimulatedAnalogSensor(
        name="sim_analog",
        location=(0.0, 0.0, 0.0),
        base=0.5,
        min_value=0.0,
        max_value=1.0,
        noise_std=0.0,
        spike_probability=1.0,
        spike_delta=2.0,
        spike_duration_s=5.0,
        seed=123,
    )

    value = sensor.read()
    assert value == 1.0


def test_simulated_analog_sensor_applies_drift() -> None:
    sensor = SimulatedAnalogSensor(
        name="sim_analog_drift",
        location=(0.0, 0.0, 0.0),
        base=0.0,
        min_value=-10.0,
        max_value=10.0,
        noise_std=0.0,
        drift_per_s=1.0,
        seed=1,
    )
    sensor._last_time = time.time() - 2.0

    value = sensor.read()
    assert 1.9 <= value <= 2.1


def test_simulated_binary_sensor_turns_on() -> None:
    sensor = SimulatedBinarySensor(
        name="sim_binary",
        location=(0.0, 0.0, 0.0),
        probability_on=1.0,
        min_on_s=0.0,
        min_off_s=0.0,
        seed=5,
    )
    sensor._last_change = time.time() - 5.0

    value = sensor.read()
    assert value == 1
