"""
test_governance_retention.py - Paper Parity Test

Tests RetentionPolicy for data governance:
- RetentionPolicy class
- Automatic event purging
- Exception handling

Reference: Paper Section 5 "Privacy, Security, and Data Governance"
Proving Example: examples/paper/governance_demo.py
"""

import time


from spaxiom.governance import RetentionPolicy


class TestRetentionPolicyClass:
    """Tests for RetentionPolicy class."""

    def test_retention_policy_exists(self):
        """RetentionPolicy class must exist."""
        assert RetentionPolicy is not None

    def test_retention_policy_constructor(self):
        """RetentionPolicy must accept default_days, raw_events_days, exceptions."""
        policy = RetentionPolicy(
            default_days=30,
            raw_events_days=7,
            exceptions=["SafetyIncident", "AuditEvent"],
        )
        assert policy.default_days == 30
        assert policy.raw_events_days == 7
        assert "SafetyIncident" in policy.exceptions

    def test_retention_policy_defaults(self):
        """RetentionPolicy has sensible defaults."""
        policy = RetentionPolicy()
        assert policy.default_days == 30
        assert policy.raw_events_days == 7
        assert policy.exceptions == []


class TestRetentionEnforcement:
    """Tests for retention policy enforcement."""

    def test_runtime_accepts_retention_policy(self):
        """Runtime must accept retention policy via set_retention_policy()."""
        from spaxiom.tick import PhasedTickRunner

        runner = PhasedTickRunner()
        policy = RetentionPolicy(default_days=30)

        runner.set_retention_policy(policy)
        assert runner._retention_policy is policy

    def test_old_events_purged(self):
        """Events older than retention period must be automatically purged."""
        policy = RetentionPolicy(default_days=1)

        # Simulate current time
        current = time.time()
        two_days_ago = current - (2 * 24 * 60 * 60)
        one_hour_ago = current - (1 * 60 * 60)

        buffer = [
            {"timestamp": two_days_ago, "event_type": "sensor_read", "value": 1},
            {"timestamp": one_hour_ago, "event_type": "sensor_read", "value": 2},
        ]

        retained = policy.apply_to_buffer(buffer, current_time=current)

        # Only the recent event should be retained
        assert len(retained) == 1
        assert retained[0]["value"] == 2

    def test_exception_events_retained(self):
        """Events in exceptions list must be retained longer."""
        policy = RetentionPolicy(default_days=1, exceptions=["SafetyIncident"])

        current = time.time()
        sixty_days_ago = current - (60 * 24 * 60 * 60)

        buffer = [
            {
                "timestamp": sixty_days_ago,
                "event_type": "SafetyIncident",
                "value": "critical",
            },
            {"timestamp": sixty_days_ago, "event_type": "sensor_read", "value": 1},
        ]

        retained = policy.apply_to_buffer(buffer, current_time=current)

        # Only SafetyIncident should be retained
        assert len(retained) == 1
        assert retained[0]["event_type"] == "SafetyIncident"

    def test_should_retain_checks_age(self):
        """should_retain() correctly checks event age."""
        policy = RetentionPolicy(default_days=7)

        current = time.time()
        old = current - (10 * 24 * 60 * 60)  # 10 days ago
        recent = current - (1 * 24 * 60 * 60)  # 1 day ago

        assert policy.should_retain(old, current_time=current) is False
        assert policy.should_retain(recent, current_time=current) is True

    def test_max_entries_limit(self):
        """max_entries limits buffer size."""
        policy = RetentionPolicy(default_days=30, max_entries=3)

        current = time.time()
        buffer = [
            {"timestamp": current, "event_type": "event", "value": i} for i in range(10)
        ]

        retained = policy.apply_to_buffer(buffer, current_time=current)

        # Only last 3 entries should be kept
        assert len(retained) == 3
        assert [e["value"] for e in retained] == [7, 8, 9]
