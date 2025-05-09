"""
Model module for probabilistic and machine learning models in Spaxiom DSL.
"""

import random
from typing import Any


class StubModel:
    """
    A stub machine learning model that returns True with a given probability.

    This is useful for testing and simulation purposes where an actual ML model
    is not needed but probabilistic behavior is desired.

    Attributes:
        name: Name of the model
        probability: Probability of returning True (between 0.0 and 1.0)
    """

    def __init__(self, name: str, probability: float = 0.1):
        """
        Initialize a stub model with a given probability of returning True.

        Args:
            name: Name of the model
            probability: Probability of returning True (default: 0.1)
                         Must be between 0.0 and 1.0

        Raises:
            ValueError: If probability is not between 0.0 and 1.0
        """
        if not 0.0 <= probability <= 1.0:
            raise ValueError("Probability must be between 0.0 and 1.0")

        self.name = name
        self.probability = probability

    def predict(self, *args: Any, **kwargs: Any) -> bool:
        """
        Make a prediction based on the configured probability.

        Args:
            *args: Any positional arguments (ignored)
            **kwargs: Any keyword arguments (ignored)

        Returns:
            True with probability set during initialization, False otherwise
        """
        return random.random() < self.probability

    def __repr__(self) -> str:
        """Return a string representation of the model."""
        return f"StubModel(name='{self.name}', probability={self.probability})"
