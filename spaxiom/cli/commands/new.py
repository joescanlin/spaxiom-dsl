"""spaxiom new - Create a new Spaxiom project scaffold."""

import os

import click

from spaxiom.cli.console import console, print_success, print_info


@click.command("new")
@click.argument("script_name", type=str)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True),
    default=".",
    help="Directory where the scaffold script will be created",
)
@click.option(
    "--sensors",
    "-s",
    type=int,
    default=2,
    help="Number of sensor placeholders to include in the scaffold",
)
@click.option(
    "--zones",
    "-z",
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
@click.pass_context
def new_cmd(
    ctx,
    script_name: str,
    output_dir: str,
    sensors: int,
    zones: int,
    privacy: bool,
):
    """Create a new Spaxiom script scaffold.

    \b
    This command generates a Python script with the basic skeleton
    for a Spaxiom application, including sensors, zones, conditions,
    and a runtime starter.

    \b
    Examples:
        spaxiom new my_app
        spaxiom new my_app --sensors 3 --zones 2
        spaxiom new my_app -o projects/ --no-privacy
    """
    quiet = ctx.obj.get("quiet", False)

    # Ensure .py extension
    if not script_name.endswith(".py"):
        script_name = f"{script_name}.py"

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Full path
    script_path = os.path.join(output_dir, script_name)

    # Check for existing file
    if os.path.exists(script_path):
        if not click.confirm(f"File {script_path} already exists. Overwrite?"):
            console.print("Operation cancelled.", style="muted")
            return

    # Generate scaffold
    base_name = os.path.basename(script_name)[:-3]
    title_text = f"{base_name} - Spaxiom Application"
    underline_length = len(title_text)

    # Generate sensor content
    sensor_content = []
    for i in range(1, sensors + 1):
        if privacy and i % 2 == 0:
            sensor_content.append(
                f"    sensor{i} = RandomSensor(\n"
                f'        name="sensor{i}",\n'
                f"        location=({i*2}, {i}, 0),\n"
                f'        privacy="private",\n'
                f"    )"
            )
        else:
            sensor_content.append(
                f"    sensor{i} = RandomSensor(\n"
                f'        name="sensor{i}",\n'
                f"        location=({i*2}, {i}, 0),\n"
                f"    )"
            )

    # Generate zone content
    zone_content = []
    for i in range(1, zones + 1):
        zone_content.append(
            f"    zone{i} = Zone(\n"
            f"        {i*5}, {i*5}, {i*5+10}, {i*5+10}  # x1, y1, x2, y2\n"
            f"    )"
        )

    condition_content = """
    # Create a condition based on sensor readings
    high_value = Condition(lambda: sensor1.read() > 0.7)
    
    # Create a temporal condition (must be true for 3 seconds)
    sustained_high = within(3.0, high_value)
    
    # Register an event handler
    @on(sustained_high)
    def handle_high_value():
        from spaxiom.runtime import format_sensor_value
        value = sensor1.read()
        formatted = format_sensor_value(sensor1, value)
        print(f"Sensor reading high: {{formatted}}")
"""

    scaffold_content = f'''#!/usr/bin/env python3
"""
{title_text}

Generated scaffold for a Spaxiom application.
"""

import logging

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
    
    from spaxiom import Sensor, Zone, Condition, on, within, SensorRegistry
    from spaxiom import RandomSensor, TogglingSensor
    
    SensorRegistry().clear()
    
    print("\\nSetting up sensors and zones...")
    
    # Sensors
{os.linesep.join(sensor_content)}
    
    # Zones
{os.linesep.join(zone_content)}
    {condition_content}
    
    print("\\nStarting runtime... Press Ctrl+C to exit\\n")
    
    from spaxiom.runtime import start_blocking
    try:
        start_blocking(poll_ms=50)
    except KeyboardInterrupt:
        print("\\nStopped by user")


if __name__ == "__main__":
    main()
'''

    # Write the file
    with open(script_path, "w") as f:
        f.write(scaffold_content)

    if not quiet:
        print_success(f"Created scaffold: {script_path}")
        print_info("Run it with:")
        console.print(f"  spaxiom run {script_path}", style="accent")
