# GPIO Sensor Onboarding (Linux)

Use GPIO sensors when deploying on Raspberry Pi or other Linux SBCs with GPIO headers.

## 1. Install Dependencies

```bash
pip install spaxiom
pip install gpiozero
```

On Raspberry Pi, install one of:

```bash
pip install RPi.GPIO
# or
pip install pigpio
```

## 2. Create a GPIO Sensor in Python

```python
from spaxiom import GPIODigitalSensor, Condition, on

button = GPIODigitalSensor(
    name="button_sensor",
    pin=17,
    pull_up=True,
    active_state=True,
)

pressed = Condition(lambda: button.read())

@on(pressed)
def on_press():
    print("Button pressed")
```

## 3. Run the Runtime

```bash
spax run ./gpio_demo.py --poll-ms 50
```

## 4. YAML Configuration (Optional)

```yaml
sensors:
  - name: gpio_button
    type: gpio_digital
    pin: 17
    location: [0, 0, 0]
    pull_up: true
    active_state: true
```

```bash
spax run ./my_script.py --config sensors.yaml
```

## Troubleshooting

- **ImportError**: `gpiozero` only works on Linux
- **Permission errors**: Run as root or configure GPIO permissions
- **Wrong pin**: Ensure BCM numbering (not board pin numbers)
