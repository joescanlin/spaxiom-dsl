"""
ASCII art banner for Spaxiom CLI.

Provides branded startup banners in different styles.
"""

from rich.console import Console
from rich.panel import Panel

# Simple box-drawing banner (works in all terminals)
BANNER = """[accent]
   ┌─┐┌─┐┌─┐─┐ ┬┬┌─┐┌┬┐
   └─┐├─┘├─┤┌┴┬┘││ ││││
   └─┘┴  ┴ ┴┴ └─┴└─┘┴ ┴
[/accent]"""

# Minimal one-line banner
BANNER_MINIMAL = "[accent]spaxiom[/accent]"

# Full block-style banner (for terminals with good Unicode support)
BANNER_FULL = """[accent]
███████╗██████╗  █████╗ ██╗  ██╗██╗ ██████╗ ███╗   ███╗
██╔════╝██╔══██╗██╔══██╗╚██╗██╔╝██║██╔═══██╗████╗ ████║
███████╗██████╔╝███████║ ╚███╔╝ ██║██║   ██║██╔████╔██║
╚════██║██╔═══╝ ██╔══██║ ██╔██╗ ██║██║   ██║██║╚██╔╝██║
███████║██║     ██║  ██║██╔╝ ██╗██║╚██████╔╝██║ ╚═╝ ██║
╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝     ╚═╝
[/accent]"""


def print_banner(
    console: Console,
    version: str,
    subtitle: str = "Edge Runtime",
    style: str = "default",
) -> None:
    """Print the Spaxiom banner.

    Args:
        console: Rich console instance
        version: Version string to display
        subtitle: Subtitle text (default: "Edge Runtime")
        style: Banner style - "default", "minimal", "full", or "box"
    """
    if style == "minimal":
        console.print(f"{BANNER_MINIMAL} {subtitle} v{version}", style="muted")
        console.print()
    elif style == "full":
        console.print(BANNER_FULL)
        console.print(f"   {subtitle} v{version}", style="muted")
        console.print()
    elif style == "box":
        content = f"[accent]spaxiom[/accent] {subtitle}\nv{version}"
        panel = Panel(
            content,
            border_style="dim",
            padding=(0, 2),
        )
        console.print(panel)
        console.print()
    else:  # default
        console.print(BANNER)
        console.print(f"   {subtitle} v{version}", style="muted")
        console.print()


def print_startup_complete(
    console: Console,
    host: str = "0.0.0.0",
    port: int = 8080,
    sensors: int = 0,
    agents: int = 0,
) -> None:
    """Print startup completion message.

    Args:
        console: Rich console instance
        host: API server host
        port: API server port
        sensors: Number of loaded sensors
        agents: Number of restored agents
    """
    console.print()
    console.print("✓ Database initialized", style="success")
    if sensors > 0:
        console.print(f"✓ Loaded {sensors} sensors", style="success")
    if agents > 0:
        console.print(f"✓ Restored {agents} agents", style="success")
    console.print(
        f"✓ API server running at [accent]http://{host}:{port}[/accent]",
        style="success",
    )
    console.print()
    console.print("Press [bold]Ctrl+C[/bold] to stop", style="muted")
    console.print()
