"""Tests for cleanroom demo seeding."""

import tempfile
from pathlib import Path

from spaxiom.edge.database import (
    AgentRepository,
    EdgeDatabase,
    PatternRepository,
    ZoneRepository,
)
from spaxiom.edge.demos.cleanroom import seed_cleanroom_demo


def test_seed_cleanroom_demo_creates_records() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    db = EdgeDatabase(db_path)
    db.init()

    ids = seed_cleanroom_demo(db)

    zones = ZoneRepository(db)
    patterns = PatternRepository(db)
    agents = AgentRepository(db)

    assert zones.get(ids["zone_id"]) is not None
    assert patterns.get(ids["pattern_id"]) is not None
    assert agents.get(ids["agent_id"]) is not None

    Path(db_path).unlink(missing_ok=True)
