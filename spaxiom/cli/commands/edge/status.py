"""spaxiom edge status - Show system status."""

import json

import click

from spaxiom.cli.console import console, print_error

try:
    from rich.table import Table

    HAS_RICH_TABLE = True
except ImportError:
    HAS_RICH_TABLE = False


def fetch_status(host: str = "localhost", port: int = 8080) -> dict:
    """Fetch status from the edge API."""
    import urllib.request
    import urllib.error

    try:
        url = f"http://{host}:{port}/api/status"
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode())
    except urllib.error.URLError:
        return {"error": "Cannot connect to edge server", "running": False}
    except Exception as e:
        return {"error": str(e), "running": False}


def format_uptime(seconds: float) -> str:
    """Format uptime in human-readable form."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


@click.command("status")
@click.option("--host", "-h", default="localhost", help="Edge server host")
@click.option("--port", "-p", default=8080, type=int, help="Edge server port")
@click.pass_context
def status_cmd(ctx, host, port):
    """Show Spaxiom Edge system status.

    \b
    Displays:
    - Server health and uptime
    - Database status
    - Sensor, zone, pattern, and agent counts

    \b
    Examples:
        spaxiom edge status
        spaxiom edge status --port 8085
        spaxiom --json edge status
    """
    status = fetch_status(host, port)

    # JSON output
    if ctx.obj.get("json"):
        click.echo(json.dumps(status, indent=2))
        return

    # Check for errors
    if "error" in status:
        print_error(status["error"])
        console.print(f"Is the edge server running on {host}:{port}?", style="muted")
        return

    # Rich table output
    if HAS_RICH_TABLE:
        console.print()
        console.print("[bold]Spaxiom Edge Status[/bold]")
        console.print("═" * 40)
        console.print()

        # Health indicator
        is_healthy = status.get("running", False)
        health_icon = "●" if is_healthy else "○"
        health_style = "green" if is_healthy else "red"
        console.print(
            f"System Health: [{health_style}]{health_icon} {'Healthy' if is_healthy else 'Unhealthy'}[/]"
        )
        console.print()

        # System table
        table = Table(show_header=True, header_style="bold")
        table.add_column("Component", style="cyan")
        table.add_column("Status")

        # Database
        db_info = status.get("database", {})
        if db_info.get("healthy"):
            table.add_row(
                "Database", f"[green]●[/] Connected ({status.get('db_path', 'memory')})"
            )
        else:
            table.add_row("Database", "[red]○[/] Disconnected")

        # API
        table.add_row("API Server", f"[green]●[/] Running on :{port}")

        # Uptime
        if "uptime" in status:
            table.add_row("Uptime", format_uptime(status["uptime"]))

        console.print(table)
        console.print()

        # Resources
        console.print("[bold]Resources[/bold]")
        console.print("─" * 40)

        sensors = status.get("sensors", {})
        console.print(
            f"  Sensors:  {sensors.get('active', 0)} active, {sensors.get('total', 0) - sensors.get('active', 0)} disabled"
        )

        zones = status.get("zones", {})
        console.print(f"  Zones:    {zones.get('total', 0)} defined")

        patterns = status.get("patterns", {})
        console.print(f"  Patterns: {patterns.get('total', 0)} configured")

        agents = status.get("agents", {})
        console.print(
            f"  Agents:   {agents.get('running', 0)} running, {agents.get('total', 0) - agents.get('running', 0)} stopped"
        )

        console.print()

    else:
        # Simple text output
        console.print("Spaxiom Edge Status")
        console.print("-" * 40)
        console.print(f"Running: {status.get('running', False)}")
        console.print(f"Database: {status.get('db_path', 'unknown')}")

        sensors = status.get("sensors", {})
        console.print(f"Sensors: {sensors.get('active', 0)} active")

        agents = status.get("agents", {})
        console.print(f"Agents: {agents.get('total', 0)} total")
