"""Tests for backup and restore functionality."""

import os
import tarfile
import tempfile
from pathlib import Path

import pytest

from spaxiom.edge.backup import (
    generate_backup_name,
    create_backup,
    list_backups,
    get_backup_info,
    restore_backup,
    delete_backup,
    cleanup_old_backups,
    BackupScheduler,
)


class TestGenerateBackupName:
    """Tests for backup name generation."""

    def test_generates_name_with_timestamp(self):
        """Test that backup name includes timestamp."""
        name = generate_backup_name()
        assert name.startswith("backup_")
        assert name.endswith(".tar.gz")

    def test_custom_prefix(self):
        """Test custom prefix."""
        name = generate_backup_name(prefix="mybackup")
        assert name.startswith("mybackup_")


class TestCreateBackup:
    """Tests for backup creation."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False, mode="w") as f:
            f.write("test database content")
            yield f.name
        os.unlink(f.name)

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config_file.write_text("test: config")
            yield tmpdir

    @pytest.fixture
    def temp_backup_dir(self):
        """Create a temporary backup directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_create_backup_db_only(self, temp_db, temp_backup_dir):
        """Test creating backup with database only."""
        backup_path, info = create_backup(temp_db, backup_dir=temp_backup_dir)

        assert os.path.exists(backup_path)
        assert info["size"] > 0
        assert any(c["type"] == "database" for c in info["contents"])

    def test_create_backup_with_config(self, temp_db, temp_config_dir, temp_backup_dir):
        """Test creating backup with config directory."""
        backup_path, info = create_backup(
            temp_db,
            config_dir=temp_config_dir,
            backup_dir=temp_backup_dir,
        )

        assert os.path.exists(backup_path)
        assert any(c["type"] == "database" for c in info["contents"])
        assert any(c["type"] == "config" for c in info["contents"])

    def test_backup_contains_manifest(self, temp_db, temp_backup_dir):
        """Test that backup contains manifest.json."""
        backup_path, _ = create_backup(temp_db, backup_dir=temp_backup_dir)

        with tarfile.open(backup_path, "r:gz") as tar:
            names = tar.getnames()
            assert "manifest.json" in names

    def test_create_backup_missing_db_raises(self, temp_backup_dir):
        """Test that missing database raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            create_backup("/nonexistent/db.sqlite", backup_dir=temp_backup_dir)


class TestListBackups:
    """Tests for listing backups."""

    @pytest.fixture
    def populated_backup_dir(self):
        """Create a directory with some backup files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake database
            db_path = os.path.join(tmpdir, "test.db")
            with open(db_path, "w") as f:
                f.write("test")

            # Create a few backups
            for i in range(3):
                create_backup(db_path, backup_dir=tmpdir)

            yield tmpdir

    def test_list_backups_returns_list(self, populated_backup_dir):
        """Test that list_backups returns a list."""
        backups = list_backups(populated_backup_dir)
        assert isinstance(backups, list)
        assert len(backups) == 3

    def test_list_backups_empty_dir(self):
        """Test listing backups in empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups = list_backups(tmpdir)
            assert backups == []

    def test_list_backups_sorted_by_date(self, populated_backup_dir):
        """Test that backups are sorted newest first."""
        backups = list_backups(populated_backup_dir)
        # Names should be in reverse chronological order
        names = [b["name"] for b in backups]
        assert names == sorted(names, reverse=True)


class TestGetBackupInfo:
    """Tests for getting backup info."""

    @pytest.fixture
    def backup_file(self):
        """Create a backup file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            with open(db_path, "w") as f:
                f.write("test database")

            backup_path, _ = create_backup(db_path, backup_dir=tmpdir)
            yield backup_path

    def test_get_backup_info(self, backup_file):
        """Test getting backup info."""
        info = get_backup_info(backup_file)

        assert "path" in info
        assert "name" in info
        assert "size" in info
        assert "contents" in info

    def test_get_backup_info_missing_file(self):
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            get_backup_info("/nonexistent/backup.tar.gz")


