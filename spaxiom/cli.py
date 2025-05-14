"""
Command-line interface for Spaxiom DSL.

This module provides a CLI for running Spaxiom scripts and applications.
"""

import os
import sys
import asyncio
import inspect
import importlib.util
import click
import logging

from spaxiom.runtime import start_blocking
from spaxiom.config import load_sensors_from_yaml


@click.group()
def cli():
    """Spaxiom DSL command-line interface."""
    pass


@cli.command("run")
@click.argument("script_path", type=click.Path(exists=True, readable=True))
@click.option(
    "--poll-ms",
    type=int,
    default=100,
    help="Polling interval in milliseconds for the runtime",
)
@click.option(
    "--history-length",
    type=int,
    default=1000,
    help="Maximum number of history entries to keep per condition",
)
@click.option(
    "--config",
    type=click.Path(exists=True, readable=True, dir_okay=False),
    help="YAML configuration file for sensors and zones",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable verbose logging for detailed runtime information",
)
def run_script(
    script_path: str,
    poll_ms: int,
    history_length: int,
    config: str = None,
    verbose: bool = False,
):
    """
    Run a Spaxiom script.

    This command imports the specified Python script, which is expected to register
    sensors and event handlers, and then starts the Spaxiom runtime.

    If a configuration file is provided via --config, sensors and zones defined
    in the YAML file will be instantiated before running the script.

    Example:
        spax-run examples/sequence_demo.py --poll-ms 50
        spax-run examples/sequence_demo.py --config sensors.yaml
    """
    # Configure logging based on verbose flag
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Get the spaxiom logger
    logger = logging.getLogger("spaxiom")
    logger.setLevel(log_level)

    if verbose:
        click.echo("Verbose logging enabled")

    script_path = os.path.abspath(script_path)
    script_dir = os.path.dirname(script_path)
    script_name = os.path.basename(script_path)

    if not script_path.endswith(".py"):
        click.echo(f"Error: {script_path} is not a Python file.", err=True)
        sys.exit(1)

    # Add script directory to sys.path to allow importing modules
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    # Load configuration if provided
    if config:
        try:
            click.echo(f"Loading configuration from {config}...")
            sensors = load_sensors_from_yaml(config)
            click.echo(f"Loaded {len(sensors)} sensors from configuration.")
        except Exception as e:
            click.echo(f"Error loading configuration: {str(e)}", err=True)
            sys.exit(1)

    # Import the script
    try:
        click.echo(f"Importing {script_path}...")
        module_name = script_name[:-3]  # Remove .py extension
        spec = importlib.util.spec_from_file_location(module_name, script_path)
        if spec is None or spec.loader is None:
            click.echo(f"Error: Could not load spec for {script_path}", err=True)
            sys.exit(1)

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Check if the script has a main() function
        main_func = getattr(module, "main", None)
        if main_func is not None and callable(main_func):
            click.echo("Script has a main() function. Executing it directly.")

            # If the main function is async, run it with asyncio
            if inspect.iscoroutinefunction(main_func):
                click.echo("Detected async main function. Running with asyncio.")
                asyncio.run(main_func())
                return

            # Otherwise, call it directly
            main_func()
            return

        # Start the runtime
        click.echo(f"Starting Spaxiom runtime with poll interval of {poll_ms}ms...")
        start_blocking(poll_ms=poll_ms, history_length=history_length)

    except Exception as e:
        click.echo(f"Error running script: {str(e)}", err=True)
        import traceback

        traceback.print_exc()
        sys.exit(1)


