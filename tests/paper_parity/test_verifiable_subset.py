"""
test_verifiable_subset.py - Paper Parity Test

Tests the verifiable subset of the Spaxiom DSL:
- VerifiableCondition class
- IR representation
- Restrictions enforcement

Reference: Paper Section 7.3 "Verified subset of Spaxiom DSL"
Proving Example: examples/paper/safety_export_uppaal.py
"""

import pytest

# Skip entire module if spaxiom.safety not yet implemented (Step 5)
pytest.importorskip("spaxiom.safety", reason="Requires Step 5: safety module")

from spaxiom.safety import (
    VerifiableCondition,
    IRNode,
    IRSignal,
    IRConst,
    IRCompare,
    IRAnd,
    IROr,
    IRNot,
    IRWithin,
    signal,
    const,
    compare,
    within,
    verifiable,
)


class TestVerifiableSubsetDefinition:
    """Tests for verifiable subset definition."""

    def test_verifiable_condition_exists(self):
        """VerifiableCondition class must exist."""
        assert VerifiableCondition is not None

    def test_verifiable_condition_creation(self):
        """VerifiableCondition can be created from IR."""
        ir = compare("temperature", "<", 100)
        cond = VerifiableCondition(ir, name="temp_safe")
        assert cond is not None
        assert cond.name == "temp_safe"

    def test_verifiable_builder_function(self):
        """verifiable() builder function works."""
        ir = compare("pressure", ">", 10)
        cond = verifiable(ir, "pressure_ok")
        assert isinstance(cond, VerifiableCondition)
        assert cond.name == "pressure_ok"


class TestIRNodes:
    """Tests for IR node types."""

    def test_ir_signal(self):
        """IRSignal represents a named signal."""
        sig = IRSignal("temperature")
        assert sig.name == "temperature"
        assert sig.get_signals() == ["temperature"]
        assert sig.to_uppaal_guard() == "temperature"

    def test_ir_const(self):
        """IRConst represents a constant value."""
        c1 = IRConst(42)
        assert c1.value == 42
        assert c1.to_uppaal_guard() == "42"

        c2 = IRConst(True)
        assert c2.to_uppaal_guard() == "true"

    def test_ir_compare(self):
        """IRCompare represents a comparison."""
        cmp = IRCompare(IRSignal("temp"), "<", IRConst(100))
        assert cmp.op == "<"
        assert cmp.to_uppaal_guard() == "temp < 100"
        assert cmp.get_signals() == ["temp"]

    def test_ir_and(self):
        """IRAnd represents logical AND."""
        left = IRCompare(IRSignal("a"), ">", IRConst(0))
        right = IRCompare(IRSignal("b"), "<", IRConst(10))
        ir_and = IRAnd(left, right)
        assert "(a > 0)" in ir_and.to_uppaal_guard()
        assert "(b < 10)" in ir_and.to_uppaal_guard()
        assert "&&" in ir_and.to_uppaal_guard()

    def test_ir_or(self):
        """IROr represents logical OR."""
        left = IRCompare(IRSignal("x"), "==", IRConst(1))
        right = IRCompare(IRSignal("y"), "==", IRConst(1))
        ir_or = IROr(left, right)
        assert "||" in ir_or.to_uppaal_guard()

    def test_ir_not(self):
        """IRNot represents logical NOT."""
        inner = IRCompare(IRSignal("flag"), "==", IRConst(True))
        ir_not = IRNot(inner)
        assert "!" in ir_not.to_uppaal_guard()


class TestVerifiableRestrictions:
    """Tests for verifiable subset restrictions."""

    def test_only_ir_based_construction(self):
        """Verifiable conditions are built from IR, not lambdas."""
        # This is enforced by the API - you MUST provide an IRNode
        ir = compare("value", ">=", 0)
        cond = VerifiableCondition(ir)
        # We cannot accidentally pass a lambda
        assert hasattr(cond, "_ir")
        assert isinstance(cond._ir, IRNode)

    def test_ir_is_inspectable(self):
        """IR can be inspected/retrieved."""
        ir = compare("sensor", "<", 50)
        cond = VerifiableCondition(ir)
        retrieved = cond.to_ir()
        assert retrieved is ir
        assert isinstance(retrieved, IRCompare)


class TestVerifiableEvaluation:
    """Tests for evaluating verifiable conditions."""

    def test_evaluate_simple_comparison(self):
        """Verifiable conditions can be evaluated."""
        ir = compare("temp", "<", 100)
        cond = VerifiableCondition(ir)

        # Safe temperature
        assert cond.evaluate({"temp": 50}) is True

        # Unsafe temperature
        assert cond.evaluate({"temp": 150}) is False

    def test_evaluate_combined_conditions(self):
        """Combined verifiable conditions can be evaluated."""
        temp_ok = compare("temp", "<", 100)
        pressure_ok = compare("pressure", "<", 50)
        ir_combined = IRAnd(temp_ok, pressure_ok)
        cond = VerifiableCondition(ir_combined)

        # Both ok
        assert cond.evaluate({"temp": 50, "pressure": 30}) is True

        # One fails
        assert cond.evaluate({"temp": 150, "pressure": 30}) is False
        assert cond.evaluate({"temp": 50, "pressure": 80}) is False

    def test_boolean_operators(self):
        """Verifiable conditions support &, |, ~ operators."""
        temp_ok = verifiable(compare("temp", "<", 100), "temp")
        pressure_ok = verifiable(compare("pressure", "<", 50), "pressure")

        # AND
        combined = temp_ok & pressure_ok
        assert isinstance(combined, VerifiableCondition)
        assert combined.evaluate({"temp": 50, "pressure": 30}) is True

        # OR
        either = temp_ok | pressure_ok
        assert isinstance(either, VerifiableCondition)
        assert either.evaluate({"temp": 150, "pressure": 30}) is True

        # NOT
        temp_high = ~temp_ok
        assert isinstance(temp_high, VerifiableCondition)
        assert temp_high.evaluate({"temp": 150}) is True


class TestBuilderFunctions:
    """Tests for IR builder functions."""

    def test_signal_builder(self):
        """signal() creates IRSignal."""
        s = signal("my_sensor")
        assert isinstance(s, IRSignal)
        assert s.name == "my_sensor"

    def test_const_builder(self):
        """const() creates IRConst."""
        c = const(42)
        assert isinstance(c, IRConst)
        assert c.value == 42

    def test_compare_builder(self):
        """compare() creates IRCompare with auto-wrapping."""
        # With strings (auto-wrap to signal)
        cmp = compare("temp", "<", 100)
        assert isinstance(cmp, IRCompare)
        assert isinstance(cmp.left, IRSignal)
        assert isinstance(cmp.right, IRConst)

    def test_within_builder(self):
        """within() creates IRWithin for temporal conditions."""
        inner = compare("motion", "==", True)
        w = within(inner, 5.0, "motion_clk")
        assert isinstance(w, IRWithin)
        assert w.seconds == 5.0
        assert "motion_clk" in w.get_clocks()
