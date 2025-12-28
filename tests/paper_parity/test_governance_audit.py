"""
test_governance_audit.py - Paper Parity Test

Tests AuditLogger for tamper-evident logging:
- AuditLogger class
- Append-only logging
- Cryptographic signing

Reference: Paper Section 5 "Audit logging and forensics"
Proving Example: examples/paper/governance_demo.py
"""

import time

import pytest

from spaxiom.governance import AuditLogger, AuditEntry


class TestAuditLoggerClass:
    """Tests for AuditLogger class."""

    def test_audit_logger_exists(self):
        """AuditLogger class must exist."""
        assert AuditLogger is not None

    def test_audit_logger_accepts_backend(self):
        """AuditLogger must accept backend parameter."""
        audit = AuditLogger(backend="append_only_db")
        assert audit.backend == "append_only_db"

    def test_audit_entry_exists(self):
        """AuditEntry class must exist."""
        assert AuditEntry is not None

    def test_audit_entry_to_dict(self):
        """AuditEntry must have to_dict() method."""
        entry = AuditEntry(
            timestamp=time.time(),
            event_type="data_access",
            actor="user_123",
            action="read",
            resource="occupancy_data",
        )
        d = entry.to_dict()

        assert d["event_type"] == "data_access"
        assert d["actor"] == "user_123"
        assert d["action"] == "read"


class TestAuditLogging:
    """Tests for audit logging operations."""

    def test_audit_has_log_method(self):
        """AuditLogger must have log(entry) method."""
        audit = AuditLogger()

        entry = AuditEntry(
            timestamp=time.time(),
            event_type="data_access",
            actor="user_123",
            action="read",
        )
        audit.log(entry)

        assert audit.count() == 1

    def test_logs_are_append_only(self):
        """Audit logs must be append-only (no modification/deletion)."""
        audit = AuditLogger()

        # Add entries
        for i in range(3):
            entry = AuditEntry(
                timestamp=time.time(),
                event_type="test",
                actor=f"user_{i}",
                action="action",
            )
            audit.log(entry)

        assert audit.count() == 3

        # Seal the log
        audit.seal()

        # Attempting to log after sealing should fail
        with pytest.raises(RuntimeError):
            audit.log(
                AuditEntry(
                    timestamp=time.time(),
                    event_type="test",
                    actor="user_x",
                    action="action",
                )
            )

    def test_log_event_convenience_method(self):
        """log_event() is a convenience for creating and logging entries."""
        audit = AuditLogger()

        entry = audit.log_event(
            event_type="config_change",
            actor="admin",
            action="update",
            resource="settings",
            details={"setting": "tick_rate", "old": 10, "new": 20},
        )

        assert entry.event_type == "config_change"
        assert audit.count() == 1

    def test_runtime_accepts_audit_logger(self):
        """Runtime must accept audit logger via set_audit_logger()."""
        from spaxiom.tick import PhasedTickRunner

        runner = PhasedTickRunner()
        audit = AuditLogger()

        runner.set_audit_logger(audit)
        assert runner._audit_logger is audit


class TestCryptographicSigning:
    """Tests for cryptographic signing."""

    def test_audit_has_sign_method(self):
        """AuditLogger must have sign(entry, private_key) method."""
        audit = AuditLogger()

        entry = AuditEntry(
            timestamp=1234567890.0,
            event_type="test",
            actor="user",
            action="action",
        )

        signature = audit.sign(entry, b"secret_key")
        assert signature is not None
        assert len(signature) == 64  # SHA256 hex

    def test_audit_has_verify_method(self):
        """AuditLogger must have verify(entry, signature, public_key) method."""
        audit = AuditLogger()
        key = b"secret_key"

        entry = AuditEntry(
            timestamp=1234567890.0,
            event_type="test",
            actor="user",
            action="action",
        )

        signature = audit.sign(entry, key)
        assert audit.verify(entry, signature, key) is True

    def test_tamper_detection(self):
        """Modified entries must fail verification."""
        audit = AuditLogger()
        key = b"secret_key"

        entry = AuditEntry(
            timestamp=1234567890.0,
            event_type="test",
            actor="user",
            action="action",
        )

        signature = audit.sign(entry, key)

        # Tamper with the entry
        entry.actor = "hacker"

        # Verification should fail
        assert audit.verify(entry, signature, key) is False

    def test_auto_signing_with_key(self):
        """AuditLogger should auto-sign when signing_key is provided."""
        key = b"auto_sign_key"
        audit = AuditLogger(signing_key=key)

        entry = AuditEntry(
            timestamp=time.time(),
            event_type="test",
            actor="user",
            action="action",
        )
        audit.log(entry)

        # Entry should be signed
        assert entry.signature is not None
        assert audit.verify(entry, entry.signature, key) is True

    def test_verify_integrity(self):
        """verify_integrity() checks all signed entries."""
        key = b"integrity_key"
        audit = AuditLogger(signing_key=key)

        for i in range(5):
            audit.log_event(
                event_type="test",
                actor=f"user_{i}",
                action="action",
            )

        # All entries should be valid
        assert audit.verify_integrity() is True

    def test_query_entries(self):
        """get_entries() supports filtering."""
        audit = AuditLogger()

        audit.log_event("read", "alice", "read_data")
        audit.log_event("write", "bob", "write_data")
        audit.log_event("read", "alice", "read_more")

        # Filter by actor
        alice_entries = audit.get_entries(actor="alice")
        assert len(alice_entries) == 2

        # Filter by event type
        read_entries = audit.get_entries(event_type="read")
        assert len(read_entries) == 2
