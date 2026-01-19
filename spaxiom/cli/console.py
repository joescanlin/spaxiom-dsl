"""
Rich console setup with Spaxiom theming.

Provides a configured console instance with brand colors
and helper functions for styled output.
"""

from rich.console import Console
from rich.theme import Theme

# Brand colors from logos
SPAXIOM_ORANGE = "#f97316"

# Custom theme with brand colors
SPAXIOM_THEME = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "red bold",
        "success": "green",
        "accent": SPAXIOM_ORANGE,
        "muted": "dim",
        "header": f"bold {SPAXIOM_ORANGE}",
        "highlight": f"bold {SPAXIOM_ORANGE}",
    }
)

# Main console for stdout
console = Console(theme=SPAXIOM_THEME)

# Error console for stderr
err_console = Console(stderr=True, theme=SPAXIOM_THEME)


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"✓ {message}", style="success")


def print_error(message: str) -> None:
    """Print an error message."""
    err_console.print(f"✗ {message}", style="error")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"⚠ {message}", style="warning")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"ℹ {message}", style="info")


def print_header(message: str) -> None:
    """Print a header."""
    console.print(message, style="header")


def print_muted(message: str) -> None:
    """Print muted/dim text."""
    console.print(message, style="muted")
