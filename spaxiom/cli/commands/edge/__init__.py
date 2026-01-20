"""spaxiom edge - Edge device management commands."""

import click

from spaxiom.cli.commands.edge.start import start_cmd
from spaxiom.cli.commands.edge.status import status_cmd
from spaxiom.cli.commands.edge.agents import agents
from spaxiom.cli.commands.edge.demo import demo_cmd


@click.group()
@click.pass_context
def edge(ctx):
    """Edge device management commands.

    \b
    Manage Spaxiom Edge deployments including:
    - Starting/stopping the edge server
    - Managing sensors, zones, patterns, and agents
    - Interactive menu and shell interfaces

    \b
    Examples:
        spaxiom edge start --port 8080
        spaxiom edge status
        spaxiom edge menu
        spaxiom edge agents list
    """
    pass


edge.add_command(start_cmd, name="start")
edge.add_command(status_cmd, name="status")
edge.add_command(agents, name="agents")
edge.add_command(demo_cmd, name="demo")

# Optional commands that require extra dependencies
try:
    from spaxiom.cli.commands.edge.menu import menu_cmd

    edge.add_command(menu_cmd, name="menu")
except ImportError:
    pass

try:
    from spaxiom.cli.commands.edge.shell import shell_cmd

    edge.add_command(shell_cmd, name="shell")
except ImportError:
    pass
