"""spaxiom edge shell - Interactive REPL."""

import json
import os
import urllib.request
import urllib.error

import click

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

from spaxiom.cli.console import console, print_success, print_error

# Available commands
COMMANDS = [
    "help",
    "exit",
    "quit",
    "menu",
    "status",
    "sensors",
    "zones",
    "patterns",
    "agents",
    "list",
    "start",
    "stop",
    "restart",
    "deploy",
    "remove",
]

# Prompt style
PROMPT_STYLE = Style.from_dict(
    {
        "prompt": "#f97316 bold",
    }
)


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


class ShellApp:
    """Interactive shell application."""

    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port

        # Setup history file
        history_file = os.path.expanduser("~/.spaxiom_history")
        self.history = FileHistory(history_file)

        # Setup completer
        self.completer = WordCompleter(COMMANDS, ignore_case=True)

        # Create session
        self.session = PromptSession(
            history=self.history,
            completer=self.completer,
            style=PROMPT_STYLE,
        )

    def api(self, method: str, path: str, data: dict = None) -> dict:
        return api_request(method, path, self.host, self.port, data)

    def run(self):
        """Run the shell loop."""
        console.print("[bold]Spaxiom Edge Shell[/bold]", style="header")
        console.print(
            "Type 'help' for commands, 'menu' for interactive menu, 'exit' to quit.",
            style="muted",
        )
        console.print()

        while True:
            try:
                text = self.session.prompt([("class:prompt", "spaxiom> ")])
                self.handle_command(text.strip())
            except KeyboardInterrupt:
                continue
            except EOFError:
                break

        console.print("\nGoodbye!", style="muted")

    def handle_command(self, cmd: str):
        """Handle a shell command."""
        if not cmd:
            return

        parts = cmd.split()
        command = parts[0].lower()
        args = parts[1:]

        if command in ("exit", "quit"):
            raise EOFError()

        elif command == "help":
            self.show_help()

        elif command == "menu":
            try:
                from spaxiom.cli.commands.edge.menu import MenuApp

                app = MenuApp(host=self.host, port=self.port)
                app.run()
            except ImportError:
                print_error(
                    "Menu requires simple-term-menu: pip install simple-term-menu"
                )

        elif command == "status":
            self.show_status()

        elif command == "sensors":
            self.handle_sensors(args)

        elif command == "agents":
            self.handle_agents(args)

        elif command == "patterns":
            self.handle_patterns(args)

        elif command == "zones":
            self.handle_zones(args)

        else:
            console.print(
                f"Unknown command: {command}. Type 'help' for available commands.",
                style="warning",
            )

    def show_help(self):
        """Show help message."""
        console.print()
        console.print("[bold]Available Commands[/bold]")
        console.print("─" * 40)
        console.print("  help              Show this help message")
        console.print("  menu              Open interactive menu")
        console.print("  status            Show system status")
        console.print()
        console.print("  sensors           List sensors")
        console.print("  zones             List zones")
        console.print("  patterns          List patterns")
        console.print()
        console.print("  agents            List agents")
        console.print("  agents start <id> Start an agent")
        console.print("  agents stop <id>  Stop an agent")
        console.print("  agents restart <id> Restart an agent")
        console.print()
        console.print("  exit, quit        Exit the shell")
        console.print()

    def show_status(self):
        """Show system status."""
        result = self.api("GET", "/api/status")

        if "error" in result:
            print_error(result["error"])
            return

        console.print()
        is_healthy = result.get("running", False)
        health_icon = "[green]●[/]" if is_healthy else "[red]○[/]"
        console.print(
            f"System: {health_icon} {'Healthy' if is_healthy else 'Unhealthy'}"
        )

        sensors = result.get("sensors", {})
        console.print(f"Sensors:  {sensors.get('active', 0)} active")

        agents = result.get("agents", {})
        console.print(
            f"Agents:   {agents.get('running', 0)} running / {agents.get('total', 0)} total"
        )
        console.print()

    def handle_sensors(self, args: list):
        """Handle sensor commands."""
        result = self.api("GET", "/api/sensors")

        if "error" in result:
            print_error(result["error"])
            return

        sensors = result if isinstance(result, list) else result.get("sensors", [])

        console.print()
        if not sensors:
            console.print("No sensors found.", style="muted")
        else:
            for sensor in sensors:
                status = sensor.get("status", "unknown")
                icon = "●" if status == "active" else "○"
                style = "green" if status == "active" else "dim"
                console.print(
                    f"  [{style}]{icon}[/] {sensor.get('name', 'Unnamed')} ({sensor.get('sensor_type', 'unknown')})"
                )
        console.print()

    def handle_agents(self, args: list):
        """Handle agent commands."""
        if not args:
            # List agents
            result = self.api("GET", "/api/agents")

            if "error" in result:
                print_error(result["error"])
                return

            agents_list = (
                result if isinstance(result, list) else result.get("agents", [])
            )

            console.print()
            if not agents_list:
                console.print("No agents found.", style="muted")
            else:
                for agent in agents_list:
                    status = agent.get("status", "unknown")
                    icon = "●" if status == "running" else "○"
                    style = "green" if status == "running" else "dim"
                    stats = agent.get("stats", {})
                    ticks = stats.get("tick_count", 0)
                    console.print(
                        f"  [{style}]{icon}[/] {agent.get('id', '')[:8]} - {agent.get('name', 'Unnamed')} (ticks: {ticks:,})"
                    )
            console.print()
            return

        action = args[0].lower()

        if action == "start" and len(args) > 1:
            agent_id = args[1]
            result = self.api("POST", f"/api/agents/{agent_id}/start")
            if "error" in result:
                print_error(result["error"])
            else:
                print_success(f"Agent {agent_id[:8]} started")

        elif action == "stop" and len(args) > 1:
            agent_id = args[1]
            result = self.api("POST", f"/api/agents/{agent_id}/stop")
            if "error" in result:
                print_error(result["error"])
            else:
                print_success(f"Agent {agent_id[:8]} stopped")

        elif action == "restart" and len(args) > 1:
            agent_id = args[1]
            result = self.api("POST", f"/api/agents/{agent_id}/restart")
            if "error" in result:
                print_error(result["error"])
            else:
                print_success(f"Agent {agent_id[:8]} restarted")

        else:
            console.print(
                "Usage: agents [start|stop|restart] <agent_id>", style="muted"
            )

    def handle_patterns(self, args: list):
        """Handle pattern commands."""
        result = self.api("GET", "/api/patterns")

        if "error" in result:
            print_error(result["error"])
            return

        patterns = result if isinstance(result, list) else result.get("patterns", [])

        console.print()
        if not patterns:
            console.print("No patterns found.", style="muted")
        else:
            for pattern in patterns:
                console.print(
                    f"  {pattern.get('id', '')[:8]} - {pattern.get('name', 'Unnamed')} ({pattern.get('pattern_type', 'unknown')})"
                )
        console.print()

    def handle_zones(self, args: list):
        """Handle zone commands."""
        result = self.api("GET", "/api/zones")

        if "error" in result:
            print_error(result["error"])
            return

        zones = result if isinstance(result, list) else result.get("zones", [])

        console.print()
        if not zones:
            console.print("No zones found.", style="muted")
        else:
            for zone in zones:
                console.print(
                    f"  {zone.get('id', '')[:8]} - {zone.get('name', 'Unnamed')}"
                )
        console.print()


@click.command("shell")
@click.option("--host", "-h", default="localhost", help="Edge server host")
@click.option("--port", "-p", default=8080, type=int, help="Edge server port")
def shell_cmd(host, port):
    """Start an interactive shell for managing Spaxiom Edge.

    \b
    Type commands directly or use 'menu' for the interactive menu.
    Supports command history and tab completion.

    \b
    Examples:
        spaxiom edge shell
        spaxiom edge shell --port 8085
    """
    app = ShellApp(host=host, port=port)
    app.run()
