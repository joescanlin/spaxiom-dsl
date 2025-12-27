"""
test_condition_dependency_tracking.py - Paper Parity Test

Tests condition dependency tracking:
- Condition.dependencies property
- Manual dependency declaration via depends_on
- Runtime invalidation of affected conditions

Reference: Paper Section 2.5
Proving Example: examples/paper/conditions_dependencies.py
"""

import pytest

from spaxiom import Condition, RandomSensor, SensorRegistry


class TestDependencyProperty:
    """Tests for Condition.dependencies property."""

    def test_condition_has_dependencies_property(self):
        """Condition must have a dependencies property."""
        cond = Condition(lambda: True)
        assert hasattr(cond, "dependencies")
        # Default should be empty set
        assert cond.dependencies == set()

    def test_dependencies_include_sensors(self):
        """dependencies must include referenced sensors."""
        # Clear registry first
        SensorRegistry().clear()

        sensor_a = RandomSensor(name="sensor_a", location=(0, 0, 0))
        cond = Condition(lambda: sensor_a.read() > 0.5, depends_on=[sensor_a])
        assert sensor_a in cond.dependencies

    def test_dependencies_include_patterns(self):
        """dependencies must include referenced patterns."""

        # Use a mock pattern-like object
        class MockPattern:
            def percent(self):
                return 50.0

        pattern = MockPattern()
        cond = Condition(lambda: pattern.percent() > 50.0, depends_on=[pattern])
        assert pattern in cond.dependencies


class TestDependencyInference:
    """Tests for dependency declaration."""

    @pytest.mark.skip(
        reason="DEFERRED: Automatic lambda inspection is complex; manual declaration is the supported path"
    )
    def test_automatic_inference_from_lambda(self):
        """Dependencies must be automatically inferred from condition function."""
        # Automatic inference from lambdas requires bytecode analysis
        # which is deferred in favor of explicit depends_on declaration.
        pass

    def test_manual_dependency_declaration(self):
        """Users must be able to manually declare dependencies."""
        SensorRegistry().clear()

        sensor_a = RandomSensor(name="sensor_a", location=(0, 0, 0))
        sensor_b = RandomSensor(name="sensor_b", location=(1, 0, 0))

        def complex_function():
            return sensor_a.read() + sensor_b.read() > 1.0

        cond = Condition(complex_function, depends_on=[sensor_a, sensor_b])
        # Check using 'in' operator since sensors aren't hashable
        assert sensor_a in cond.dependencies
        assert sensor_b in cond.dependencies
        assert len(cond.dependencies) == 2


class TestRuntimeInvalidation:
    """Tests for runtime dependency invalidation."""

    def test_runtime_builds_dependency_graph(self):
        """Runtime/Condition tracks dependencies that can be used for invalidation."""
        SensorRegistry().clear()

        sensor_a = RandomSensor(name="sensor_a", location=(0, 0, 0))
        sensor_b = RandomSensor(name="sensor_b", location=(1, 0, 0))

        cond_a = Condition(
            lambda: sensor_a.read() > 0.5,
            mode="event-driven",
            depends_on=[sensor_a],
        )
        cond_b = Condition(
            lambda: sensor_b.read() > 0.5,
            mode="event-driven",
            depends_on=[sensor_b],
        )

        # Verify dependencies are correctly tracked
        assert sensor_a in cond_a.dependencies
        assert sensor_b not in cond_a.dependencies
        assert sensor_b in cond_b.dependencies
        assert sensor_a not in cond_b.dependencies

    @pytest.mark.skip(
        reason="DEFERRED: Full runtime integration test requires async test setup"
    )
    def test_sensor_update_invalidates_dependents(self):
        """When sensor updates, runtime must mark dependent conditions as needing evaluation."""
        # This is tested in test_event_driven_condition_selection.py with async tests
        pass


class TestCombinedConditionDependencies:
    """Tests for dependencies in combined conditions."""

    def test_and_combines_dependencies(self):
        """AND operation should combine dependencies from both conditions."""
        SensorRegistry().clear()

        sensor_a = RandomSensor(name="sensor_a", location=(0, 0, 0))
        sensor_b = RandomSensor(name="sensor_b", location=(1, 0, 0))

        cond_a = Condition(lambda: sensor_a.read() > 0.5, depends_on=[sensor_a])
        cond_b = Condition(lambda: sensor_b.read() > 0.5, depends_on=[sensor_b])

        combined = cond_a & cond_b
        # Check using 'in' operator since sensors aren't hashable
        assert sensor_a in combined.dependencies
        assert sensor_b in combined.dependencies
        assert len(combined.dependencies) == 2

    def test_or_combines_dependencies(self):
        """OR operation should combine dependencies from both conditions."""
        SensorRegistry().clear()

        sensor_a = RandomSensor(name="sensor_a", location=(0, 0, 0))
        sensor_b = RandomSensor(name="sensor_b", location=(1, 0, 0))

        cond_a = Condition(lambda: sensor_a.read() > 0.5, depends_on=[sensor_a])
        cond_b = Condition(lambda: sensor_b.read() > 0.5, depends_on=[sensor_b])

        combined = cond_a | cond_b
        # Check using 'in' operator since sensors aren't hashable
        assert sensor_a in combined.dependencies
        assert sensor_b in combined.dependencies
        assert len(combined.dependencies) == 2

    def test_not_preserves_dependencies(self):
        """NOT operation should preserve dependencies from original condition."""
        SensorRegistry().clear()

        sensor_a = RandomSensor(name="sensor_a", location=(0, 0, 0))

        cond_a = Condition(lambda: sensor_a.read() > 0.5, depends_on=[sensor_a])

        inverted = ~cond_a
        # Check using 'in' operator since sensors aren't hashable
        assert sensor_a in inverted.dependencies
        assert len(inverted.dependencies) == 1
