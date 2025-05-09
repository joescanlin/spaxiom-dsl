"""
Units module for handling physical quantities in Spaxiom DSL.
"""

from typing import Any, Union
import pint

# Create a global unit registry
ureg = pint.UnitRegistry()


def Quantity(value: Union[int, float], unit_str: str) -> Any:
    """
    Create a Pint Quantity with the given value and unit.

    Args:
        value: Numeric value
        unit_str: String representation of the unit (e.g., 'm', 'kg', 's')

    Returns:
        Pint Quantity object that combines the value and unit

    Example:
        ```python
        distance = Quantity(5, 'm')
        time = Quantity(10, 's')
        speed = distance / time  # Automatically handles unit conversion
        ```
    """
    # Always use Quantity constructor for all units to handle offset units properly
    return ureg.Quantity(value, unit_str)


# Export the Quantity type for type annotations
QuantityType = pint.Quantity
