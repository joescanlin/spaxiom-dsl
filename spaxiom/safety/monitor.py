"""
SafetyMonitor for runtime safety property enforcement.

Monitors safety properties during runtime and triggers failsafe callbacks
when violations occur. Produces structured audit records.

Reference: Paper Section 7.3 "Runtime monitoring and enforcement"
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from spaxiom.safety.ir import VerifiableCondition
    from spaxiom.safety.verify import UppaalAutomaton
    from spaxiom.logic import Condition


@dataclass
class SafetyViolation:
    """Structured audit record for a safety violation.

    Contains all information needed for post-incident analysis.
    """

    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    monitor_name: str = ""
    property_name: str = ""
    state: str = "violated"
    previous_state: str = "ok"
    context: Dict[str, Any] = field(default_factory=dict)
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON/logging."""
        return asdict(self)


class SafetyMonitor:
    """Runtime safety monitor that checks properties each tick.

    A SafetyMonitor wraps a safety property (condition) and triggers
    a failsafe callback when the property is violated (becomes false).

    Safety properties should be conditions that must ALWAYS be true.
    When they become false, a violation has occurred.

    Example:
        # Safety property: robot arm never exceeds speed limit
        arm_safe = VerifiableCondition(
            compare("arm_speed", "<", 100),
            name="arm_speed_limit"
        )

        def emergency_stop():
            robot.stop()

        monitor = SafetyMonitor(
            name="arm_safety",
            property=arm_safe,
            on_violation=emergency_stop
        )
    """

    def __init__(
        self,
        name: str,
        property: Union["VerifiableCondition", "Condition", Callable[[], bool]],
        on_violation: Optional[Callable[["SafetyViolation"], None]] = None,
    ):
        """Create a safety monitor.

        Args:
            name: Human-readable name for this monitor
            property: Safety property to monitor. Can be:
                - VerifiableCondition (recommended for UPPAAL export)
                - Regular Condition
                - Callable returning bool (legacy)
            on_violation: Callback invoked when property becomes false.
                         Receives the SafetyViolation record.
        """
        self._name = name
        self._property = property
        self._on_violation = on_violation
        self._last_state: bool = True  # Assume safe initially
        self._violations: List[SafetyViolation] = []
        self._check_count: int = 0

    @property
    def name(self) -> str:
        """Return monitor name."""
        return self._name

    @property
    def violations(self) -> List[SafetyViolation]:
        """Return list of recorded violations."""
        return self._violations.copy()

    @property
    def check_count(self) -> int:
        """Return number of times check() has been called."""
        return self._check_count

    def check(self, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check the safety property.

        Args:
            context: Optional context dict for VerifiableConditions

        Returns:
            True if property holds (safe), False if violated

        Side effects:
            - If violation detected, calls on_violation callback
            - Records violation in audit log
        """
        self._check_count += 1
        context = context or {}

        # Evaluate the property
        try:
            if hasattr(self._property, "evaluate"):
                # VerifiableCondition or similar
                current_state = bool(self._property.evaluate(context))
            elif hasattr(self._property, "__call__"):
                # Regular Condition or callable
                if hasattr(self._property, "fn"):
                    # It's a Condition object
                    current_state = bool(self._property())
                else:
                    current_state = bool(self._property())
            else:
                raise ValueError(
                    f"Property must be callable or have evaluate(): {type(self._property)}"
                )
        except Exception as e:
            # Treat evaluation errors as violations
            current_state = False
            context["_error"] = str(e)

        # Detect violation (transition from ok to violated)
        if self._last_state and not current_state:
            # Get property name
            prop_name = ""
            if hasattr(self._property, "name"):
                prop_name = self._property.name
            elif hasattr(self._property, "_name"):
                prop_name = self._property._name
            else:
                prop_name = str(self._property)

            # Create violation record
            violation = SafetyViolation(
                monitor_name=self._name,
                property_name=prop_name,
                state="violated",
                previous_state="ok",
                context=context.copy(),
                message=f"Safety property '{prop_name}' violated",
            )

            # Record violation
            self._violations.append(violation)

            # Trigger callback
            if self._on_violation:
                try:
                    self._on_violation(violation)
                except Exception:
                    # Don't let callback errors propagate
                    pass

        self._last_state = current_state
        return current_state

    def reset(self) -> None:
        """Reset the monitor state (for testing)."""
        self._last_state = True
        self._violations.clear()
        self._check_count = 0

    def get_audit_records(self) -> List[Dict[str, Any]]:
        """Return all violations as serialized audit records.

        Returns:
            List of violation dicts
        """
        return [v.to_dict() for v in self._violations]

    def compile_to_uppaal(self, name: Optional[str] = None) -> "UppaalAutomaton":
        """Export this monitor as an UPPAAL automaton.

        Only works if property is a VerifiableCondition.

        Args:
            name: Optional name for the automaton

        Returns:
            UppaalAutomaton instance

        Raises:
            TypeError: If property is not a VerifiableCondition
        """
        from spaxiom.safety.ir import VerifiableCondition
        from spaxiom.safety.verify import compile_to_uppaal

        if not isinstance(self._property, VerifiableCondition):
            raise TypeError(
                f"compile_to_uppaal requires VerifiableCondition, got {type(self._property)}"
            )

        return compile_to_uppaal(
            conditions=[self._property],
            name=name or f"Monitor_{self._name}",
        )

    def __repr__(self) -> str:
        return f"SafetyMonitor(name={self._name!r}, violations={len(self._violations)})"
