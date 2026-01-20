"""spaxiom edge demo - Load demo profiles."""

import click

from spaxiom.cli.console import print_success, print_error, print_info


@click.group()
def demo_cmd():
    """Load demo data into the edge database."""
    pass


@demo_cmd.command("cleanroom")
@click.option("--db-path", type=click.Path(), help="Database file path")
def demo_cleanroom(db_path: str | None = None) -> None:
    """Seed the cleanroom demo into the edge database."""
    try:
        from spaxiom.edge import EdgeDatabase
        from spaxiom.edge.demos.cleanroom import seed_cleanroom_demo
    except ImportError as e:
        print_error(f"Edge module not available: {e}")
        raise click.Abort()

    db = EdgeDatabase(db_path or "spaxiom.db")
    db.init()
    ids = seed_cleanroom_demo(db)

    print_success("Cleanroom demo seeded")
    print_info(f"Zone ID: {ids['zone_id']}")
    print_info(f"Pattern ID: {ids['pattern_id']}")
    print_info(f"Agent ID: {ids['agent_id']}")
