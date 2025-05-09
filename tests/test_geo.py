"""
Unit tests for the geometry module.
"""

import unittest
from spaxiom import Zone, intersection, union


class TestGeometry(unittest.TestCase):
    """Test suite for geometry operations."""

    def test_intersection(self):
        """Test the intersection of two zones."""
        # Overlapping zones
        z1 = Zone(0, 0, 10, 10)
        z2 = Zone(5, 5, 15, 15)
        result = intersection(z1, z2)
        self.assertIsNotNone(result)
        self.assertEqual(result.x1, 5)
        self.assertEqual(result.y1, 5)
        self.assertEqual(result.x2, 10)
        self.assertEqual(result.y2, 10)

        # Non-overlapping zones
        z3 = Zone(0, 0, 5, 5)
        z4 = Zone(10, 10, 15, 15)
        result = intersection(z3, z4)
        self.assertIsNone(result)

        # One zone completely inside another
        z5 = Zone(0, 0, 20, 20)
        z6 = Zone(5, 5, 15, 15)
        result = intersection(z5, z6)
        self.assertIsNotNone(result)
        self.assertEqual(result.x1, 5)
        self.assertEqual(result.y1, 5)
        self.assertEqual(result.x2, 15)
        self.assertEqual(result.y2, 15)

    def test_union(self):
        """Test the union of multiple zones."""
        # Two zones
        z1 = Zone(0, 0, 10, 10)
        z2 = Zone(5, 5, 15, 15)
        result = union(z1, z2)
        self.assertIsNotNone(result)
        self.assertEqual(result.x1, 0)
        self.assertEqual(result.y1, 0)
        self.assertEqual(result.x2, 15)
        self.assertEqual(result.y2, 15)

        # Three zones
        z3 = Zone(-5, -5, 0, 0)
        result = union(z1, z2, z3)
        self.assertIsNotNone(result)
        self.assertEqual(result.x1, -5)
        self.assertEqual(result.y1, -5)
        self.assertEqual(result.x2, 15)
        self.assertEqual(result.y2, 15)

        # No zones
        result = union()
        self.assertIsNone(result)

        # Single zone
        result = union(z1)
        self.assertIsNotNone(result)
        self.assertEqual(result.x1, 0)
        self.assertEqual(result.y1, 0)
        self.assertEqual(result.x2, 10)
        self.assertEqual(result.y2, 10)

    def test_operator_overloads(self):
        """Test the operator overloads (& and |) for zones."""
        # Intersection with &
        z1 = Zone(0, 0, 10, 10)
        z2 = Zone(5, 5, 15, 15)
        result = z1 & z2
        self.assertIsNotNone(result)
        self.assertEqual(result.x1, 5)
        self.assertEqual(result.y1, 5)
        self.assertEqual(result.x2, 10)
        self.assertEqual(result.y2, 10)

        # Union with |
        result = z1 | z2
        self.assertIsNotNone(result)
        self.assertEqual(result.x1, 0)
        self.assertEqual(result.y1, 0)
        self.assertEqual(result.x2, 15)
        self.assertEqual(result.y2, 15)

        # No intersection
        z3 = Zone(0, 0, 5, 5)
        z4 = Zone(10, 10, 15, 15)
        result = z3 & z4
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
