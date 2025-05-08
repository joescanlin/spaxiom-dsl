"""
Tests for the Zone module functionality.
"""

import pytest
import numpy as np
from spaxiom.zone import Point, Zone, distance


def test_point_creation():
    """Test that Point objects can be created and accessed correctly."""
    p = Point(3.5, 4.2)
    assert p.x == 3.5
    assert p.y == 4.2
    
    # Test repr
    assert "Point" in repr(p)
    assert "3.50" in repr(p)
    assert "4.20" in repr(p)


def test_zone_creation():
    """Test Zone creation and reordering of coordinates."""
    # Normal order
    z1 = Zone(1.0, 2.0, 5.0, 6.0)
    assert z1.x1 == 1.0
    assert z1.y1 == 2.0
    assert z1.x2 == 5.0
    assert z1.y2 == 6.0
    
    # Reversed order - should reorder in __post_init__
    z2 = Zone(5.0, 6.0, 1.0, 2.0)
    assert z2.x1 == 1.0
    assert z2.y1 == 2.0
    assert z2.x2 == 5.0
    assert z2.y2 == 6.0
    
    # Test repr
    assert "Zone" in repr(z1)


def test_zone_contains():
    """Test the Zone.contains method with various points."""
    zone = Zone(10.0, 10.0, 20.0, 20.0)
    
    # Points as tuples
    assert zone.contains((15.0, 15.0)) is True  # Center
    assert zone.contains((10.0, 10.0)) is True  # Bottom-left corner
    assert zone.contains((20.0, 20.0)) is True  # Top-right corner
    assert zone.contains((5.0, 15.0)) is False  # Outside left
    assert zone.contains((25.0, 15.0)) is False  # Outside right
    assert zone.contains((15.0, 5.0)) is False  # Outside bottom
    assert zone.contains((15.0, 25.0)) is False  # Outside top
    
    # Points as Point objects
    assert zone.contains(Point(15.0, 15.0)) is True  # Center
    assert zone.contains(Point(10.0, 10.0)) is True  # Bottom-left corner
    assert zone.contains(Point(20.0, 20.0)) is True  # Top-right corner
    assert zone.contains(Point(5.0, 15.0)) is False  # Outside left


def test_distance_function():
    """Test the distance function with various points."""
    # Using Point objects
    p1 = Point(0.0, 0.0)
    p2 = Point(3.0, 4.0)
    p3 = Point(10.0, 10.0)
    
    assert distance(p1, p2) == 5.0  # 3-4-5 triangle
    assert distance(p1, p3) == pytest.approx(14.142135)  # 10√2
    assert distance(p2, p3) == pytest.approx(10.77032)  # sqrt(7^2 + 6^2)
    
    # Using tuples
    assert distance((0.0, 0.0), (3.0, 4.0)) == 5.0
    assert distance((0.0, 0.0), (10.0, 10.0)) == pytest.approx(14.142135)
    
    # Mixed
    assert distance(p1, (3.0, 4.0)) == 5.0
    assert distance((10.0, 10.0), p2) == pytest.approx(10.77032)
    
    # Verify equivalent to numpy's hypot
    for _ in range(10):
        x1, y1 = np.random.random(2) * 100
        x2, y2 = np.random.random(2) * 100
        
        our_dist = distance((x1, y1), (x2, y2))
        np_dist = np.hypot(x2 - x1, y2 - y1)
        
        assert our_dist == pytest.approx(np_dist) 