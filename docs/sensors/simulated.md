# Simulated Sensor Onboarding

Spaxiom includes built-in simulated sensors for demos and testing.

## Simulated Analog Sensor

```python
from spaxiom.sim.sensors import SimulatedAnalogSensor
from spaxiom import Condition, on

temp = SimulatedAnalogSensor(
    name="sim_temp",
    location=(0, 0, 0),
    base=22.0,
    min_value=18.0,
    max_value=30.0,
    noise_std=0.2,
    drift_per_s=0.01,
)

high = Condition(lambda: temp.read() > 28.0)

@on(high)
def alert():
    print("Sim temp high")
```

## Simulated Binary Sensor

```python
from spaxiom.sim.sensors import SimulatedBinarySensor

motion = SimulatedBinarySensor(
    name="sim_motion",
    location=(0, 0, 0),
    probability_on=0.2,
    min_on_s=1.0,
    min_off_s=2.0,
)
```

## Run Example

```bash
spax run ./sim_demo.py --poll-ms 200
```
