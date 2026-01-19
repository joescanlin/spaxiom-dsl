"""spaxiom edge start - Start the edge server."""

import click

from spaxiom.cli.console import console, print_success, print_error, print_info
from spaxiom.cli.banner import print_banner

try:
    from rich.progress import Progress, SpinnerColumn, TextColumn

    HAS_RICH_PROGRESS = True
except ImportError:
    HAS_RICH_PROGRESS = False


@click.command("start")
@click.option("--host", "-h", default="0.0.0.0", help="API server host")
@click.option("--port", "-p", default=8080, type=int, help="API server port")
@click.option("--db-path", type=click.Path(), help="Database file path")
@click.option("--log-path", type=click.Path(), help="Log file path")
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Logging level",
)
@click.option("--no-banner", is_flag=True, help="Skip the startup banner")
@click.pass_context
def start_cmd(ctx, host, port, db_path, log_path, log_level, no_banner):
    """Start the Spaxiom Edge server.

    \b
    This starts the edge runtime with:
    - SQLite database for persistence
    - REST API server for management
    - Web UI for monitoring

    \b
    Examples:
        spaxiom edge start
        spaxiom edge start --port 8085
        spaxiom edge start --db-path /data/spaxiom.db
    """
    from spaxiom import __version__

    quiet = ctx.obj.get("quiet", False)

    # Print banner
    if not quiet and not no_banner:
        print_banner(console, __version__)

    # Show startup progress
    if HAS_RICH_PROGRESS and not quiet:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Initializing edge runtime...", total=None)

            # Import here to show progress
            try:
                from spaxiom.edge import SpaxiomEdge
            except ImportError as e:
                print_error(f"Edge module not available: {e}")
                print_info("Install edge dependencies: pip install spaxiom[edge]")
                raise click.Abort()

            progress.update(task, description="Starting server...")

            # Create and run the app
            app = SpaxiomEdge(
                db_path=db_path,
                log_path=log_path,
                log_level=log_level,
                api_host=host,
                api_port=port,
            )

        # Progress done, show success
        print_success("Database initialized")
        print_success(f"API server starting at [accent]http://{host}:{port}[/accent]")
        console.print()
        console.print("Press [bold]Ctrl+C[/bold] to stop", style="muted")
        console.print()

        # Run (blocking)
        try:
            app.run_sync()
        except KeyboardInterrupt:
            console.print("\nShutting down...", style="muted")

    else:
        # Simple startup without progress
        try:
            from spaxiom.edge import SpaxiomEdge
        except ImportError as e:
            print_error(f"Edge module not available: {e}")
            raise click.Abort()

        app = SpaxiomEdge(
            db_path=db_path,
            log_path=log_path,
            log_level=log_level,
            api_host=host,
            api_port=port,
        )

        try:
            app.run_sync()
        except KeyboardInterrupt:
            if not quiet:
                console.print("\nShutting down...", style="muted")