@cli.command("new")
@click.argument("script_name", type=str)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True),
    default=".",
    help="Directory where the scaffold script will be created",
)
@click.option(
    "--sensors",
    type=int,
    default=2,
    help="Number of sensor placeholders to include in the scaffold",
)
@click.option(
    "--zones",
    type=int,
    default=1,
    help="Number of zone placeholders to include in the scaffold",
)
@click.option(
    "--privacy/--no-privacy",
    is_flag=True,
    default=True,
    help="Include privacy settings for sensors",
)
def create_scaffold(
    script_name: str, output_dir: str, sensors: int, zones: int, privacy: bool
):
    """
    Create a new Spaxiom script scaffold.

    This command generates a Python script with the basic skeleton needed
    for a Spaxiom application, including sensors, zones, conditions, and
    a runtime starter.

    Example:
        spax new my_smart_home --sensors 3 --zones 2
    """
    # Ensure the script name has a .py extension
    if not script_name.endswith(".py"):
        script_name = f"{script_name}.py"

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Full path for the new script
    script_path = os.path.join(output_dir, script_name)

    # Check if the file already exists
    if os.path.exists(script_path):
        if not click.confirm(f"File {script_path} already exists. Overwrite?"):
            click.echo("Operation cancelled.")
            return

    # Get the base name for display in the script
    base_name = os.path.basename(script_name)[:-3]

    # Calculate the underline length to use in the script header
    title_text = f"{base_name} - Spaxiom Application"
    underline_length = len(title_text)

    # Generate sensor and zone content based on the requested numbers
    sensor_content = []
    for i in range(1, sensors + 1):
        if (
            privacy and i % 2 == 0
        ):  # Make every other sensor private if privacy is enabled
            sensor_content.append(
                f"    sensor{i} = RandomSensor(\n"
                f'        name="sensor{i}",\n'
                f"        location=({i*2}, {i}, 0),\n"
                f'        privacy="private",  # This sensor has privacy restrictions\n'
                f"    )"
            )
        else:
            sensor_content.append(
                f"    sensor{i} = RandomSensor(\n"
                f'        name="sensor{i}",\n'
                f"        location=({i*2}, {i}, 0),\n"
                f"    )"
            )

    zone_content = []
    for i in range(1, zones + 1):
        zone_content.append(
            f"    zone{i} = Zone(\n"
            f"        {i*5}, {i*5}, {i*5+10}, {i*5+10}  # x1, y1, x2, y2\n"
            f"    )"
        )

    # Generate condition and event handler
    condition_content = """
    # Create a condition based on sensor readings
    high_value = Condition(lambda: sensor1.read() > 0.7)
    
    # Create a temporal condition (must be true for 3 seconds)
    sustained_high = within(3.0, high_value)
    
    # Register an event handler
    @on(sustained_high)
    def handle_high_value():
        # If using privacy features, format sensor values appropriately
        from spaxiom.runtime import format_sensor_value
        value = sensor1.read()
        formatted = format_sensor_value(sensor1, value)
        print(f"Sensor reading high: {{formatted}}")
"""

    # Scaffold content with proper templating
    scaffold_content = f'''#!/usr/bin/env python3
"""
{title_text}

Generated scaffold for a Spaxiom application.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    """Run the Spaxiom application."""
    
    print(f"\\n{title_text}")
    print("=" * {underline_length})
    
    # Import Spaxiom components
    from spaxiom import Sensor, Zone, Condition, on, within, SensorRegistry
    from spaxiom import RandomSensor, TogglingSensor
    
    # Clear the registry to start fresh
    SensorRegistry().clear()
    
    print("\\nSetting up sensors and zones...")
    
    # Create sensors
{os.linesep.join(sensor_content)}
    
    # Create zones
{os.linesep.join(zone_content)}
    {condition_content}
    
    print("\\nStarting runtime...")
    print("Press Ctrl+C to exit\\n")
    
    # Start the Spaxiom runtime
    from spaxiom.runtime import start_blocking
    try:
        # Run with a smaller polling interval for better responsiveness
        start_blocking(poll_ms=50)
    except KeyboardInterrupt:
        print("\\nApplication stopped by user")


if __name__ == "__main__":
    main()
'''

    # Write the scaffold to the file
    with open(script_path, "w") as f:
        f.write(scaffold_content)

    click.echo(f"Created scaffold script: {script_path}")
    click.echo("Run it with:")
    click.echo(f"  spax-run {script_path}")


def main():
    """Entry point for the spax-run command."""
    cli()


if __name__ == "__main__":
    main()
