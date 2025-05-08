"""
Zone module for spatial definitions in Spaxiom DSL.
"""

from dataclasses import dataclass
from typing import Union, Tuple
import numpy as np


@dataclass(frozen=True)
class Point:
    """
    A 2D point in the spatial system.

    Attributes:
        x: The x-coordinate
        y: The y-coordinate
    """

    x: float
    y: float

    def __repr__(self) -> str:
        return f"Point({self.x:.2f}, {self.y:.2f})"


@dataclass
class Zone:
    """
    A rectangular zone defined by two corner points.

    Attributes:
        x1: The x-coordinate of the first corner
        y1: The y-coordinate of the first corner
        x2: The x-coordinate of the second corner
        y2: The y-coordinate of the second corner
    """

    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self):
        """Ensure x1,y1 is the bottom-left and x2,y2 is the top-right"""
        if self.x1 > self.x2:
            self.x1, self.x2 = self.x2, self.x1
        if self.y1 > self.y2:
            self.y1, self.y2 = self.y2, self.y1

    def contains(self, point: Union[Point, Tuple[float, float]]) -> bool:
        """
        Check if a point is within this zone.

        Args:
            point: Either a Point object or a tuple of (x, y) coordinates

        Returns:
            True if the point is inside the zone, False otherwise
        """
        if isinstance(point, tuple):
            x, y = point
        else:
            x, y = point.x, point.y

        return (self.x1 <= x <= self.x2) and (self.y1 <= y <= self.y2)

    def __repr__(self) -> str:
        return f"Zone({self.x1:.2f}, {self.y1:.2f}, {self.x2:.2f}, {self.y2:.2f})"


def distance(
    p1: Union[Point, Tuple[float, float]], p2: Union[Point, Tuple[float, float]]
) -> float:
    """
    Calculate the Euclidean distance between two points.

    Args:
        p1: First point (Point object or tuple of coordinates)
        p2: Second point (Point object or tuple of coordinates)

    Returns:
        The Euclidean distance between the points
    """
    if isinstance(p1, tuple):
        x1, y1 = p1
    else:
        x1, y1 = p1.x, p1.y

    if isinstance(p2, tuple):
        x2, y2 = p2
    else:
        x2, y2 = p2.x, p2.y

    return float(np.hypot(x2 - x1, y2 - y1))
