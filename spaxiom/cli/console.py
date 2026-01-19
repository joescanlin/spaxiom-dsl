"""
Rich console setup with Spaxiom theming.

Provides a configured console instance with brand colors
and helper functions for styled output.

Falls back to click.echo if rich is not installed.
"""

import sys

# Brand colors from logos
SPAXIOM_ORANGE = "#f97316"

# Try to import rich, fall back to simple output
try:
    from rich.console import Console
    from rich.theme import Theme

    HAS_RICH = True

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

except ImportError:
    HAS_RICH = False

    class SimpleConsole:
        """Fallback console that uses print."""

        def __init__(self, stderr: bool = False):
            self.stderr = stderr

        def print(self, message: str, style: str = None) -> None:
            # Strip rich markup
            import re

            clean = re.sub(r"\[/?[^\]]+\]", "", str(message))
            if self.stderr:
                print(clean, file=sys.stderr)
            else:
                print(clean)

        def status(self, message: str):
            """Context manager that just prints."""
            return SimpleStatus(message)

    class SimpleStatus:
        """Simple status context manager."""

        def __init__(self, message: str):
            self.message = message

        def __enter__(self):
            print(self.message)
            return self

        def __exit__(self, *args):
            pass

    console = SimpleConsole()
    err_console = SimpleConsole(stderr=True)


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
