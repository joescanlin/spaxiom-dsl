#!/usr/bin/env python3
"""
governance_demo.py - Paper Parity Example

Demonstrates all governance primitives working together:
1. RetentionPolicy - bounded storage with TTL
2. ConsentManager - zone/entity opt-out
3. Authorizer (RBAC/ABAC) - access control
4. AuditLogger - structured event logging

Reference: Paper Section 5 "Privacy, Security, and Data Governance"
"""

import time

from spaxiom.governance import (
    RetentionPolicy,
    ConsentManager,
    Authorizer,
    Role,
    Policy,
    AuditLogger,
)
from spaxiom.tick import PhasedTickRunner


def main():
    print("=" * 60)
    print("governance_demo.py - Governance Primitives Demo")
    print("=" * 60)
    print()

    # =========================================================================
    # 1. Retention Policy
    # =========================================================================
    print("1. RetentionPolicy - Bounded Storage with TTL")
    print("-" * 40)

    retention = RetentionPolicy(
        default_days=30,
        raw_events_days=7,
        exceptions=["SafetyIncident", "AuditEvent"],
        max_entries=1000,
    )

    print(f"   Default retention: {retention.default_days} days")
    print(f"   Raw events retention: {retention.raw_events_days} days")
    print(f"   Exceptions: {retention.exceptions}")
    print(f"   Max entries: {retention.max_entries}")

    # Demonstrate retention filtering
    current = time.time()
    sample_buffer = [
        {"timestamp": current - (10 * 24 * 60 * 60), "event_type": "sensor", "val": 1},
        {"timestamp": current - (1 * 60 * 60), "event_type": "sensor", "val": 2},
        {"timestamp": current - (60 * 24 * 60 * 60), "event_type": "SafetyIncident"},
    ]

    retained = retention.apply_to_buffer(sample_buffer, current_time=current)
    print(f"   Sample buffer: {len(sample_buffer)} events")
    print(f"   After retention: {len(retained)} events")
    print("   (SafetyIncident retained despite age due to exception)")
    print()

    # =========================================================================
    # 2. Consent Manager
    # =========================================================================
    print("2. ConsentManager - Zone-Based Consent")
    print("-" * 40)

    consent = ConsentManager()

    # Employee opts out of certain zones
    consent.opt_out(user_id="employee_42", zones=["lounge", "restroom"])
    consent.opt_out(user_id="employee_99", zones=["restroom"])

    # Globally suppress a zone
    consent.suppress_zone("executive_suite")

    print("   Opt-outs recorded:")
    print(f"     employee_42: {consent.get_opted_out_zones('employee_42')}")
    print(f"     employee_99: {consent.get_opted_out_zones('employee_99')}")

    # Test event filtering
    events = [
        {"zone": "lobby", "occupancy": 5},
        {"zone": "lounge", "occupancy": 2},
        {"zone": "executive_suite", "occupancy": 1},
    ]

    print("   Event filtering:")
    for event in events:
        filtered = consent.filter_event(event)
        status = "ALLOWED" if filtered else "SUPPRESSED"
        print(f"     Zone '{event['zone']}': {status}")

    print(f"   Summary: {consent.get_consent_summary()}")
    print()

    # =========================================================================
    # 3. Authorization (RBAC + ABAC)
    # =========================================================================
    print("3. Authorizer - RBAC + ABAC Access Control")
    print("-" * 40)

    auth = Authorizer()

    # Define roles (RBAC)
    operator = Role(name="operator", permissions={"read:occupancy", "read:queue"})
    admin = Role(name="admin", permissions={"read:*", "write:config"})
    viewer = Role(name="viewer", permissions={"read:occupancy"})

    auth.add_role(operator)
    auth.add_role(admin)
    auth.add_role(viewer)

    # Assign users to roles
    auth.assign_user("alice", "admin")
    auth.assign_user("bob", "operator")
    auth.assign_user("charlie", "viewer")

    print("   RBAC Roles:")
    print(
        f"     alice (admin): can read:occupancy = {auth.check('alice', 'read:occupancy')}"
    )
    print(
        f"     alice (admin): can write:config = {auth.check('alice', 'write:config')}"
    )
    print(
        f"     bob (operator): can read:occupancy = {auth.check('bob', 'read:occupancy')}"
    )
    print(
        f"     bob (operator): can write:config = {auth.check('bob', 'write:config')}"
    )
    print(
        f"     charlie (viewer): can read:queue = {auth.check('charlie', 'read:queue')}"
    )

    # Add ABAC policy (time-based)
    office_hours = Policy(
        name="office_hours",
        effect="allow",
        condition=lambda ctx: 9 <= ctx.get("environment", {}).get("hour", 12) <= 17,
    )
    auth.add_policy(office_hours)

    print("   ABAC Policy: office_hours (9-17)")
    print()

    # =========================================================================
    # 4. Audit Logger
    # =========================================================================
    print("4. AuditLogger - Tamper-Evident Logging")
    print("-" * 40)

    # Create signed audit logger
    signing_key = b"governance_demo_key_12345"
    audit = AuditLogger(backend="memory", signing_key=signing_key)

    # Log some governance events
    audit.log_event(
        event_type="consent_change",
        actor="employee_42",
        action="opt_out",
        resource="zone:lounge",
        details={"reason": "privacy preference"},
    )

    audit.log_event(
        event_type="access_check",
        actor="bob",
        action="read:occupancy",
        resource="zone:lobby",
        outcome="allowed",
    )

    audit.log_event(
        event_type="retention_purge",
        actor="system",
        action="purge",
        resource="event_buffer",
        details={"events_purged": 42, "policy": "30_days"},
    )

    print(f"   Logged {audit.count()} audit entries")
    print(f"   All entries signed: {all(e.signature for e in audit._entries)}")
    print(f"   Integrity verified: {audit.verify_integrity()}")

    # Query audit log
    consent_events = audit.get_entries(event_type="consent_change")
    print(f"   Consent changes: {len(consent_events)}")

    # Export for inspection
    print("   Sample entry:")
    sample = audit._entries[0].to_dict()
    print(f"     event_type: {sample['event_type']}")
    print(f"     actor: {sample['actor']}")
    print(f"     action: {sample['action']}")
    print(f"     signature: {sample['signature'][:32]}...")
    print()

    # =========================================================================
    # 5. Runtime Integration
    # =========================================================================
    print("5. Runtime Integration")
    print("-" * 40)

    runner = PhasedTickRunner(tick_rate_hz=10.0)

    # Register all governance hooks
    runner.set_retention_policy(retention)
    runner.set_consent_manager(consent)
    runner.set_authorizer(auth)
    runner.set_audit_logger(audit)

    print("   Governance hooks registered:")
    print(f"     retention_policy: {runner._retention_policy is not None}")
    print(f"     consent_manager: {runner._consent_manager is not None}")
    print(f"     authorizer: {runner._authorizer is not None}")
    print(f"     audit_logger: {runner._audit_logger is not None}")
    print()

    # =========================================================================
    # 6. End-to-End Enforcement Example
    # =========================================================================
    print("6. End-to-End Enforcement Example")
    print("-" * 40)

    def process_occupancy_event(event, user_id):
        """Demonstrate governance checks on an event."""
        print(f"   Processing event: {event}")

        # 1. Check authorization
        if not auth.check(user_id, "read:occupancy"):
            audit.log_event(
                event_type="access_denied",
                actor=user_id,
                action="read:occupancy",
                resource=event.get("zone", "unknown"),
                outcome="denied",
            )
            print(f"     -> DENIED: {user_id} lacks read:occupancy permission")
            return None

        # 2. Check consent
        zone = event.get("zone", "")
        if consent.should_suppress_event(zone):
            audit.log_event(
                event_type="event_suppressed",
                actor="system",
                action="suppress",
                resource=zone,
                details={"reason": "consent_opt_out"},
            )
            print(f"     -> SUPPRESSED: zone '{zone}' opted out")
            return None

        # 3. Log successful access
        audit.log_event(
            event_type="data_access",
            actor=user_id,
            action="read:occupancy",
            resource=zone,
            outcome="success",
        )
        print(f"     -> ALLOWED: {user_id} accessed zone '{zone}'")
        return event

    # Test scenarios
    print()
    process_occupancy_event({"zone": "lobby", "occupancy": 10}, "bob")
    process_occupancy_event({"zone": "lounge", "occupancy": 3}, "bob")
    process_occupancy_event({"zone": "lobby", "occupancy": 8}, "charlie")
    print()

    print("=" * 60)
    print("Done!")
    print(f"Total audit entries: {audit.count()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
