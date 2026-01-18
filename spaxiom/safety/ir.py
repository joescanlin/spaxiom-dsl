"""
Intermediate Representation (IR) for verifiable conditions.

Defines the verifiable subset of the Spaxiom DSL:
- No arbitrary Python lambdas
- Only Boolean ops, comparisons, temporal operators
- Supports export to UPPAAL timed automata

Reference: Paper Section 7.3 "Verified subset of Spaxiom DSL"
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Union

# =============================================================================
# IR Node Hierarchy
# =============================================================================


class IRNode(ABC):
    """Base class for all IR nodes in the verifiable subset."""

    @abstractmethod
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate the IR node given a context of signal values.

        Args:
            context: Dict mapping signal names to their current values

        Returns:
            Boolean result of evaluation
        """
        pass

    @abstractmethod
    def to_uppaal_guard(self) -> str:
        """Convert IR node to UPPAAL guard syntax.

        Returns:
            String representation as UPPAAL guard condition
        """
        pass

    @abstractmethod
    def get_signals(self) -> List[str]:
        """Get list of signal names referenced by this node.

        Returns:
            List of signal names
        """
        pass

    @abstractmethod
    def get_clocks(self) -> List[str]:
        """Get list of clock names referenced by this node (for temporal).

        Returns:
            List of clock names
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


@dataclass
class IRSignal(IRNode):
    """Reference to a named signal (sensor value, pattern output, etc.)."""

    name: str

    def evaluate(self, context: Dict[str, Any]) -> Any:
        """Return the signal value from context."""
        if self.name not in context:
            raise ValueError(f"Signal '{self.name}' not found in context")
        return context[self.name]

    def to_uppaal_guard(self) -> str:
        return self.name

    def get_signals(self) -> List[str]:
        return [self.name]

    def get_clocks(self) -> List[str]:
        return []

    def __repr__(self) -> str:
        return f"IRSignal({self.name!r})"


@dataclass
class IRConst(IRNode):
    """Constant value in the IR."""

    value: Union[bool, int, float]

    def evaluate(self, context: Dict[str, Any]) -> Any:
        return self.value

    def to_uppaal_guard(self) -> str:
        if isinstance(self.value, bool):
            return "true" if self.value else "false"
        return str(self.value)

    def get_signals(self) -> List[str]:
        return []

    def get_clocks(self) -> List[str]:
        return []

    def __repr__(self) -> str:
        return f"IRConst({self.value!r})"


@dataclass
class IRCompare(IRNode):
    """Comparison between two values (signals or constants)."""

    left: IRNode
    op: str  # "<", "<=", ">", ">=", "==", "!="
    right: IRNode

    def evaluate(self, context: Dict[str, Any]) -> bool:
        left_val = self.left.evaluate(context)
        right_val = self.right.evaluate(context)

        if self.op == "<":
            return left_val < right_val
        elif self.op == "<=":
            return left_val <= right_val
        elif self.op == ">":
            return left_val > right_val
        elif self.op == ">=":
            return left_val >= right_val
        elif self.op == "==":
            return left_val == right_val
        elif self.op == "!=":
            return left_val != right_val
        else:
            raise ValueError(f"Unknown comparison operator: {self.op}")

    def to_uppaal_guard(self) -> str:
        return f"{self.left.to_uppaal_guard()} {self.op} {self.right.to_uppaal_guard()}"

    def get_signals(self) -> List[str]:
        return self.left.get_signals() + self.right.get_signals()

    def get_clocks(self) -> List[str]:
        return self.left.get_clocks() + self.right.get_clocks()

    def __repr__(self) -> str:
        return f"IRCompare({self.left!r}, {self.op!r}, {self.right!r})"


@dataclass
class IRAnd(IRNode):
    """Logical AND of two conditions."""

    left: IRNode
    right: IRNode

    def evaluate(self, context: Dict[str, Any]) -> bool:
        return bool(self.left.evaluate(context) and self.right.evaluate(context))

    def to_uppaal_guard(self) -> str:
        return f"({self.left.to_uppaal_guard()}) && ({self.right.to_uppaal_guard()})"

    def get_signals(self) -> List[str]:
        return self.left.get_signals() + self.right.get_signals()

    def get_clocks(self) -> List[str]:
        return self.left.get_clocks() + self.right.get_clocks()

    def __repr__(self) -> str:
        return f"IRAnd({self.left!r}, {self.right!r})"


@dataclass
class IROr(IRNode):
    """Logical OR of two conditions."""

    left: IRNode
    right: IRNode

    def evaluate(self, context: Dict[str, Any]) -> bool:
        return bool(self.left.evaluate(context) or self.right.evaluate(context))

    def to_uppaal_guard(self) -> str:
        return f"({self.left.to_uppaal_guard()}) || ({self.right.to_uppaal_guard()})"

    def get_signals(self) -> List[str]:
        return self.left.get_signals() + self.right.get_signals()

    def get_clocks(self) -> List[str]:
        return self.left.get_clocks() + self.right.get_clocks()

    def __repr__(self) -> str:
        return f"IROr({self.left!r}, {self.right!r})"


@dataclass
class IRNot(IRNode):
    """Logical NOT of a condition."""

    operand: IRNode

    def evaluate(self, context: Dict[str, Any]) -> bool:
        return not self.operand.evaluate(context)

    def to_uppaal_guard(self) -> str:
        return f"!({self.operand.to_uppaal_guard()})"

    def get_signals(self) -> List[str]:
        return self.operand.get_signals()

    def get_clocks(self) -> List[str]:
        return self.operand.get_clocks()

    def __repr__(self) -> str:
        return f"IRNot({self.operand!r})"


@dataclass
class IRWithin(IRNode):
    """Temporal 'within' operator: condition has been true for at least N seconds.

    This maps to a clock constraint in UPPAAL.
    """

    condition: IRNode
    seconds: float
    clock_name: str = field(default="")

    def __post_init__(self):
        if not self.clock_name:
            # Generate a unique clock name based on condition
            self.clock_name = f"clk_{id(self) % 10000}"

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate requires clock value in context."""
        cond_val = self.condition.evaluate(context)
        if not cond_val:
            return False
        # Check if clock has reached threshold
        clock_key = f"_clock_{self.clock_name}"
        clock_val = context.get(clock_key, 0.0)
        return clock_val >= self.seconds

    def to_uppaal_guard(self) -> str:
        cond_guard = self.condition.to_uppaal_guard()
        return f"({cond_guard}) && ({self.clock_name} >= {self.seconds})"

    def get_signals(self) -> List[str]:
        return self.condition.get_signals()

    def get_clocks(self) -> List[str]:
        return [self.clock_name] + self.condition.get_clocks()

    def __repr__(self) -> str:
        return f"IRWithin({self.condition!r}, {self.seconds})"


