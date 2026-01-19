"""Tests for SSL/TLS certificate management."""

import os
import tempfile
from pathlib import Path

import pytest

# Import will set HAS_CRYPTOGRAPHY based on availability
from spaxiom.edge.ssl import (
    HAS_CRYPTOGRAPHY,
    cert_exists,
)

# Only run certificate generation tests if cryptography is installed
if HAS_CRYPTOGRAPHY:
    from spaxiom.edge.ssl import (
        generate_self_signed_cert,
        get_cert_info,
        validate_cert,
        create_ssl_context,
        ensure_certs,
    )


class TestCertExists:
    """Tests for cert_exists function."""

    def test_cert_exists_returns_false_for_missing_dir(self):
        """Test that cert_exists returns False for non-existent directory."""
        assert cert_exists("/nonexistent/path") is False

    def test_cert_exists_returns_false_for_missing_files(self):
        """Test that cert_exists returns False when files are missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert cert_exists(tmpdir) is False

    def test_cert_exists_returns_false_for_partial_files(self):
        """Test that cert_exists returns False when only one file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create only cert file
            (Path(tmpdir) / "cert.pem").touch()
            assert cert_exists(tmpdir) is False

            # Create only key file
            (Path(tmpdir) / "cert.pem").unlink()
            (Path(tmpdir) / "key.pem").touch()
            assert cert_exists(tmpdir) is False


@pytest.mark.skipif(not HAS_CRYPTOGRAPHY, reason="cryptography not installed")
class TestCertificateGeneration:
    """Tests for certificate generation functions."""

    def test_generate_self_signed_cert(self):
        """Test generating a self-signed certificate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path, key_path = generate_self_signed_cert(
                common_name="Test Cert",
                output_dir=tmpdir,
            )

            assert os.path.exists(cert_path)
            assert os.path.exists(key_path)

            # Check key file permissions
            key_stat = os.stat(key_path)
            assert key_stat.st_mode & 0o777 == 0o600

    def test_generate_cert_creates_directory(self):
        """Test that generate_self_signed_cert creates the output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = os.path.join(tmpdir, "nested", "certs")

            cert_path, key_path = generate_self_signed_cert(output_dir=nested_dir)

            assert os.path.exists(nested_dir)
            assert os.path.exists(cert_path)
            assert os.path.exists(key_path)

    def test_cert_exists_returns_true_after_generation(self):
        """Test that cert_exists returns True after generating certs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_self_signed_cert(output_dir=tmpdir)
            assert cert_exists(tmpdir) is True

    def test_get_cert_info(self):
        """Test getting certificate information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path, _ = generate_self_signed_cert(
                common_name="Test Cert",
                organization="Test Org",
                valid_days=365,
                output_dir=tmpdir,
            )

            info = get_cert_info(cert_path)

            assert "Test Cert" in info["subject"]
            assert "Test Org" in info["subject"]
            assert info["is_expired"] is False
            assert info["days_until_expiry"] > 360

    def test_validate_cert_valid(self):
        """Test validating a valid certificate/key pair."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path, key_path = generate_self_signed_cert(output_dir=tmpdir)

            is_valid, message = validate_cert(cert_path, key_path)

            assert is_valid is True
            assert "valid" in message.lower()

    def test_validate_cert_mismatched_key(self):
        """Test validating with mismatched certificate and key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Generate two different cert/key pairs
            dir1 = os.path.join(tmpdir, "cert1")
            dir2 = os.path.join(tmpdir, "cert2")

            cert_path1, _ = generate_self_signed_cert(output_dir=dir1)
            _, key_path2 = generate_self_signed_cert(output_dir=dir2)

            # Try to validate with mismatched files
            is_valid, message = validate_cert(cert_path1, key_path2)

            assert is_valid is False
            assert "match" in message.lower()

    def test_create_ssl_context(self):
        """Test creating an SSL context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path, key_path = generate_self_signed_cert(output_dir=tmpdir)

            context = create_ssl_context(cert_path, key_path)

            assert context is not None

    def test_ensure_certs_generates_when_missing(self):
        """Test that ensure_certs generates certs when missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path, key_path = ensure_certs(tmpdir)

            assert os.path.exists(cert_path)
            assert os.path.exists(key_path)

    def test_ensure_certs_reuses_existing_valid(self):
        """Test that ensure_certs reuses existing valid certs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Generate initial certs
            cert_path1, key_path1 = generate_self_signed_cert(output_dir=tmpdir)

            # Get modification time
            mtime1 = os.path.getmtime(cert_path1)

            # Call ensure_certs - should reuse existing
            cert_path2, key_path2 = ensure_certs(tmpdir)

            assert cert_path1 == cert_path2
            assert key_path1 == key_path2

            # File should not be modified
            mtime2 = os.path.getmtime(cert_path2)
            assert mtime1 == mtime2
