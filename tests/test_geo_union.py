"""
Unit tests for geometry operations focusing on overlapping box behaviors.
"""

import unittest
from spaxiom import Zone, intersection, union


class TestOverlappingBoxOperations(unittest.TestCase):
    """Test suite focusing on union and intersection behavior of overlapping boxes."""

    def test_simple_overlap(self):
        """Test partial overlap where boxes share a quadrant."""
        # Boxes overlapping in top-right/bottom-left quadrants
        z1 = Zone(0, 0, 10, 10)
        z2 = Zone(5, 5, 15, 15)

        # Intersection should be the overlapping part
        result = intersection(z1, z2)
        self.assertEqual(result.x1, 5)
        self.assertEqual(result.y1, 5)
        self.assertEqual(result.x2, 10)
        self.assertEqual(result.y2, 10)

        # Union should encompass both boxes
        result = union(z1, z2)
        self.assertEqual(result.x1, 0)
        self.assertEqual(result.y1, 0)
        self.assertEqual(result.x2, 15)
        self.assertEqual(result.y2, 15)

    def test_containment(self):
        """Test when one box completely contains the other."""
        # Box z1 completely contains z2
        z1 = Zone(0, 0, 20, 20)
        z2 = Zone(5, 5, 15, 15)

        # Intersection should be the smaller box
        result = intersection(z1, z2)
        self.assertEqual(result.x1, 5)
        self.assertEqual(result.y1, 5)
        self.assertEqual(result.x2, 15)
        self.assertEqual(result.y2, 15)

        # Union should be the larger box
        result = union(z1, z2)
        self.assertEqual(result.x1, 0)
        self.assertEqual(result.y1, 0)
        self.assertEqual(result.x2, 20)
        self.assertEqual(result.y2, 20)

    def test_edge_overlap(self):
        """Test boxes that overlap only along an edge."""
        # Boxes share a vertical edge
        z1 = Zone(0, 0, 10, 10)
        z2 = Zone(10, 2, 20, 8)

        # Intersection is a vertical line (represented as a zero-width Zone)
        result = intersection(z1, z2)
        self.assertEqual(result.x1, 10)
        self.assertEqual(result.y1, 2)
        self.assertEqual(result.x2, 10)
        self.assertEqual(result.y2, 8)

        # Union covers the full range
        result = union(z1, z2)
        self.assertEqual(result.x1, 0)
        self.assertEqual(result.y1, 0)
        self.assertEqual(result.x2, 20)
        self.assertEqual(result.y2, 10)

        # Boxes share a horizontal edge
        z3 = Zone(0, 0, 10, 10)
        z4 = Zone(2, 10, 8, 20)

        # Intersection is a horizontal line (represented as a zero-height Zone)
        result = intersection(z3, z4)
        self.assertEqual(result.x1, 2)
        self.assertEqual(result.y1, 10)
        self.assertEqual(result.x2, 8)
        self.assertEqual(result.y2, 10)

        # Union covers the full range
        result = union(z3, z4)
        self.assertEqual(result.x1, 0)
        self.assertEqual(result.y1, 0)
        self.assertEqual(result.x2, 10)
        self.assertEqual(result.y2, 20)

    def test_corner_overlap(self):
        """Test boxes that overlap only at a corner."""
        # Boxes share only the top-right/bottom-left corner
        z1 = Zone(0, 0, 10, 10)
        z2 = Zone(10, 10, 20, 20)

        # Intersection is a single point (represented as a zero-area Zone)
        result = intersection(z1, z2)
        self.assertEqual(result.x1, 10)
        self.assertEqual(result.y1, 10)
        self.assertEqual(result.x2, 10)
        self.assertEqual(result.y2, 10)

        # Union covers the full range
        result = union(z1, z2)
        self.assertEqual(result.x1, 0)
        self.assertEqual(result.y1, 0)
        self.assertEqual(result.x2, 20)
        self.assertEqual(result.y2, 20)

    def test_disjoint_boxes(self):
        """Test boxes that don't overlap at all."""
        z1 = Zone(0, 0, 5, 5)
        z2 = Zone(10, 10, 15, 15)

        # Intersection should be None
        result = intersection(z1, z2)
        self.assertIsNone(result)

        # Union should encompass both boxes
        result = union(z1, z2)
        self.assertEqual(result.x1, 0)
        self.assertEqual(result.y1, 0)
        self.assertEqual(result.x2, 15)
        self.assertEqual(result.y2, 15)

    def test_operator_chaining(self):
        """Test chaining multiple union and intersection operations."""
        z1 = Zone(0, 0, 10, 10)
        z2 = Zone(5, 5, 15, 15)
        z3 = Zone(20, 20, 30, 30)

        # Chain unions: (z1 | z2) | z3
        result = (z1 | z2) | z3
        self.assertEqual(result.x1, 0)
        self.assertEqual(result.y1, 0)
        self.assertEqual(result.x2, 30)
        self.assertEqual(result.y2, 30)

        # Chain intersection with union: (z1 & z2) | z3
        result = (z1 & z2) | z3
        self.assertEqual(result.x1, 5)
        self.assertEqual(result.y1, 5)
        self.assertEqual(result.x2, 30)
        self.assertEqual(result.y2, 30)

        # Test more complex combinations
        z4 = Zone(7, 7, 25, 25)  # Overlaps with z2 and z3

        # (z1 & z2) | (z3 & z4)
        intersection1 = z1 & z2  # (5,5,10,10)
        intersection2 = z3 & z4  # (20,20,25,25)
        result = intersection1 | intersection2

        # Result should span from intersection1 to intersection2
        self.assertEqual(result.x1, 5)
        self.assertEqual(result.y1, 5)
        self.assertEqual(result.x2, 25)
        self.assertEqual(result.y2, 25)


if __name__ == "__main__":
    unittest.main()
