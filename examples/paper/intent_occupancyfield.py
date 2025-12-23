#!/usr/bin/env python3
"""
intent_occupancyfield.py - Paper Parity Example

Demonstrates OccupancyField pattern with proper runtime integration:
- Pattern.update(dt, context) method
- Pattern.emit() returning typed OccupancyChanged events
- Pattern.depends_on() for dependency declaration
- Event serialization via to_dict()

Reference: Paper Section 2.4 and Section 3

STATUS: NOT IMPLEMENTED YET

What this example will demonstrate when implemented:
- OccupancyField integrated into runtime tick loop
- Typed event emission (OccupancyChanged, CrowdingDetected)
- Event serialization for LLM consumption
"""

print("=" * 60)
print("intent_occupancyfield.py")
print("=" * 60)
print()
print("STATUS: NOT IMPLEMENTED YET")
print()
print("Missing capabilities:")
print("  - Pattern base class with update(dt, context)")
print("  - Pattern.emit() returning typed events")
print("  - Pattern.depends_on() for dependencies")
print("  - Typed event classes with to_dict()")
print("  - Runtime integration for pattern updates")
print()
print("When implemented, this example will:")
print("  1. Create a floor grid sensor (simulated)")
print("  2. Create OccupancyField pattern wrapping it")
print("  3. Run runtime and observe emitted events")
print("  4. Serialize events to JSON for LLM context")
print()
print("See: docs/paper_parity_checklist.md Section 3.1")
