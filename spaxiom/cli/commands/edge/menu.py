"""spaxiom edge menu - Interactive menu interface."""

import json
import urllib.request
import urllib.error

import click

from simple_term_menu import TerminalMenu

from spaxiom.cli.console import console, print_success, print_error, print_warning
from spaxiom.cli.banner import print_banner

try:
    from rich.table import Table

    HAS_RICH_TABLE = True
except ImportError:
    HAS_RICH_TABLE = False


# Menu definitions
MAIN_MENU = [
    "[1] Dashboard        - View system status",
    "[2] Sensors          - Manage sensors",
    "[3] Zones            - Manage zones",
    "[4] Patterns         - Manage patterns",
    "[5] Agents           - Manage agents",
    "[6] Logs             - View recent logs",
    "[q] Exit",
]

AGENT_MENU = [
    "[1] List all agents",
    "[2] Deploy new agent",
    "[3] Start an agent",
    "[4] Stop an agent",
    "[5] Restart an agent",
    "[6] View agent details",
    "[7] Remove an agent",
    "[b] Back to main menu",
]

SENSOR_MENU = [
    "[1] List all sensors",
    "[2] Add new sensor",
    "[3] Test a sensor",
    "[4] Remove a sensor",
    "[b] Back to main menu",
]


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


class MenuApp:
    """Interactive menu application."""

    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port

    def api(self, method: str, path: str, data: dict = None) -> dict:
        return api_request(method, path, self.host, self.port, data)

    def run(self):
        """Run the main menu loop."""
        from spaxiom import __version__

        print_banner(console, __version__)

        while True:
            console.print("\n[bold]Main Menu[/bold]")

            menu = TerminalMenu(
                MAIN_MENU,
                title="Spaxiom Edge",
                menu_cursor="-> ",
                menu_cursor_style=("fg_yellow", "bold"),
                menu_highlight_style=("bg_yellow", "fg_black"),
                cycle_cursor=True,
                clear_screen=False,
            )

            choice = menu.show()

            if choice is None or choice == 6:  # Exit
                console.print("\nGoodbye!", style="muted")
                break
            elif choice == 0:  # Dashboard
                self.show_dashboard()
            elif choice == 1:  # Sensors
                self.sensor_menu()
            elif choice == 2:  # Zones
                self.zone_menu()
            elif choice == 3:  # Patterns
                self.pattern_menu()
            elif choice == 4:  # Agents
                self.agent_menu()
            elif choice == 5:  # Logs
                self.show_logs()

    def show_dashboard(self):
        """Show system dashboard."""
        console.print("\n[bold]Dashboard[/bold]")
        console.print("=" * 40)

        status = self.api("GET", "/api/status")

        if "error" in status:
            print_error(status["error"])
            return

        # Health
        is_healthy = status.get("running", False)
        health_icon = "[green]●[/]" if is_healthy else "[red]○[/]"
        console.print(
            f"\nSystem: {health_icon} {'Healthy' if is_healthy else 'Unhealthy'}"
        )

        # Resources
        sensors = status.get("sensors", {})
        console.print(f"Sensors:  {sensors.get('active', 0)} active")

        zones = status.get("zones", {})
        console.print(f"Zones:    {zones.get('total', 0)} defined")

        patterns = status.get("patterns", {})
        console.print(f"Patterns: {patterns.get('total', 0)} configured")

        agents = status.get("agents", {})
        console.print(
            f"Agents:   {agents.get('running', 0)} running / {agents.get('total', 0)} total"
        )

        console.print("\nPress Enter to continue...", style="muted")
        input()

    def agent_menu(self):
        """Agent management submenu."""
        while True:
            # Get agent count
            result = self.api("GET", "/api/agents")
            agents_list = (
                result if isinstance(result, list) else result.get("agents", [])
            )
            running = sum(1 for a in agents_list if a.get("status") == "running")

            console.print(
                f"\n[bold]Agents[/bold] ({len(agents_list)} total, {running} running)"
            )

            menu = TerminalMenu(
                AGENT_MENU,
                menu_cursor="-> ",
                menu_cursor_style=("fg_yellow", "bold"),
            )

            choice = menu.show()

            if choice is None or choice == 7:  # Back
                break
            elif choice == 0:  # List
                self.list_agents()
            elif choice == 1:  # Deploy
                self.deploy_agent_interactive()
            elif choice == 2:  # Start
                self.start_agent_interactive()
            elif choice == 3:  # Stop
                self.stop_agent_interactive()
            elif choice == 4:  # Restart
                self.restart_agent_interactive()
            elif choice == 5:  # Details
                self.view_agent_interactive()
            elif choice == 6:  # Remove
                self.remove_agent_interactive()

    def list_agents(self):
        """List all agents in a table."""
        result = self.api("GET", "/api/agents")

        if "error" in result:
            print_error(result["error"])
            return

        agents_list = result if isinstance(result, list) else result.get("agents", [])

        if not agents_list:
            console.print("\nNo agents found.", style="muted")
            input("\nPress Enter to continue...")
            return

        console.print()

        if HAS_RICH_TABLE:
            table = Table(title="Agents")
            table.add_column("ID", style="dim", max_width=10)
            table.add_column("Name")
            table.add_column("Status")
            table.add_column("Ticks", justify="right")

            for agent in agents_list:
                status = agent.get("status", "unknown")
                status_style = "green" if status == "running" else "dim"
                stats = agent.get("stats", {})

                table.add_row(
                    agent.get("id", "")[:8],
                    agent.get("name", "Unnamed"),
                    f"[{status_style}]{status}[/]",
                    f"{stats.get('tick_count', 0):,}",
                )

            console.print(table)
        else:
            for agent in agents_list:
                status = agent.get("status", "unknown")
                icon = "●" if status == "running" else "○"
                console.print(
                    f"  {icon} {agent.get('id', '')[:8]} - {agent.get('name', 'Unnamed')}"
                )

        input("\nPress Enter to continue...")

    def deploy_agent_interactive(self):
        """Interactive agent deployment."""
        # Get available patterns
        result = self.api("GET", "/api/patterns")

        if "error" in result:
            print_error(result["error"])
            return

        patterns = result if isinstance(result, list) else result.get("patterns", [])

        if not patterns:
            print_warning("No patterns available. Create a pattern first.")
            input("\nPress Enter to continue...")
            return

        # Pattern selection menu
        pattern_choices = [
            f"{p.get('name', 'Unnamed')} ({p.get('pattern_type', 'unknown')})"
            for p in patterns
        ]
        pattern_choices.append("[b] Cancel")

        console.print("\n[bold]Select a pattern to deploy:[/bold]")

        menu = TerminalMenu(pattern_choices, menu_cursor="-> ")
        choice = menu.show()

        if choice is None or choice == len(patterns):
            return

        selected = patterns[choice]

        # Confirmation
        console.print(
            f"\nDeploy [accent]{selected.get('name', 'pattern')}[/accent] as a new agent?"
        )
        confirm = TerminalMenu(["Yes, deploy", "No, cancel"])

        if confirm.show() == 0:
            with console.status("Deploying agent..."):
                result = self.api("POST", "/api/agents", {"pattern_id": selected["id"]})

            if "error" in result:
                print_error(result["error"])
            else:
                agent_id = result.get("id", result.get("agent_id", "unknown"))
                print_success(f"Agent deployed: {agent_id[:8]}")

            input("\nPress Enter to continue...")

    def select_agent(self, status_filter: str = None) -> dict | None:
        """Show agent selection menu and return selected agent."""
        result = self.api("GET", "/api/agents")

        if "error" in result:
            print_error(result["error"])
            return None

        agents_list = result if isinstance(result, list) else result.get("agents", [])

        if status_filter:
            agents_list = [a for a in agents_list if a.get("status") == status_filter]

        if not agents_list:
            console.print("No matching agents found.", style="muted")
            return None

        choices = [
            f"{a.get('id', '')[:8]} - {a.get('name', 'Unnamed')} ({a.get('status', 'unknown')})"
            for a in agents_list
        ]
        choices.append("[b] Cancel")

        console.print("\n[bold]Select an agent:[/bold]")
        menu = TerminalMenu(choices, menu_cursor="-> ")
        choice = menu.show()

        if choice is None or choice == len(agents_list):
            return None

        return agents_list[choice]

    def start_agent_interactive(self):
        """Start an agent interactively."""
        agent = self.select_agent(status_filter="stopped")
        if not agent:
            return

        with console.status(f"Starting {agent.get('name', 'agent')}..."):
            result = self.api("POST", f"/api/agents/{agent['id']}/start")

        if "error" in result:
            print_error(result["error"])
        else:
            print_success("Agent started")

        input("\nPress Enter to continue...")

    def stop_agent_interactive(self):
        """Stop an agent interactively."""
        agent = self.select_agent(status_filter="running")
        if not agent:
            return

        confirm = TerminalMenu(["Yes, stop", "No, cancel"])
        console.print(f"\nStop [accent]{agent.get('name', 'agent')}[/accent]?")

        if confirm.show() == 0:
            with console.status(f"Stopping {agent.get('name', 'agent')}..."):
                result = self.api("POST", f"/api/agents/{agent['id']}/stop")

            if "error" in result:
                print_error(result["error"])
            else:
                print_success("Agent stopped")

        input("\nPress Enter to continue...")

    def restart_agent_interactive(self):
        """Restart an agent interactively."""
        agent = self.select_agent()
        if not agent:
            return

        with console.status(f"Restarting {agent.get('name', 'agent')}..."):
            result = self.api("POST", f"/api/agents/{agent['id']}/restart")

        if "error" in result:
            print_error(result["error"])
        else:
            print_success("Agent restarted")

        input("\nPress Enter to continue...")

    def view_agent_interactive(self):
        """View agent details interactively."""
        agent = self.select_agent()
        if not agent:
            return

        result = self.api("GET", f"/api/agents/{agent['id']}")

        if "error" in result:
            print_error(result["error"])
            return

        console.print(f"\n[bold]{result.get('name', 'Agent')}[/bold]")
        console.print("─" * 40)
        console.print(f"  ID:      {result.get('id', 'unknown')}")
        console.print(f"  Pattern: {result.get('pattern_id', 'none')}")
        console.print(f"  Status:  {result.get('status', 'unknown')}")

        stats = result.get("stats", {})
        if stats:
            console.print("\n[bold]Stats[/bold]")
            console.print(f"  Ticks:    {stats.get('tick_count', 0):,}")
            console.print(f"  Events:   {stats.get('events_emitted', 0):,}")
            console.print(f"  Avg Tick: {stats.get('avg_tick_ms', 0):.2f}ms")

        input("\nPress Enter to continue...")

    def remove_agent_interactive(self):
        """Remove an agent interactively."""
        agent = self.select_agent()
        if not agent:
            return

        print_warning("This will permanently remove the agent.")
        confirm = TerminalMenu(["Yes, remove", "No, cancel"])
        console.print(f"\nRemove [accent]{agent.get('name', 'agent')}[/accent]?")

        if confirm.show() == 0:
            with console.status(f"Removing {agent.get('name', 'agent')}..."):
                result = self.api("DELETE", f"/api/agents/{agent['id']}")

            if "error" in result:
                print_error(result["error"])
            else:
                print_success("Agent removed")

        input("\nPress Enter to continue...")

    def sensor_menu(self):
        """Sensor management submenu."""
        while True:
            console.print("\n[bold]Sensors[/bold]")

            menu = TerminalMenu(SENSOR_MENU, menu_cursor="-> ")
            choice = menu.show()

            if choice is None or choice == 4:  # Back
                break
            elif choice == 0:  # List
                self.list_sensors()
            elif choice == 1:  # Add
                console.print("Add sensor: Use the web UI or API", style="muted")
                input("\nPress Enter to continue...")
            elif choice == 2:  # Test
                console.print("Test sensor: Use the web UI or API", style="muted")
                input("\nPress Enter to continue...")
            elif choice == 3:  # Remove
                console.print("Remove sensor: Use the web UI or API", style="muted")
                input("\nPress Enter to continue...")

    def list_sensors(self):
        """List all sensors."""
        result = self.api("GET", "/api/sensors")

        if "error" in result:
            print_error(result["error"])
            return

        sensors = result if isinstance(result, list) else result.get("sensors", [])

        if not sensors:
            console.print("\nNo sensors found.", style="muted")
        else:
            console.print()
            for sensor in sensors:
                status = sensor.get("status", "unknown")
                icon = "●" if status == "active" else "○"
                console.print(
                    f"  {icon} {sensor.get('name', 'Unnamed')} ({sensor.get('sensor_type', 'unknown')})"
                )

        input("\nPress Enter to continue...")

    def zone_menu(self):
        """Zone management submenu."""
        console.print("\n[bold]Zones[/bold]")
        console.print(
            "Zone management: Use the web UI for visual editing", style="muted"
        )
        input("\nPress Enter to continue...")

    def pattern_menu(self):
        """Pattern management submenu."""
        console.print("\n[bold]Patterns[/bold]")
        console.print(
            "Pattern management: Use the web UI for visual editing", style="muted"
        )
        input("\nPress Enter to continue...")

    def show_logs(self):
        """Show recent logs."""
        result = self.api("GET", "/api/events?limit=20")

        if "error" in result:
            print_error(result["error"])
            return

        events = result if isinstance(result, list) else result.get("events", [])

        console.print("\n[bold]Recent Events[/bold]")
        console.print("─" * 60)

        if not events:
            console.print("No events found.", style="muted")
        else:
            for event in events[:20]:
                ts = event.get("timestamp", "")[:19]
                etype = event.get("event_type", "unknown")
                console.print(f"  {ts}  {etype}")

        input("\nPress Enter to continue...")


@click.command("menu")
@click.option("--host", "-h", default="localhost", help="Edge server host")
@click.option("--port", "-p", default=8080, type=int, help="Edge server port")
def menu_cmd(host, port):
    """Start interactive menu interface.

    \b
    Navigate with arrow keys, Enter to select, 'q' to quit.

    \b
    Examples:
        spaxiom edge menu
        spaxiom edge menu --port 8085
    """
    app = MenuApp(host=host, port=port)
    app.run()
