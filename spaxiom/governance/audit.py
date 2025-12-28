"""
Audit logging for governance and forensics.

Provides structured, append-only logging with optional cryptographic signing.

Reference: Paper Section 5 "Audit logging and forensics"
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class AuditEntry:
    """A single audit log entry.

    Attributes:
        timestamp: When the event occurred
        event_type: Type of event (e.g., "data_access", "config_change")
        actor: Who performed the action
        action: What action was performed
        resource: What resource was affected
        outcome: Result of the action ("success", "failure", "denied")
        details: Additional context
        signature: Optional cryptographic signature
    """

    timestamp: float
    event_type: str
    actor: str
    action: str
    resource: str = ""
    outcome: str = "success"
    details: Dict[str, Any] = field(default_factory=dict)
    signature: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary for serialization."""
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "actor": self.actor,
            "action": self.action,
            "resource": self.resource,
            "outcome": self.outcome,
            "details": self.details,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEntry":
        """Create entry from dictionary."""
        return cls(
            timestamp=data.get("timestamp", time.time()),
            event_type=data.get("event_type", "unknown"),
            actor=data.get("actor", "unknown"),
            action=data.get("action", "unknown"),
            resource=data.get("resource", ""),
            outcome=data.get("outcome", "success"),
            details=data.get("details", {}),
            signature=data.get("signature"),
        )

    def canonical_form(self) -> str:
        """Get canonical string representation for signing.

        Returns:
            JSON string with sorted keys (excluding signature)
        """
        data = self.to_dict()
        data.pop("signature", None)
        return json.dumps(data, sort_keys=True, separators=(",", ":"))


class AuditLogger:
    """Append-only audit logger with optional signing.

    Provides tamper-evident logging for governance and forensics.
    """

    def __init__(
        self,
        backend: str = "memory",
        signing_key: Optional[bytes] = None,
        on_log: Optional[Callable[[AuditEntry], None]] = None,
    ) -> None:
        """Initialize audit logger.

        Args:
            backend: Storage backend ("memory", "append_only_db", "file")
            signing_key: Optional key for HMAC signing
            on_log: Optional callback for each logged entry
        """
        self._backend = backend
        self._signing_key = signing_key
        self._on_log = on_log
        self._entries: List[AuditEntry] = []
        self._sealed = False  # When True, no more writes allowed

    @property
    def backend(self) -> str:
        """Get the backend type."""
        return self._backend

    def log(self, entry: AuditEntry) -> None:
        """Append an entry to the audit log.

        Args:
            entry: Entry to log

        Raises:
            RuntimeError: If log is sealed
        """
        if self._sealed:
            raise RuntimeError("Audit log is sealed, no new entries allowed")

        # Auto-sign if key is configured
        if self._signing_key and entry.signature is None:
            entry.signature = self.sign(entry, self._signing_key)

        self._entries.append(entry)

        if self._on_log:
            self._on_log(entry)

    def log_event(
        self,
        event_type: str,
        actor: str,
        action: str,
        resource: str = "",
        outcome: str = "success",
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """Convenience method to create and log an entry.

        Args:
            event_type: Type of event
            actor: Who performed the action
            action: What action was performed
            resource: What resource was affected
            outcome: Result of the action
            details: Additional context

        Returns:
            The logged entry
        """
        entry = AuditEntry(
            timestamp=time.time(),
            event_type=event_type,
            actor=actor,
            action=action,
            resource=resource,
            outcome=outcome,
            details=details or {},
        )
        self.log(entry)
        return entry

    def sign(self, entry: AuditEntry, private_key: bytes) -> str:
        """Sign an entry with HMAC-SHA256.

        Args:
            entry: Entry to sign
            private_key: Key for HMAC

        Returns:
            Hex-encoded signature
        """
        canonical = entry.canonical_form()
        signature = hmac.new(
            private_key,
            canonical.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def verify(
        self,
        entry: AuditEntry,
        signature: str,
        public_key: bytes,
    ) -> bool:
        """Verify an entry's signature.

        For HMAC, public_key is the same as private_key (symmetric).

        Args:
            entry: Entry to verify
            signature: Signature to check
            public_key: Key for verification

        Returns:
            True if signature is valid
        """
        expected = self.sign(entry, public_key)
        return hmac.compare_digest(expected, signature)

    def get_entries(
        self,
        event_type: Optional[str] = None,
        actor: Optional[str] = None,
        since: Optional[float] = None,
        until: Optional[float] = None,
    ) -> List[AuditEntry]:
        """Query audit log entries.

        Args:
            event_type: Filter by event type
            actor: Filter by actor
            since: Filter entries after this timestamp
            until: Filter entries before this timestamp

        Returns:
            List of matching entries
        """
        results = []
        for entry in self._entries:
            if event_type and entry.event_type != event_type:
                continue
            if actor and entry.actor != actor:
                continue
            if since and entry.timestamp < since:
                continue
            if until and entry.timestamp > until:
                continue
            results.append(entry)
        return results

    def count(self) -> int:
        """Get total number of entries."""
        return len(self._entries)

    def seal(self) -> None:
        """Seal the log to prevent further writes."""
        self._sealed = True

    def is_sealed(self) -> bool:
        """Check if log is sealed."""
        return self._sealed

    def verify_integrity(self) -> bool:
        """Verify integrity of all signed entries.

        Returns:
            True if all signed entries have valid signatures
        """
        if not self._signing_key:
            return True

        for entry in self._entries:
            if entry.signature:
                if not self.verify(entry, entry.signature, self._signing_key):
                    return False
        return True

    def export(self) -> List[Dict[str, Any]]:
        """Export all entries as dictionaries."""
        return [entry.to_dict() for entry in self._entries]
