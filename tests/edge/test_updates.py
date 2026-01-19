"""Tests for software update management."""

import pytest

from spaxiom.edge.updates import (
    UpdateStatus,
    VersionInfo,
    UpdateResult,
    UpdateManager,
    get_current_version,
    parse_version,
    is_newer_version,
    verify_checksum,
)


class TestVersionInfo:
    """Tests for VersionInfo."""

    def test_version_info_creation(self):
        """Test creating version info."""
        info = VersionInfo(
            version="1.2.3",
            release_date="2024-01-01",
            changelog="Bug fixes",
        )

        assert info.version == "1.2.3"
        assert info.release_date == "2024-01-01"
        assert info.changelog == "Bug fixes"
        assert info.is_prerelease is False

    def test_version_info_to_dict(self):
        """Test version info serialization."""
        info = VersionInfo(
            version="1.2.3",
            release_date="2024-01-01",
            changelog="Bug fixes",
            download_url="https://example.com/download",
        )

        d = info.to_dict()

        assert d["version"] == "1.2.3"
        assert d["download_url"] == "https://example.com/download"


class TestUpdateResult:
    """Tests for UpdateResult."""

    def test_update_result_creation(self):
        """Test creating update result."""
        result = UpdateResult(
            success=True,
            message="Update installed",
            old_version="1.0.0",
            new_version="1.1.0",
        )

        assert result.success is True
        assert result.old_version == "1.0.0"
        assert result.new_version == "1.1.0"

    def test_update_result_to_dict(self):
        """Test update result serialization."""
        result = UpdateResult(
            success=False,
            message="Installation failed",
            old_version="1.0.0",
        )

        d = result.to_dict()

        assert d["success"] is False
        assert d["message"] == "Installation failed"
        assert "timestamp" in d


class TestParseVersion:
    """Tests for version parsing."""

    def test_parse_simple_version(self):
        """Test parsing simple version."""
        result = parse_version("1.2.3")
        assert result == (1, 2, 3, 0, 0)

    def test_parse_version_with_prefix(self):
        """Test parsing version with v prefix."""
        result = parse_version("v1.2.3")
        assert result == (1, 2, 3, 0, 0)

    def test_parse_prerelease_rc(self):
        """Test parsing RC version."""
        result = parse_version("1.2.3rc1")
        assert result[0:3] == (1, 2, 3)
        assert result[3] == -1  # RC marker

    def test_parse_prerelease_alpha(self):
        """Test parsing alpha version."""
        result = parse_version("1.2.3alpha1")
        assert result[3] == -3  # Alpha marker

    def test_parse_prerelease_beta(self):
        """Test parsing beta version."""
        result = parse_version("1.2.3beta2")
        assert result[3] == -2  # Beta marker

    def test_parse_short_version(self):
        """Test parsing version with fewer parts."""
        result = parse_version("1.2")
        assert result == (1, 2, 0, 0, 0)


class TestIsNewerVersion:
    """Tests for version comparison."""

    def test_newer_major(self):
        """Test newer major version."""
        assert is_newer_version("1.0.0", "2.0.0") is True

    def test_newer_minor(self):
        """Test newer minor version."""
        assert is_newer_version("1.0.0", "1.1.0") is True

    def test_newer_patch(self):
        """Test newer patch version."""
        assert is_newer_version("1.0.0", "1.0.1") is True

    def test_older_version(self):
        """Test older version."""
        assert is_newer_version("1.1.0", "1.0.0") is False

    def test_same_version(self):
        """Test same version."""
        assert is_newer_version("1.0.0", "1.0.0") is False

    def test_release_newer_than_rc(self):
        """Test release is newer than RC."""
        assert is_newer_version("1.0.0rc1", "1.0.0") is True

    def test_rc2_newer_than_rc1(self):
        """Test RC2 is newer than RC1."""
        assert is_newer_version("1.0.0rc1", "1.0.0rc2") is True

    def test_beta_newer_than_alpha(self):
        """Test beta is newer than alpha."""
        assert is_newer_version("1.0.0alpha1", "1.0.0beta1") is True


class TestGetCurrentVersion:
    """Tests for get_current_version."""

    def test_returns_version_string(self):
        """Test that a version string is returned."""
        version = get_current_version()
        assert isinstance(version, str)
        assert len(version) > 0


class TestVerifyChecksum:
    """Tests for checksum verification."""

    def test_verify_valid_checksum(self, tmp_path):
        """Test verifying valid checksum."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Calculate actual checksum
        import hashlib

        expected = hashlib.sha256(b"test content").hexdigest()

        assert verify_checksum(str(test_file), expected) is True

    def test_verify_invalid_checksum(self, tmp_path):
        """Test verifying invalid checksum."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        assert verify_checksum(str(test_file), "invalid") is False


class TestUpdateStatus:
    """Tests for UpdateStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert UpdateStatus.IDLE.value == "idle"
        assert UpdateStatus.CHECKING.value == "checking"
        assert UpdateStatus.AVAILABLE.value == "available"
        assert UpdateStatus.DOWNLOADING.value == "downloading"
        assert UpdateStatus.INSTALLING.value == "installing"
        assert UpdateStatus.COMPLETE.value == "complete"
        assert UpdateStatus.FAILED.value == "failed"
        assert UpdateStatus.ROLLED_BACK.value == "rolled_back"


class TestUpdateManager:
    """Tests for UpdateManager."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create update manager."""
        return UpdateManager(
            update_url="https://updates.example.com",
            check_interval=3600,
            backup_dir=str(tmp_path / "backups"),
        )

    def test_initial_status(self, manager):
        """Test initial status is idle."""
        assert manager.status == UpdateStatus.IDLE

    def test_no_available_update_initially(self, manager):
        """Test no update available initially."""
        assert manager.available_update is None

    def test_get_status(self, manager):
        """Test getting manager status."""
        status = manager.get_status()

        assert status["status"] == "idle"
        assert "current_version" in status
        assert status["available_update"] is None
        assert status["auto_install"] is False

    def test_add_callback(self, manager):
        """Test adding event callback."""
        events = []

        def callback(event, data):
            events.append((event, data))

        manager.add_callback(callback)

        manager._notify("test_event", {"key": "value"})

        assert len(events) == 1
        assert events[0][0] == "test_event"

    @pytest.mark.asyncio
    async def test_check_for_updates_sets_status(self, manager):
        """Test that checking for updates sets status."""
        await manager.check_for_updates()

        # Should be idle or available after check
        assert manager.status in [UpdateStatus.IDLE, UpdateStatus.AVAILABLE]
        assert manager._last_check is not None
