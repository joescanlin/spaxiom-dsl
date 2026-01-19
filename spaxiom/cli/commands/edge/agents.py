"""spaxiom edge agents - Agent management commands."""

import json
import urllib.request
import urllib.error

import click

from spaxiom.cli.console import console, print_success, print_error, print_warning

try:
    from rich.table import Table

    HAS_RICH_TABLE = True
except ImportError:
    HAS_RICH_TABLE = False


def api_request(
    method: str, path: str, host: str, port: int, data: dict = None
) -> dict:
    """Make an API request to the edge server."""
    url = f"http://{host}:{port}{path}"

    if data:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
            method=method,
        )
    else:
        req = urllib.request.Request(url, method=method)

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"error": body}
    except urllib.error.URLError as e:
        return {"error": f"Cannot connect: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


@click.group()
@click.option(
    "--host", "-h", default="localhost", help="Edge server host", envvar="SPAXIOM_HOST"
)
@click.option(
    "--port",
    "-p",
    default=8080,
    type=int,
    help="Edge server port",
    envvar="SPAXIOM_PORT",
)
@click.pass_context
def agents(ctx, host, port):
    """Manage deployed agents.

    \b
    Commands for listing, deploying, starting, stopping,
    and removing agents on the edge server.
    """
    ctx.ensure_object(dict)
    ctx.obj["host"] = host
    ctx.obj["port"] = port


@agents.command("list")
@click.option(
    "--status",
    "status_filter",
    type=click.Choice(["all", "running", "stopped"]),
    default="all",
)
@click.pass_context
def list_agents(ctx, status_filter):
    """List all agents.

    \b
    Examples:
        spaxiom edge agents list
        spaxiom edge agents list --status running
    """
    host = ctx.obj["host"]
    port = ctx.obj["port"]

    result = api_request("GET", "/api/agents", host, port)

    if "error" in result:
        print_error(result["error"])
        return

    agents_list = result if isinstance(result, list) else result.get("agents", [])

    # Filter by status
    if status_filter != "all":
        agents_list = [a for a in agents_list if a.get("status") == status_filter]

    # JSON output
    if ctx.obj.get("json"):
        click.echo(json.dumps(agents_list, indent=2))
        return

    if not agents_list:
        console.print("No agents found.", style="muted")
        return

    # Rich table
    if HAS_RICH_TABLE:
        table = Table(title="Agents")
        table.add_column("ID", style="dim", max_width=10)
        table.add_column("Name")
        table.add_column("Pattern")
        table.add_column("Status")
        table.add_column("Ticks", justify="right")
        table.add_column("Events", justify="right")

        for agent in agents_list:
            status = agent.get("status", "unknown")
            status_icon = "●" if status == "running" else "○"
            status_style = "green" if status == "running" else "dim"

            stats = agent.get("stats", {})

            table.add_row(
                agent.get("id", "")[:8],
                agent.get("name", "Unnamed"),
                agent.get("pattern_id", "")[:8] if agent.get("pattern_id") else "-",
                f"[{status_style}]{status_icon} {status}[/]",
                f"{stats.get('tick_count', 0):,}",
                f"{stats.get('events_emitted', 0):,}",
            )

        console.print(table)

        running = sum(1 for a in agents_list if a.get("status") == "running")
        console.print(
            f"\nTotal: {len(agents_list)} agents ({running} running)", style="muted"
        )

    else:
        # Simple text output
        for agent in agents_list:
            status = agent.get("status", "unknown")
            icon = "●" if status == "running" else "○"
            console.print(
                f"{icon} {agent.get('id', '')[:8]} - {agent.get('name', 'Unnamed')} ({status})"
            )


@agents.command("deploy")
@click.argument("pattern_id")
@click.option("--name", "-n", help="Custom name for the agent")
@click.pass_context
def deploy_agent(ctx, pattern_id, name):
    """Deploy a pattern as a new agent.

    \b
    Examples:
        spaxiom edge agents deploy abc123
        spaxiom edge agents deploy abc123 --name "Lobby Monitor"
    """
    host = ctx.obj["host"]
    port = ctx.obj["port"]

    data = {"pattern_id": pattern_id}
    if name:
        data["name"] = name

    with console.status("Deploying agent..."):
        result = api_request("POST", "/api/agents", host, port, data)

    if "error" in result:
        print_error(result["error"])
        return

    if ctx.obj.get("json"):
        click.echo(json.dumps(result, indent=2))
        return

    agent_id = result.get("id", result.get("agent_id", "unknown"))
    print_success(f"Agent deployed: {agent_id[:8]}")


@agents.command("start")
@click.argument("agent_id")
@click.pass_context
def start_agent(ctx, agent_id):
    """Start a stopped agent.

    \b
    Examples:
        spaxiom edge agents start abc123
    """
    host = ctx.obj["host"]
    port = ctx.obj["port"]

    with console.status(f"Starting agent {agent_id[:8]}..."):
        result = api_request("POST", f"/api/agents/{agent_id}/start", host, port)

    if "error" in result:
        print_error(result["error"])
        return

    if ctx.obj.get("json"):
        click.echo(json.dumps(result, indent=2))
        return

    print_success(f"Agent {agent_id[:8]} started")


@agents.command("stop")
@click.argument("agent_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
@click.pass_context
def stop_agent(ctx, agent_id, force):
    """Stop a running agent.

    \b
    Examples:
        spaxiom edge agents stop abc123
        spaxiom edge agents stop abc123 --force
    """
    host = ctx.obj["host"]
    port = ctx.obj["port"]

    if not force:
        if not click.confirm(f"Stop agent {agent_id[:8]}?"):
            console.print("Cancelled.", style="muted")
            return

    with console.status(f"Stopping agent {agent_id[:8]}..."):
        result = api_request("POST", f"/api/agents/{agent_id}/stop", host, port)

    if "error" in result:
        print_error(result["error"])
        return

    if ctx.obj.get("json"):
        click.echo(json.dumps(result, indent=2))
        return

    print_success(f"Agent {agent_id[:8]} stopped")


@agents.command("restart")
@click.argument("agent_id")
@click.pass_context
def restart_agent(ctx, agent_id):
    """Restart an agent.

    \b
    Examples:
        spaxiom edge agents restart abc123
    """
    host = ctx.obj["host"]
    port = ctx.obj["port"]

    with console.status(f"Restarting agent {agent_id[:8]}..."):
        result = api_request("POST", f"/api/agents/{agent_id}/restart", host, port)

    if "error" in result:
        print_error(result["error"])
        return

    if ctx.obj.get("json"):
        click.echo(json.dumps(result, indent=2))
        return

    print_success(f"Agent {agent_id[:8]} restarted")


@agents.command("remove")
@click.argument("agent_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
@click.pass_context
def remove_agent(ctx, agent_id, force):
    """Remove an agent.

    \b
    Examples:
        spaxiom edge agents remove abc123
        spaxiom edge agents remove abc123 --force
    """
    host = ctx.obj["host"]
    port = ctx.obj["port"]

    if not force:
        print_warning("This will permanently remove the agent.")
        if not click.confirm(f"Remove agent {agent_id[:8]}?"):
            console.print("Cancelled.", style="muted")
            return

    with console.status(f"Removing agent {agent_id[:8]}..."):
        result = api_request("DELETE", f"/api/agents/{agent_id}", host, port)

    if "error" in result:
        print_error(result["error"])
        return

    if ctx.obj.get("json"):
        click.echo(json.dumps(result, indent=2))
        return

    print_success(f"Agent {agent_id[:8]} removed")


@agents.command("info")
@click.argument("agent_id")
@click.pass_context
def agent_info(ctx, agent_id):
    """Show detailed agent information.

    \b
    Examples:
        spaxiom edge agents info abc123
    """
    host = ctx.obj["host"]
    port = ctx.obj["port"]

    result = api_request("GET", f"/api/agents/{agent_id}", host, port)

    if "error" in result:
        print_error(result["error"])
        return

    if ctx.obj.get("json"):
        click.echo(json.dumps(result, indent=2))
        return

    # Display agent details
    console.print()
    console.print(f"[bold]Agent: {result.get('name', 'Unnamed')}[/bold]")
    console.print("─" * 40)
    console.print(f"  ID:         {result.get('id', 'unknown')}")
    console.print(f"  Pattern:    {result.get('pattern_id', 'none')}")

    status = result.get("status", "unknown")
    status_style = "green" if status == "running" else "dim"
    console.print(f"  Status:     [{status_style}]{status}[/]")

    console.print(f"  Created:    {result.get('created_at', 'unknown')}")

    # Stats
    stats = result.get("stats", {})
    if stats:
        console.print()
        console.print("[bold]Statistics[/bold]")
        console.print(f"  Ticks:      {stats.get('tick_count', 0):,}")
        console.print(f"  Events:     {stats.get('events_emitted', 0):,}")
        console.print(f"  Avg Tick:   {stats.get('avg_tick_ms', 0):.2f}ms")
        console.print(f"  Errors:     {stats.get('error_count', 0)}")

    console.print()
