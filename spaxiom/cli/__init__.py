"""
Spaxiom CLI - Command-line interface for Spaxiom DSL.

Provides a unified CLI with:
- Script execution (run)
- Project scaffolding (new)
- Edge device management (edge)
- Interactive menu and shell
"""

import click

from spaxiom.cli.console import console  # noqa: F401
from spaxiom.cli.commands.run import run_cmd
from spaxiom.cli.commands.new import new_cmd
from spaxiom.cli.commands.version import version_cmd
from spaxiom.cli.commands.edge import edge


@click.group()
@click.option(
    "--quiet", "-q", is_flag=True, help="Suppress banner and non-essential output"
)
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.pass_context
def cli(ctx, quiet, json_output):
    """Spaxiom - Spatial AI Agent Framework.

    \b
    Commands:
      run      Run a Spaxiom script
      new      Create a new project scaffold
      edge     Edge device management
      version  Show version information

    \b
    Examples:
      spaxiom run examples/demo.py
      spaxiom new my_project --sensors 3
      spaxiom edge start --port 8080
      spaxiom edge menu
    """
    ctx.ensure_object(dict)
    ctx.obj["quiet"] = quiet
    ctx.obj["json"] = json_output


cli.add_command(run_cmd, name="run")
cli.add_command(new_cmd, name="new")
cli.add_command(version_cmd, name="version")
cli.add_command(edge, name="edge")


def main():
    """Entry point for the spaxiom CLI."""
    cli()


if __name__ == "__main__":
    main()
