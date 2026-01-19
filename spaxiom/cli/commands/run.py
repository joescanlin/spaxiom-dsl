"""spaxiom run - Run a Spaxiom script."""

import os
import sys
import asyncio
import inspect
import importlib.util
import logging

import click

from spaxiom.cli.console import console, print_success, print_error, print_info
from spaxiom.runtime import start_blocking
from spaxiom.config import load_sensors_from_yaml


@click.command("run")
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
    "-c",
    type=click.Path(exists=True, readable=True, dir_okay=False),
    help="YAML configuration file for sensors and zones",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging for detailed runtime information",
)
@click.pass_context
def run_cmd(
    ctx,
    script_path: str,
    poll_ms: int,
    history_length: int,
    config: str = None,
    verbose: bool = False,
):
    """Run a Spaxiom script.

    \b
    This command imports the specified Python script, which is expected
    to register sensors and event handlers, and then starts the runtime.

    \b
    Examples:
        spaxiom run examples/demo.py
        spaxiom run examples/demo.py --poll-ms 50
        spaxiom run examples/demo.py --config sensors.yaml
    """
    quiet = ctx.obj.get("quiet", False)

    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger("spaxiom")
    logger.setLevel(log_level)

    if verbose and not quiet:
        print_info("Verbose logging enabled")

    script_path = os.path.abspath(script_path)
    script_dir = os.path.dirname(script_path)
    script_name = os.path.basename(script_path)

    if not script_path.endswith(".py"):
        print_error(f"{script_path} is not a Python file.")
        sys.exit(1)

    # Add script directory to sys.path
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    # Load configuration if provided
    if config:
        try:
            if not quiet:
                print_info(f"Loading configuration from {config}...")
            sensors = load_sensors_from_yaml(config)
            if not quiet:
                print_success(f"Loaded {len(sensors)} sensors from configuration.")
        except Exception as e:
            print_error(f"Error loading configuration: {str(e)}")
            sys.exit(1)

    # Import and run the script
    try:
        if not quiet:
            print_info(f"Importing {script_name}...")

        module_name = script_name[:-3]
        spec = importlib.util.spec_from_file_location(module_name, script_path)
        if spec is None or spec.loader is None:
            print_error(f"Could not load spec for {script_path}")
            sys.exit(1)

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Check for main() function
        main_func = getattr(module, "main", None)
        if main_func is not None and callable(main_func):
            if not quiet:
                print_info("Executing main() function...")

            if inspect.iscoroutinefunction(main_func):
                if not quiet:
                    print_info("Running async main()")
                asyncio.run(main_func())
                return

            main_func()
            return

        # Start runtime
        if not quiet:
            print_info(f"Starting runtime with poll interval of {poll_ms}ms...")
        start_blocking(poll_ms=poll_ms, history_length=history_length)

    except KeyboardInterrupt:
        if not quiet:
            console.print("\nStopped by user", style="muted")
    except Exception as e:
        print_error(f"Error running script: {str(e)}")
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)
