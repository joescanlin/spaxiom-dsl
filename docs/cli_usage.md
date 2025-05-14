# Spaxiom CLI Usage Guide

Spaxiom provides a command-line interface (CLI) for easily running Spaxiom DSL scripts. The CLI tool, `spax-run`, allows you to execute scripts that define sensors and event handlers without writing any additional runtime code.

## Installation

The `spax-run` command is automatically installed when you install the Spaxiom package:

```bash
pip install spaxiom
```

## Basic Usage

The basic syntax for the CLI is:

```bash
spax-run run <script_path> [options]
```

### Options

- `--poll-ms`: Polling interval in milliseconds (default: 100)
- `--history-length`: Maximum number of history entries to keep per condition (default: 1000)

## Creating New Scripts

The CLI also provides a convenient command for generating new Spaxiom script scaffolds:

```bash
spax-run new <script_name> [options]
```

### Options

- `--output-dir`: Directory where the scaffold script will be created (default: current directory)
- `--sensors`: Number of sensor placeholders to include (default: 2)
- `--zones`: Number of zone placeholders to include (default: 1)
- `--privacy/--no-privacy`: Include privacy settings for sensors (default: enabled)

### Creating a Demo Script

To create a quick demo application:

```bash
spax-run new demo
```

This will generate a `demo.py` file in the current directory with:
- 2 sensors (one with privacy settings)
- 1 zone
- A sample condition and event handler
- A properly configured main function

You can customize the script with more sensors and zones:

```bash
spax-run new complex_demo --sensors 5 --zones 3
```

Then, run your generated script with:

```bash
spax-run run demo.py
```

## Examples

### Running the Occupancy Demo

The occupancy demo (`examples/occupancy_demo.py`) demonstrates how to create multiple sensor types and define zones for occupancy detection.

To run the demo:

```bash
spax-run run examples/occupancy_demo.py
```

Example output:

```
Importing /path/to/examples/occupancy_demo.py...
Script has a main() function. Executing it directly.

Spaxiom Occupancy Detection Demo
--------------------------------
Zone A: Zone(x1=0, y1=0, x2=10, y2=10)
Zone B: Zone(x1=15, y1=0, x2=25, y2=10)

Setting up sensors in zones A and B...
Sensors initialized:
  OccupancySensor(name=pressure_A, location=(5, 5, 0), sensor_type=pressure)
  OccupancySensor(name=thermal_A, location=(5, 5, 0), sensor_type=thermal)
  OccupancySensor(name=pressure_B, location=(20, 5, 0), sensor_type=pressure)

Starting occupancy monitoring...
The message '** ZONE A OCCUPIED **' will appear when:
  1. Pressure is detected in Zone A
  2. Thermal signature is detected in Zone A
  3. No pressure is detected in Zone B
  4. These conditions remain true for at least 1 second

Press Ctrl+C to exit

Pressure A: ON | Thermal A: ON | Pressure B: off | Occupancy Condition: TRUE
** ZONE A OCCUPIED **
Pressure A: ON | Thermal A: ON | Pressure B: off | Occupancy Condition: TRUE
Pressure A: off | Thermal A: ON | Pressure B: ON | Occupancy Condition: false
Pressure A: ON | Thermal A: ON | Pressure B: off | Occupancy Condition: TRUE
** ZONE A OCCUPIED **
```

### Running the Sequence Demo

The sequence demo demonstrates how to detect a temporal sequence of events:

```bash
spax-run run examples/sequence_demo.py --poll-ms 50
```

Example output:

```
Importing /path/to/examples/sequence_demo.py...
Script has a main() function. Executing it directly.
Detected async main function. Running with asyncio.

Sequence Pattern Example: Door → Person → Door Close
----------------------------------------------------
This example detects the sequence: door open → person present → door close
When the pattern is detected within 10 seconds, it prints 'Entry detected'
Door front_door CLOSED at t=1685432017.81
Person no longer detected by entry_area

Starting runtime and waiting for events...

[Spaxiom] Runtime started with poll interval of 50ms

Simulating sequence: door open → person detected → door closed
Door front_door OPENED at t=1685432018.81
PERSON DETECTED by entry_area at t=1685432020.81
Door front_door CLOSED at t=1685432022.81

Waiting for sequence detection...
Sequence successfully detected!

Demo complete.
```

### Customizing Polling Rate

For more responsive monitoring, you can decrease the polling interval:

```bash
spax-run run examples/occupancy_demo.py --poll-ms 50
```

This will make the runtime check sensor values more frequently (every 50ms instead of the default 100ms).

### Managing History Length

For memory-sensitive applications or when you need to track longer histories:

```bash
spax-run run examples/sequence_demo.py --history-length 2000
```

This increases the maximum number of historical states kept for each condition from the default 1000 to 2000.

## Getting Help

To view available commands and options:

```bash
spax-run --help
```

For help on a specific command:

```bash
spax-run run --help
```

## Advanced Usage

The CLI detects whether your script has a `main()` function:

1. If a `main()` function is present, it will be executed directly.
2. If the `main()` function is asynchronous (an async function), it will be run with `asyncio.run()`.
3. If no `main()` function is found, the Spaxiom runtime will be started automatically to process any registered sensors and event handlers. 