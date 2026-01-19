"""spaxiom version - Show version information."""

import click
import platform

from spaxiom.cli.console import console


@click.command("version")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed version info")
@click.pass_context
def version_cmd(ctx, verbose):
    """Show Spaxiom version information."""
    from spaxiom import __version__

    if ctx.obj.get("json"):
        import json

        info = {
            "spaxiom": __version__,
            "python": platform.python_version(),
            "platform": platform.platform(),
        }
        click.echo(json.dumps(info, indent=2))
        return

    if verbose:
        console.print(f"[accent]spaxiom[/accent] {__version__}")
        console.print(f"Python {platform.python_version()}", style="muted")
        console.print(f"{platform.platform()}", style="muted")

        # Check for optional dependencies
        console.print()
        console.print("Optional dependencies:", style="muted")

        deps = [
            ("fastapi", "API server"),
            ("uvicorn", "ASGI server"),
            ("rich", "CLI formatting"),
            ("simple_term_menu", "Interactive menus"),
            ("prompt_toolkit", "Shell REPL"),
        ]

        for pkg, desc in deps:
            try:
                mod = __import__(pkg)
                ver = getattr(mod, "__version__", "installed")
                console.print(f"  ✓ {pkg} ({ver}) - {desc}", style="success")
            except ImportError:
                console.print(f"  ○ {pkg} - {desc}", style="muted")
    else:
        console.print(f"spaxiom {__version__}")