# =============================================================================
# Verifiable Condition Wrapper
# =============================================================================


class VerifiableCondition:
    """A condition that is part of the verifiable subset.

    Unlike regular Conditions which can wrap arbitrary Python lambdas,
    VerifiableConditions are built from IR nodes and can be exported
    to UPPAAL for formal verification.
    """

    def __init__(self, ir: IRNode, name: str = ""):
        """Create a verifiable condition from an IR node.

        Args:
            ir: The IR node representing this condition
            name: Optional human-readable name for the condition
        """
        self._ir = ir
        self._name = name or f"cond_{id(self) % 10000}"

    @property
    def name(self) -> str:
        """Return the condition name."""
        return self._name

    @property
    def ir(self) -> IRNode:
        """Return the IR representation."""
        return self._ir

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate the condition given signal values.

        Args:
            context: Dict mapping signal names to values

        Returns:
            Boolean result
        """
        return self._ir.evaluate(context)

    def to_ir(self) -> IRNode:
        """Return the IR representation (for export/inspection)."""
        return self._ir

    def to_uppaal_guard(self) -> str:
        """Convert to UPPAAL guard syntax."""
        return self._ir.to_uppaal_guard()

    def get_signals(self) -> List[str]:
        """Get list of signals referenced by this condition."""
        return list(set(self._ir.get_signals()))

    def get_clocks(self) -> List[str]:
        """Get list of clocks referenced by this condition."""
        return list(set(self._ir.get_clocks()))

    # Boolean operators return new VerifiableConditions
    def __and__(self, other: "VerifiableCondition") -> "VerifiableCondition":
        return VerifiableCondition(IRAnd(self._ir, other._ir))

    def __or__(self, other: "VerifiableCondition") -> "VerifiableCondition":
        return VerifiableCondition(IROr(self._ir, other._ir))

    def __invert__(self) -> "VerifiableCondition":
        return VerifiableCondition(IRNot(self._ir))

    def __repr__(self) -> str:
        return f"VerifiableCondition({self._ir!r}, name={self._name!r})"


# =============================================================================
# Builder Functions for Creating IR
# =============================================================================


def signal(name: str) -> IRSignal:
    """Create a signal reference."""
    return IRSignal(name)


def const(value: Union[bool, int, float]) -> IRConst:
    """Create a constant value."""
    return IRConst(value)


def compare(
    left: Union[IRNode, str, int, float],
    op: str,
    right: Union[IRNode, str, int, float],
) -> IRCompare:
    """Create a comparison.

    Args:
        left: Left operand (signal name, constant, or IR node)
        op: Comparison operator ("<", "<=", ">", ">=", "==", "!=")
        right: Right operand

    Returns:
        IRCompare node
    """
    if isinstance(left, str):
        left = IRSignal(left)
    elif isinstance(left, (int, float, bool)):
        left = IRConst(left)

    if isinstance(right, str):
        right = IRSignal(right)
    elif isinstance(right, (int, float, bool)):
        right = IRConst(right)

    return IRCompare(left, op, right)


def within(condition: IRNode, seconds: float, clock_name: str = "") -> IRWithin:
    """Create a temporal 'within' constraint."""
    return IRWithin(condition, seconds, clock_name)


def verifiable(ir: IRNode, name: str = "") -> VerifiableCondition:
    """Create a verifiable condition from IR.

    This is the primary entry point for creating verifiable conditions.

    Args:
        ir: IR node representing the condition
        name: Optional name for the condition

    Returns:
        VerifiableCondition instance
    """
    return VerifiableCondition(ir, name)
