"""
Tests for the Model module functionality.
"""

import pytest
import random

from spaxiom.model import StubModel


def test_stub_model_creation():
    """Test that StubModel can be created with valid parameters."""
    # Default probability
    model = StubModel(name="test_model")
    assert model.name == "test_model"
    assert model.probability == 0.1

    # Custom probability
    model2 = StubModel(name="test_model2", probability=0.75)
    assert model2.name == "test_model2"
    assert model2.probability == 0.75


def test_stub_model_invalid_probability():
    """Test that StubModel raises an error with invalid probability values."""
    # Below 0.0
    with pytest.raises(ValueError) as excinfo:
        StubModel(name="invalid", probability=-0.1)
    assert "Probability must be between 0.0 and 1.0" in str(excinfo.value)

    # Above 1.0
    with pytest.raises(ValueError) as excinfo:
        StubModel(name="invalid", probability=1.1)
    assert "Probability must be between 0.0 and 1.0" in str(excinfo.value)


def test_stub_model_predict_deterministic():
    """
    Test that StubModel.predict() returns True with the correct probability.
    This uses a fixed seed for deterministic testing.
    """
    # Set a fixed seed for determinism
    random.seed(42)

    # With probability 0.0, should always return False
    always_false_model = StubModel(name="always_false", probability=0.0)
    results = [always_false_model.predict() for _ in range(100)]
    assert all(result is False for result in results)

    # With probability 1.0, should always return True
    always_true_model = StubModel(name="always_true", probability=1.0)
    results = [always_true_model.predict() for _ in range(100)]
    assert all(result is True for result in results)


def test_stub_model_predict_statistical():
    """
    Test that StubModel.predict() returns True with approximately the correct probability.
    This is a statistical test that may occasionally fail by chance.
    """
    # Set a seed for consistency
    random.seed(123)

    # With probability 0.3, should return True about 30% of the time
    model = StubModel(name="prob_0.3", probability=0.3)

    # Run a large number of predictions
    n_trials = 1000
    results = [model.predict() for _ in range(n_trials)]

    # Count number of True results
    n_true = sum(results)

    # Check that the proportion is close to expected (within 5 percentage points)
    proportion = n_true / n_trials
    assert 0.25 <= proportion <= 0.35


def test_stub_model_predict_ignores_args():
    """Test that StubModel.predict() ignores any arguments passed to it."""
    random.seed(42)

    model = StubModel(name="test_args", probability=0.5)

    # Same model should give same results regardless of arguments
    result1 = model.predict()
    # Call with different arguments but don't check the results directly
    model.predict("ignored_arg")
    model.predict(1, 2, 3, keyword_arg="value")

    # Reset seed to get the same sequence
    random.seed(42)
    result4 = model.predict()

    # First and fourth calls should match because we reset the seed
    assert result1 == result4


def test_stub_model_repr():
    """Test the string representation of StubModel."""
    model = StubModel(name="test_model", probability=0.25)
    assert str(model) == "StubModel(name='test_model', probability=0.25)"
