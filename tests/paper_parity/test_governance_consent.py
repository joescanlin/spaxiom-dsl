"""
test_governance_consent.py - Paper Parity Test

Tests ConsentManager for zone-based consent:
- ConsentManager class
- opt_out / is_opted_out methods
- Event suppression

Reference: Paper Section 5 "Zone-based consent management"
Proving Example: examples/paper/governance_demo.py
"""

from spaxiom.governance import ConsentManager


class TestConsentManagerClass:
    """Tests for ConsentManager class."""

    def test_consent_manager_exists(self):
        """ConsentManager class must exist."""
        assert ConsentManager is not None

    def test_consent_manager_has_opt_out(self):
        """ConsentManager must have opt_out(user_id, zones) method."""
        consent = ConsentManager()
        consent.opt_out(user_id="employee_42", zones=["lounge", "restroom"])

        # Verify opt-out was recorded
        opted_out_zones = consent.get_opted_out_zones("employee_42")
        assert "lounge" in opted_out_zones
        assert "restroom" in opted_out_zones

    def test_consent_manager_has_is_opted_out(self):
        """ConsentManager must have is_opted_out(zone) method."""
        consent = ConsentManager()
        consent.opt_out(user_id="employee_42", zones=["lounge"])

        assert consent.is_opted_out(zone="lounge") is True
        assert consent.is_opted_out(zone="lobby") is False


class TestConsentEnforcement:
    """Tests for consent enforcement."""

    def test_events_suppressed_for_opted_out_zones(self):
        """Events must be suppressed for zones where user has opted out."""
        consent = ConsentManager()
        consent.opt_out(user_id="employee_42", zones=["lounge"])

        # Event from opted-out zone
        event = {"zone": "lounge", "user_id": "employee_42", "value": 1}

        # Should be suppressed
        assert consent.should_suppress_event(zone="lounge", user_id="employee_42")
        assert consent.filter_event(event) is None

    def test_events_allowed_for_other_zones(self):
        """Events must still be emitted for zones not opted out."""
        consent = ConsentManager()
        consent.opt_out(user_id="employee_42", zones=["lounge"])

        # Event from allowed zone
        event = {"zone": "lobby", "user_id": "employee_42", "value": 1}

        # Should NOT be suppressed
        assert not consent.should_suppress_event(zone="lobby", user_id="employee_42")
        filtered = consent.filter_event(event)
        assert filtered is not None
        assert filtered["value"] == 1

    def test_global_zone_suppression(self):
        """Globally suppressed zones block all events."""
        consent = ConsentManager()
        consent.suppress_zone("private_room")

        # Event from globally suppressed zone
        event = {"zone": "private_room", "value": 1}

        assert consent.is_opted_out("private_room") is True
        assert consent.filter_event(event) is None

    def test_opt_in_reverses_opt_out(self):
        """opt_in() should reverse a previous opt_out()."""
        consent = ConsentManager()
        consent.opt_out(user_id="user1", zones=["zone_a", "zone_b"])

        assert consent.is_opted_out("zone_a", user_id="user1") is True

        consent.opt_in(user_id="user1", zones=["zone_a"])

        assert consent.is_opted_out("zone_a", user_id="user1") is False
        assert consent.is_opted_out("zone_b", user_id="user1") is True

    def test_runtime_accepts_consent_manager(self):
        """Runtime must accept consent manager via set_consent_manager()."""
        from spaxiom.tick import PhasedTickRunner

        runner = PhasedTickRunner()
        consent = ConsentManager()

        runner.set_consent_manager(consent)
        assert runner._consent_manager is consent

    def test_consent_summary(self):
        """get_consent_summary() returns useful statistics."""
        consent = ConsentManager()
        consent.opt_out(user_id="user1", zones=["zone_a"])
        consent.opt_out(user_id="user2", zones=["zone_a", "zone_b"])
        consent.suppress_zone("zone_c")

        summary = consent.get_consent_summary()

        assert summary["total_users"] == 2
        assert "zone_a" in summary["zones_with_optouts"]
        assert "zone_c" in summary["globally_suppressed"]
        assert summary["optouts_by_zone"]["zone_a"] == 2
