import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

# Import onnx helper for creating test models
try:
    import onnx
    from onnx import helper, TensorProto

    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

from spaxiom import OnnxModel


def create_simple_onnx_model(path):
    """Create a simple ONNX model that adds two inputs and saves it to the specified path."""
    # Create the graph with one add operation
    X = helper.make_tensor_value_info("X", TensorProto.FLOAT, [1, 3])
    Y = helper.make_tensor_value_info("Y", TensorProto.FLOAT, [1, 3])
    Z = helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 3])

    # Create an Add node (Z = X + Y)
    node_def = helper.make_node(
        "Add",
        inputs=["X", "Y"],
        outputs=["output"],
    )

    # Create the graph
    graph_def = helper.make_graph([node_def], "simple-model", [X, Y], [Z])

    # Create the model
    model_def = helper.make_model(graph_def, producer_name="spaxiom-test")
    model_def.opset_import[0].version = 13

    # Save the model
    onnx.save(model_def, path)


@pytest.mark.skipif(not ONNX_AVAILABLE, reason="ONNX not installed")
class TestOnnxModel(unittest.TestCase):
    """Test cases for the OnnxModel class."""

    def setUp(self):
        """Set up temporary model file for tests."""
        # Create a temporary file for the ONNX model
        self.temp_dir = tempfile.TemporaryDirectory()
        self.model_path = os.path.join(self.temp_dir.name, "simple_model.onnx")

        # Create a simple ONNX model
        create_simple_onnx_model(self.model_path)

    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()

    def test_init(self):
        """Test that the model initializes correctly without loading session."""
        model = OnnxModel("test_model", self.model_path, ["X", "Y"])

        # Check that the model is initialized but session is not loaded yet
        self.assertEqual(model.name, "test_model")
        self.assertEqual(model.path, self.model_path)
        self.assertEqual(model.input_names, ["X", "Y"])
        self.assertEqual(model.output_name, "output")
        self.assertIsNone(model._session)

    def test_lazy_loading(self):
        """Test that the model loads the session lazily only when needed."""
        model = OnnxModel("test_model", self.model_path, ["X", "Y"])

        # Session should not be loaded yet
        self.assertIsNone(model._session)

        # Calling _ensure_session should load the session
        model._ensure_session()
        self.assertIsNotNone(model._session)

    def test_predict(self):
        """Test that predict runs inference and returns the correct result."""
        model = OnnxModel("test_model", self.model_path, ["X", "Y"])

        # Create test inputs
        X = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)
        Y = np.array([[4.0, 5.0, 6.0]], dtype=np.float32)

        # Run prediction
        result = model.predict(X=X, Y=Y)

        # Check that the result is as expected (X + Y)
        expected = np.array([[5.0, 7.0, 9.0]], dtype=np.float32)
        np.testing.assert_allclose(result, expected)

        # Session should be loaded after prediction
        self.assertIsNotNone(model._session)

    def test_missing_input(self):
        """Test that predict raises ValueError when input is missing."""
        model = OnnxModel("test_model", self.model_path, ["X", "Y"])

        # Create only one of the required inputs
        X = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)

        # Run prediction - should raise ValueError
        with self.assertRaises(ValueError):
            model.predict(X=X)

    def test_custom_providers(self):
        """Test that custom providers are correctly passed to InferenceSession."""
        # Create model with custom provider
        with patch("onnxruntime.InferenceSession") as mock_session:
            # Create a mock that simulates running inference
            mock_instance = MagicMock()
            mock_instance.run.return_value = [
                np.array([[5.0, 7.0, 9.0]], dtype=np.float32)
            ]
            mock_session.return_value = mock_instance

            # Create the model with a custom provider
            model = OnnxModel(
                "test_model",
                self.model_path,
                ["X", "Y"],
                providers=["TestExecutionProvider"],
            )

            # Trigger session creation and check that provider was passed
            X = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)
            Y = np.array([[4.0, 5.0, 6.0]], dtype=np.float32)
            model.predict(X=X, Y=Y)

            # Check that the session was created with the correct provider
            mock_session.assert_called_once_with(
                self.model_path, providers=["TestExecutionProvider"]
            )


if __name__ == "__main__":
    unittest.main()
