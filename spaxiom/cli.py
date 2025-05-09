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

from spaxiom.runtime import start_blocking


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
def run_script(script_path: str, poll_ms: int, history_length: int):
    """
    Run a Spaxiom script.

    This command imports the specified Python script, which is expected to register
    sensors and event handlers, and then starts the Spaxiom runtime.

    Example:
        spax-run examples/sequence_demo.py --poll-ms 50
    """
    script_path = os.path.abspath(script_path)
    script_dir = os.path.dirname(script_path)
    script_name = os.path.basename(script_path)

    if not script_path.endswith(".py"):
        click.echo(f"Error: {script_path} is not a Python file.", err=True)
        sys.exit(1)

    # Add script directory to sys.path to allow importing modules
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

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


if __name__ == "__main__":
    cli()
