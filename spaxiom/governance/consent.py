"""
Consent management for zone/entity opt-out.

Provides data minimization and collection controls.

Reference: Paper Section 5 "Zone-based consent management"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class ConsentRecord:
    """Record of a consent decision.

    Attributes:
        user_id: Identifier for the user/entity
        zones: Zones the user has opted out of
        opted_out_at: Timestamp when opt-out was recorded
        reason: Optional reason for opt-out
    """

    user_id: str
    zones: Set[str] = field(default_factory=set)
    opted_out_at: Optional[float] = None
    reason: str = ""


class ConsentManager:
    """Manages consent for data collection and emission.

    Tracks which users have opted out of which zones,
    and provides enforcement checks for event emission.
    """

    def __init__(self) -> None:
        """Initialize the consent manager."""
        # user_id -> ConsentRecord
        self._records: Dict[str, ConsentRecord] = {}
        # zone -> set of user_ids that have opted out
        self._zone_opt_outs: Dict[str, Set[str]] = {}
        # Globally suppressed zones (all users)
        self._global_suppressions: Set[str] = set()

    def opt_out(
        self,
        user_id: str,
        zones: List[str],
        reason: str = "",
    ) -> None:
        """Record that a user has opted out of specified zones.

        Args:
            user_id: Identifier for the user
            zones: List of zone names to opt out of
            reason: Optional reason for opting out
        """
        import time

        if user_id not in self._records:
            self._records[user_id] = ConsentRecord(
                user_id=user_id,
                opted_out_at=time.time(),
                reason=reason,
            )

        record = self._records[user_id]
        for zone in zones:
            record.zones.add(zone)
            if zone not in self._zone_opt_outs:
                self._zone_opt_outs[zone] = set()
            self._zone_opt_outs[zone].add(user_id)

    def opt_in(self, user_id: str, zones: List[str]) -> None:
        """Record that a user has opted back in for specified zones.

        Args:
            user_id: Identifier for the user
            zones: List of zone names to opt in to
        """
        if user_id not in self._records:
            return

        record = self._records[user_id]
        for zone in zones:
            record.zones.discard(zone)
            if zone in self._zone_opt_outs:
                self._zone_opt_outs[zone].discard(user_id)

    def is_opted_out(self, zone: str, user_id: Optional[str] = None) -> bool:
        """Check if a zone is opted out.

        Args:
            zone: Zone name to check
            user_id: Optional user to check specifically

        Returns:
            True if zone is opted out (by user or globally)
        """
        # Check global suppression
        if zone in self._global_suppressions:
            return True

        # If no user specified, check if ANY user has opted out
        if user_id is None:
            return zone in self._zone_opt_outs and len(self._zone_opt_outs[zone]) > 0

        # Check specific user
        if user_id in self._records:
            return zone in self._records[user_id].zones
        return False

    def suppress_zone(self, zone: str) -> None:
        """Globally suppress a zone (all data collection).

        Args:
            zone: Zone to suppress
        """
        self._global_suppressions.add(zone)

    def unsuppress_zone(self, zone: str) -> None:
        """Remove global suppression from a zone.

        Args:
            zone: Zone to unsuppress
        """
        self._global_suppressions.discard(zone)

    def get_opted_out_zones(self, user_id: str) -> Set[str]:
        """Get all zones a user has opted out of.

        Args:
            user_id: User identifier

        Returns:
            Set of zone names
        """
        if user_id in self._records:
            return self._records[user_id].zones.copy()
        return set()

    def should_suppress_event(
        self,
        zone: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """Check if an event should be suppressed based on consent.

        This is the main enforcement point for event emission.

        Args:
            zone: Zone the event originated from
            user_id: Optional user context

        Returns:
            True if event should be suppressed
        """
        return self.is_opted_out(zone, user_id)

    def filter_event(
        self,
        event: Dict[str, Any],
        zone_key: str = "zone",
        user_key: str = "user_id",
    ) -> Optional[Dict[str, Any]]:
        """Filter an event based on consent.

        Returns None if event should be suppressed, or the event otherwise.
        Can be extended to redact specific fields instead of full suppression.

        Args:
            event: Event dictionary
            zone_key: Key for zone field in event
            user_key: Key for user_id field in event

        Returns:
            Event dict if allowed, None if suppressed
        """
        zone = event.get(zone_key, "")
        user_id = event.get(user_key)

        if self.should_suppress_event(zone, user_id):
            return None
        return event

    def get_consent_summary(self) -> Dict[str, Any]:
        """Get summary of consent state for audit purposes.

        Returns:
            Dict with consent statistics
        """
        return {
            "total_users": len(self._records),
            "zones_with_optouts": list(self._zone_opt_outs.keys()),
            "globally_suppressed": list(self._global_suppressions),
            "optouts_by_zone": {
                zone: len(users) for zone, users in self._zone_opt_outs.items()
            },
        }
