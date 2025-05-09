#!/usr/bin/env python3
"""
Geometry Demo for Spaxiom DSL.

This demonstrates:
1. Creating zones
2. Computing zone intersections using both the intersection() function and & operator
3. Computing zone unions using both the union() function and | operator
"""

import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spaxiom import Zone, intersection, union


def main():
    """Run the geometry demo."""
    print("Spaxiom Geometry Demo")
    print("--------------------")
    print("This demo demonstrates zone operations using the geo module")
    print()

    # Create some zones
    zone1 = Zone(0, 0, 10, 10)
    zone2 = Zone(5, 5, 15, 15)
    zone3 = Zone(20, 20, 30, 30)

    print(f"Zone 1: {zone1}")
    print(f"Zone 2: {zone2}")
    print(f"Zone 3: {zone3}")
    print()

    # Test intersection using function
    print("Intersection operations:")
    print(f"intersection(zone1, zone2): {intersection(zone1, zone2)}")
    print(f"intersection(zone1, zone3): {intersection(zone1, zone3)}")
    print()

    # Test intersection using operator
    print("Intersection using & operator:")
    print(f"zone1 & zone2: {zone1 & zone2}")
    print(f"zone1 & zone3: {zone1 & zone3}")
    print()

    # Test union using function
    print("Union operations:")
    print(f"union(zone1, zone2): {union(zone1, zone2)}")
    print(f"union(zone1, zone2, zone3): {union(zone1, zone2, zone3)}")
    print()

    # Test union using operator
    print("Union using | operator:")
    print(f"zone1 | zone2: {zone1 | zone2}")
    print(f"zone1 | zone3: {zone1 | zone3}")
    print()

    # Complex operation using both operators
    print("Complex operation:")
    print(f"(zone1 & zone2) | zone3: {(zone1 & zone2) | zone3}")


if __name__ == "__main__":
    main()