class TestRestoreBackup:
    """Tests for restoring backups."""

    @pytest.fixture
    def backup_and_restore_dirs(self):
        """Create backup file and restore directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create source database
            db_path = os.path.join(tmpdir, "source.db")
            with open(db_path, "w") as f:
                f.write("original database content")

            # Create config
            config_dir = os.path.join(tmpdir, "config")
            os.makedirs(config_dir)
            with open(os.path.join(config_dir, "config.yaml"), "w") as f:
                f.write("original: config")

            # Create backup
            backup_path, _ = create_backup(
                db_path,
                config_dir=config_dir,
                backup_dir=tmpdir,
            )

            # Create restore paths
            restore_db = os.path.join(tmpdir, "restored.db")
            restore_config = os.path.join(tmpdir, "restored_config")

            yield {
                "backup_path": backup_path,
                "restore_db": restore_db,
                "restore_config": restore_config,
            }

    def test_restore_database(self, backup_and_restore_dirs):
        """Test restoring database."""
        result = restore_backup(
            backup_and_restore_dirs["backup_path"],
            backup_and_restore_dirs["restore_db"],
        )

        assert result["status"] == "success"
        assert os.path.exists(backup_and_restore_dirs["restore_db"])

        with open(backup_and_restore_dirs["restore_db"]) as f:
            content = f.read()
            assert content == "original database content"

    def test_restore_with_config(self, backup_and_restore_dirs):
        """Test restoring database and config."""
        result = restore_backup(
            backup_and_restore_dirs["backup_path"],
            backup_and_restore_dirs["restore_db"],
            config_dir=backup_and_restore_dirs["restore_config"],
        )

        assert result["status"] == "success"
        assert os.path.exists(backup_and_restore_dirs["restore_config"])

    def test_restore_missing_backup_raises(self):
        """Test that missing backup raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            restore_backup("/nonexistent/backup.tar.gz", "/tmp/restore.db")


class TestDeleteBackup:
    """Tests for deleting backups."""

    def test_delete_backup(self):
        """Test deleting a backup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            with open(db_path, "w") as f:
                f.write("test")

            backup_path, _ = create_backup(db_path, backup_dir=tmpdir)

            assert os.path.exists(backup_path)

            result = delete_backup(backup_path)

            assert result is True
            assert not os.path.exists(backup_path)

    def test_delete_missing_backup_raises(self):
        """Test that deleting missing backup raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            delete_backup("/nonexistent/backup.tar.gz")


class TestCleanupOldBackups:
    """Tests for cleanup functionality."""

    def test_cleanup_keeps_max_backups(self):
        """Test that cleanup keeps only max_backups."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            with open(db_path, "w") as f:
                f.write("test")

            # Create 5 backups
            for _ in range(5):
                create_backup(db_path, backup_dir=tmpdir)

            # Cleanup to keep only 2
            deleted = cleanup_old_backups(tmpdir, max_backups=2, max_age_days=365)

            assert len(deleted) == 3

            remaining = list_backups(tmpdir)
            assert len(remaining) == 2


class TestBackupScheduler:
    """Tests for BackupScheduler."""

    @pytest.fixture
    def scheduler(self):
        """Create a backup scheduler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            with open(db_path, "w") as f:
                f.write("test database")

            scheduler = BackupScheduler(
                db_path=db_path,
                backup_dir=tmpdir,
                interval_hours=24,
                max_backups=5,
            )
            yield scheduler

    def test_get_status(self, scheduler):
        """Test getting scheduler status."""
        status = scheduler.get_status()

        assert "running" in status
        assert status["running"] is False
        assert status["interval_hours"] == 24
        assert status["max_backups"] == 5

    @pytest.mark.asyncio
    async def test_run_now(self, scheduler):
        """Test running a backup immediately."""
        backup_path, info = await scheduler.run_now()

        assert os.path.exists(backup_path)
        assert info["size"] > 0
        assert scheduler._last_backup is not None
