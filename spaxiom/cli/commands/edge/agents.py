"""spaxiom edge agents - Agent management commands."""

import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

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


def _parse_timespec(value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    text = value.strip()
    if not text:
        return None

    suffix = text[-1].lower()
    if suffix in {"s", "m", "h", "d"}:
        try:
            amount = float(text[:-1])
        except ValueError:
            return text

        seconds = amount
        if suffix == "m":
            seconds *= 60
        elif suffix == "h":
            seconds *= 3600
        elif suffix == "d":
            seconds *= 86400

        since = datetime.utcnow() - timedelta(seconds=seconds)
        return since.isoformat()

    return text


def _read_settings(host: str, port: int) -> Dict[str, Any]:
    result = api_request("GET", "/api/system/settings", host, port)
    if "error" in result:
        return {"error": result["error"]}
    return result if isinstance(result, dict) else {}


def _write_settings(host: str, port: int, settings: Dict[str, Any]) -> Dict[str, Any]:
    return api_request(
        "PUT", "/api/system/settings", host, port, {"settings": settings}
    )


def _extract_pattern_event(event_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if event_record.get("event_type") != "pattern_event":
        return None
    data = event_record.get("data") or {}
    if isinstance(data, dict) and "event" in data:
        return data.get("event")
    if isinstance(data, dict):
        return data
    return None


def _action_recommendations(events: List[Dict[str, Any]]) -> List[str]:
    recommendations = []

    for event in events:
        event_type = event.get("event_type")
        if not event_type:
            continue

        if event_type == "PressureBreach":
            recommendations.append("Check door seals and pressure control.")
        elif event_type == "ParticleExcursion":
            recommendations.append("Inspect filtration and pause sensitive work.")
        elif event_type == "AirlockViolation":
            recommendations.append("Review airlock protocol and training.")
        elif event_type == "HighRiskMovement":
            recommendations.append("Limit occupancy until CRI stabilizes.")
        elif event_type == "ServiceNeeded":
            reason = event.get("reason")
            if reason == "low_towels":
                recommendations.append("Restock towels in the facility.")
            elif reason == "bin_full":
                recommendations.append("Empty waste bin.")
            elif reason == "gas_high":
                recommendations.append("Ventilate area and inspect ventilation.")
            elif reason == "spill":
                recommendations.append("Dispatch cleaning crew for spill.")

    return sorted(set(recommendations))


def _summarize_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    pattern_events: List[Dict[str, Any]] = []

    for record in events:
        event_type = record.get("event_type", "unknown")
        counts[event_type] = counts.get(event_type, 0) + 1

        pattern_event = _extract_pattern_event(record)
        if pattern_event:
            pattern_events.append(pattern_event)

    pattern_counts: Dict[str, int] = {}
    for event in pattern_events:
        event_type = event.get("event_type", "unknown")
        pattern_counts[event_type] = pattern_counts.get(event_type, 0) + 1

    return {
        "total_events": len(events),
        "event_counts": counts,
        "pattern_event_counts": pattern_counts,
        "actions": _action_recommendations(pattern_events),
    }


def _format_summary(summary: Dict[str, Any], fmt: str) -> str:
    if fmt == "json":
        return json.dumps(summary, indent=2)

    lines = ["Agent Summary", ""]
    lines.append(f"Total events: {summary.get('total_events', 0)}")
    lines.append("\nEvent counts:")
    for key, value in summary.get("event_counts", {}).items():
        lines.append(f"- {key}: {value}")

    pattern_counts = summary.get("pattern_event_counts", {})
    if pattern_counts:
        lines.append("\nPattern event counts:")
        for key, value in pattern_counts.items():
            lines.append(f"- {key}: {value}")

    actions = summary.get("actions", [])
    lines.append("\nRecommended actions:")
    if actions:
        lines.extend([f"- {action}" for action in actions])
    else:
        lines.append("- (none)")

    return "\n".join(lines)


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


@agents.group("schedule")
@click.pass_context
def schedule_group(ctx):
    """Manage agent summary schedules."""
    pass


@schedule_group.command("list")
@click.pass_context
def list_schedules(ctx):
    """List configured summary schedules."""
    host = ctx.obj["host"]
    port = ctx.obj["port"]

    settings = _read_settings(host, port)
    if "error" in settings:
        print_error(settings["error"])
        return

    schedules = settings.get("agent_summary_schedules", [])
    if ctx.obj.get("json"):
        click.echo(json.dumps(schedules, indent=2))
        return

    if not schedules:
        console.print("No schedules configured.", style="muted")
        return

    for schedule in schedules:
        console.print(
            f"- {schedule.get('name', schedule.get('id', 'schedule'))}: "
            f"cadence={schedule.get('cadence')} format={schedule.get('format')} "
            f"agent={schedule.get('agent_id', 'all')} out={schedule.get('output', 'stdout')}"
        )


@schedule_group.command("set")
@click.option("--name", required=True, help="Schedule name")
@click.option("--agent-id", help="Agent ID to scope summary")
@click.option("--cadence", default="24h", help="Cadence (e.g., 2h, 1d)")
@click.option(
    "--format",
    "format_",
    type=click.Choice(["json", "md", "text"], case_sensitive=False),
    default="md",
    show_default=True,
)
@click.option("--output", default="stdout", help="Output target (stdout or file path)")
@click.pass_context
def set_schedule(ctx, name, agent_id, cadence, format_, output):
    """Create or update a summary schedule."""
    host = ctx.obj["host"]
    port = ctx.obj["port"]

    settings = _read_settings(host, port)
    if "error" in settings:
        print_error(settings["error"])
        return

    schedules = settings.get("agent_summary_schedules", [])
    updated = False
    for schedule in schedules:
        if schedule.get("name") == name:
            schedule.update(
                {
                    "agent_id": agent_id,
                    "cadence": cadence,
                    "format": format_,
                    "output": output,
                }
            )
            updated = True

    if not updated:
        schedules.append(
            {
                "name": name,
                "agent_id": agent_id,
                "cadence": cadence,
                "format": format_,
                "output": output,
                "created_at": datetime.utcnow().isoformat(),
            }
        )

    result = _write_settings(host, port, {"agent_summary_schedules": schedules})
    if "error" in result:
        print_error(result["error"])
        return

    print_success(f"Schedule {'updated' if updated else 'created'}: {name}")


@schedule_group.command("remove")
@click.option("--name", required=True, help="Schedule name to remove")
@click.pass_context
def remove_schedule(ctx, name):
    """Remove a summary schedule by name."""
    host = ctx.obj["host"]
    port = ctx.obj["port"]

    settings = _read_settings(host, port)
    if "error" in settings:
        print_error(settings["error"])
        return

    schedules = settings.get("agent_summary_schedules", [])
    filtered = [schedule for schedule in schedules if schedule.get("name") != name]

    if len(filtered) == len(schedules):
        print_warning(f"No schedule named '{name}' found")
        return

    result = _write_settings(host, port, {"agent_summary_schedules": filtered})
    if "error" in result:
        print_error(result["error"])
        return

    print_success(f"Schedule removed: {name}")


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


@agents.command("summary")
@click.option("--agent-id", help="Filter by agent ID")
@click.option("--since", default="24h", help="Time window start (e.g., 2h, 1d, ISO)")
@click.option("--until", help="Time window end (ISO timestamp)")
@click.option("--limit", default=500, show_default=True)
@click.option(
    "--format",
    "format_",
    type=click.Choice(["json", "md", "text"], case_sensitive=False),
    default="md",
    show_default=True,
)
@click.option("--out", "out_path", type=click.Path(dir_okay=False))
@click.pass_context
def agent_summary(ctx, agent_id, since, until, limit, format_, out_path):
    """Summarize recent agent events and recommended actions."""
    host = ctx.obj["host"]
    port = ctx.obj["port"]

    query_parts = [f"limit={int(limit)}"]
    since_value = _parse_timespec(since)
    until_value = _parse_timespec(until)
    if since_value:
        query_parts.append(f"since={since_value}")
    if until_value:
        query_parts.append(f"until={until_value}")
    if agent_id:
        query_parts.append(f"source={agent_id}")

    query = "&".join(query_parts)
    result = api_request("GET", f"/api/events?{query}", host, port)

    if "error" in result:
        print_error(result["error"])
        return

    events = result if isinstance(result, list) else result.get("events", [])
    summary = _summarize_events(events)
    output = _format_summary(summary, "json" if format_ == "json" else "md")

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(output)
        print_success(f"Summary written to {out_path}")
        return

    click.echo(output)


@agents.command("preview")
@click.option("--agent-id", required=True, help="Agent ID to preview actions for")
@click.option("--window", default="2h", help="Lookback window (e.g., 2h, 1d)")
@click.pass_context
def agent_preview(ctx, agent_id, window):
    """Preview recommended actions based on recent events."""
    host = ctx.obj["host"]
    port = ctx.obj["port"]

    since_value = _parse_timespec(window)
    query = f"source={agent_id}"
    if since_value:
        query = f"{query}&since={since_value}"

    result = api_request("GET", f"/api/events?{query}", host, port)
    if "error" in result:
        print_error(result["error"])
        return

    events = result if isinstance(result, list) else result.get("events", [])
    summary = _summarize_events(events)

    if ctx.obj.get("json"):
        click.echo(json.dumps({"actions": summary["actions"]}, indent=2))
        return

    console.print("Recommended actions:")
    actions = summary.get("actions", [])
    if not actions:
        console.print("- (none)", style="muted")
    else:
        for action in actions:
            console.print(f"- {action}")


@agents.command("playback")
@click.argument("scenario_path", type=click.Path(exists=True, readable=True))
@click.option(
    "--format",
    "format_",
    type=click.Choice(["json", "md", "text"], case_sensitive=False),
    default="md",
    show_default=True,
)
@click.pass_context
def agent_playback(ctx, scenario_path, format_):
    """Replay a scenario file and summarize actions."""
    with open(scenario_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    events = payload.get("events") if isinstance(payload, dict) else payload
    if not isinstance(events, list):
        print_error("Scenario file must be a list of events or {" "'events': [...]}.")
        return

    normalized = []
    for event in events:
        if isinstance(event, dict) and "event_type" in event:
            normalized.append({"event_type": "pattern_event", "data": event})

    summary = _summarize_events(normalized)
    output = _format_summary(summary, "json" if format_ == "json" else "md")
    click.echo(output)


@agents.command("feed")
@click.option("--agent-id", help="Filter by agent ID")
@click.option("--event-type", help="Filter by event type")
@click.pass_context
def agent_feed(ctx, agent_id, event_type):
    """Stream live agent events from the edge server."""
    host = ctx.obj["host"]
    port = ctx.obj["port"]
    url = f"http://{host}:{port}/api/events/stream"

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            for raw in response:
                line = raw.decode("utf-8").strip()
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                try:
                    event = json.loads(payload)
                except json.JSONDecodeError:
                    continue

                if agent_id and event.get("agent_id") != agent_id:
                    continue
                if event_type and event.get("type") != event_type:
                    continue

                if ctx.obj.get("json"):
                    click.echo(json.dumps(event))
                else:
                    console.print(
                        f"[{event.get('timestamp', '')}] {event.get('type', 'event')} "
                        f"agent={event.get('agent_id', '-')}",
                        style="info",
                    )
    except urllib.error.URLError as e:
        print_error(f"Cannot connect: {e.reason}")
    except KeyboardInterrupt:
        pass


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
