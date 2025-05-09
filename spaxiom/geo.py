"""
Geometry module for spatial operations in Spaxiom DSL.
"""

from typing import Optional

from spaxiom.zone import Zone


def intersection(z1: Zone, z2: Zone) -> Optional[Zone]:
    """
    Calculate the intersection of two zones.

    Args:
        z1: First zone
        z2: Second zone

    Returns:
        A new Zone representing the intersection, or None if there is no intersection
    """
    # Find the coordinates of the intersection rectangle
    x1 = max(z1.x1, z2.x1)
    y1 = max(z1.y1, z2.y1)
    x2 = min(z1.x2, z2.x2)
    y2 = min(z1.y2, z2.y2)

    # Check if the zones actually intersect
    if x1 > x2 or y1 > y2:
        return None

    # Return the intersection zone
    return Zone(x1, y1, x2, y2)


def union(*zones: Zone) -> Optional[Zone]:
    """
    Calculate the smallest zone containing all input zones (bounding box).

    Args:
        *zones: One or more zones to union

    Returns:
        A new Zone representing the union, or None if no zones provided
    """
    if not zones:
        return None

    # Find the coordinates of the bounding rectangle
    x1 = min(z.x1 for z in zones)
    y1 = min(z.y1 for z in zones)
    x2 = max(z.x2 for z in zones)
    y2 = max(z.y2 for z in zones)

    # Return the union zone
    return Zone(x1, y1, x2, y2)


# Add the operator overloads to the Zone class
def _add_operator_overloads():
    """Add operator overloads to the Zone class."""

    def __and__(self, other: Zone) -> Optional[Zone]:
        """
        Implement the & operator for zone intersection.

        Args:
            other: Another zone to intersect with this one

        Returns:
            A new Zone representing the intersection, or None if no intersection
        """
        return intersection(self, other)

    def __or__(self, other: Zone) -> Zone:
        """
        Implement the | operator for zone union.

        Args:
            other: Another zone to union with this one

        Returns:
            A new Zone representing the union
        """
        return union(self, other)

    # Add the methods to the Zone class
    Zone.__and__ = __and__
    Zone.__or__ = __or__


# Apply the operator overloads when this module is imported
_add_operator_overloads()
