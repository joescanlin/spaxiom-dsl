"""
Model module for probabilistic and machine learning models in Spaxiom DSL.
"""

import random
from typing import Any, List, Optional
import numpy as np


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


class SensorModel:
    """
    Base class for models that process sensor data.

    All sensor models should inherit from this class and implement the predict method.
    """

    def __init__(self, name: str):
        """
        Initialize a sensor model with a name.

        Args:
            name: Name of the model
        """
        self.name = name

    def predict(self, **kwargs: Any) -> Any:
        """
        Make a prediction based on input data.

        Args:
            **kwargs: Input data for the model

        Returns:
            Model prediction
        """
        raise NotImplementedError("Subclasses must implement predict()")

    def __repr__(self) -> str:
        """Return a string representation of the model."""
        return f"{self.__class__.__name__}(name='{self.name}')"


class OnnxModel(SensorModel):
    """
    A model that uses ONNX Runtime for inference.

    This class loads an ONNX model and provides a predict method to run inference.
    The model is loaded lazily when the first prediction is made.

    Attributes:
        name: Name of the model
        path: Path to the ONNX model file
        input_names: List of input tensor names
        output_name: Name of the output tensor
        providers: List of execution providers to use
    """

    def __init__(
        self,
        name: str,
        path: str,
        input_names: List[str],
        output_name: str = "output",
        providers: Optional[List[str]] = None,
    ):
        """
        Initialize an ONNX model.

        Args:
            name: Name of the model
            path: Path to the ONNX model file
            input_names: List of input tensor names expected by the model
            output_name: Name of the output tensor (default: 'output')
            providers: List of execution providers to use (default: CPUExecutionProvider)
        """
        super().__init__(name)
        self.path = path
        self.input_names = input_names
        self.output_name = output_name
        self.providers = providers
        self._session = None
        self._onnx_available = self._check_onnx_available()

    def _check_onnx_available(self) -> bool:
        """Check if onnxruntime is available."""
        try:
            import onnxruntime  # noqa: F401

            return True
        except ImportError:
            return False

    def _ensure_session(self):
        """
        Ensure the ONNX session is loaded.
        Loads the session lazily if it hasn't been loaded yet.

        Raises:
            ImportError: If onnxruntime is not installed
        """
        if not self._onnx_available:
            raise ImportError(
                "onnxruntime is not installed. Please install it with: pip install onnxruntime>=1.18"
            )

        if self._session is None:
            import onnxruntime as ort

            # Use default provider if none specified
            if self.providers is None:
                self.providers = ["CPUExecutionProvider"]

            # Load the model
            self._session = ort.InferenceSession(self.path, providers=self.providers)

    def predict(self, **named_arrays) -> np.ndarray:
        """
        Run inference on the ONNX model.

        Args:
            **named_arrays: Input tensors as numpy arrays, with names matching input_names

        Returns:
            Model output as numpy array

        Raises:
            ValueError: If any of the required input names are missing
            ImportError: If onnxruntime is not installed
        """
        # Ensure session is loaded
        self._ensure_session()

        # Validate inputs
        missing_inputs = set(self.input_names) - set(named_arrays.keys())
        if missing_inputs:
            raise ValueError(f"Missing required inputs: {missing_inputs}")

        # Prepare input dict, only including the expected inputs
        input_dict = {name: named_arrays[name] for name in self.input_names}

        # Run inference
        outputs = self._session.run([self.output_name], input_dict)

        # Return the first output
        return outputs[0]

    def __repr__(self) -> str:
        """Return a string representation of the model."""
        return f"OnnxModel(name='{self.name}', path='{self.path}')"
