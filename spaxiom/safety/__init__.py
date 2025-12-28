"""
Safety verification and monitoring for Spaxiom DSL.

This module provides:
- Verifiable subset of the DSL (IR representation)
- UPPAAL timed automaton export
- Runtime safety monitoring

Reference: Paper Section 7.3
"""

from .ir import (
    # IR node types
    IRNode,
    IRSignal,
    IRConst,
    IRCompare,
    IRAnd,
    IROr,
    IRNot,
    IRWithin,
    # Verifiable condition wrapper
    VerifiableCondition,
    # Builder functions
    signal,
    const,
    compare,
    within,
    verifiable,
)

from .monitor import (
    SafetyMonitor,
    SafetyViolation,
)

from . import verify

__all__ = [
    # IR nodes
    "IRNode",
    "IRSignal",
    "IRConst",
    "IRCompare",
    "IRAnd",
    "IROr",
    "IRNot",
    "IRWithin",
    # Verifiable condition
    "VerifiableCondition",
    # Builder functions
    "signal",
    "const",
    "compare",
    "within",
    "verifiable",
    # Monitor
    "SafetyMonitor",
    "SafetyViolation",
    # Verify module
    "verify",
]
