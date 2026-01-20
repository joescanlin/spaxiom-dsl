# File/CSV Sensor Onboarding

Use `FileSensor` to replay historical CSV data as a live sensor stream.

## 1. Prepare a CSV File

Example file `temperature.csv`:

```csv
timestamp,temperature
2024-01-01T00:00:00Z,22.1
2024-01-01T00:00:01Z,22.2
2024-01-01T00:00:02Z,22.4
```

## 2. Create a FileSensor in Python

```python
from spaxiom.adaptors.file_sensor import FileSensor
from spaxiom import Condition, on

temp = FileSensor(
    name="temp_file",
    file_path="./temperature.csv",
    column_name="temperature",
    loop=True,
)

high = Condition(lambda: temp.read() > 28.0)

@on(high)
def on_high():
    print("Temperature exceeded 28°C")
```

## 3. Run the Runtime

```bash
spax run ./file_demo.py --poll-ms 200
```

## Notes

- `column_name` can be a header name or a numeric column index.
- Use `loop=True` to repeat data when the file ends.
- For large files, consider downsampling before replay.
