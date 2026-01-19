"""
SSL/TLS certificate management for Spaxiom Edge.

Provides:
- Self-signed certificate generation
- Certificate validation
- SSL context creation
"""

import logging
import os
import ssl
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Try to import cryptography for certificate generation
try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    logger.warning(
        "cryptography package not installed. "
        "Self-signed certificate generation will not be available."
    )


def generate_self_signed_cert(
    common_name: str = "Spaxiom Edge",
    organization: str = "Spaxiom",
    country: str = "US",
    state: str = "California",
    locality: str = "San Francisco",
    valid_days: int = 365,
    key_size: int = 2048,
    output_dir: Optional[str] = None,
) -> Tuple[str, str]:
    """Generate a self-signed SSL certificate and private key.

    Args:
        common_name: Certificate common name (CN)
        organization: Organization name (O)
        country: Country code (C)
        state: State/Province (ST)
        locality: City/Locality (L)
        valid_days: Certificate validity in days
        key_size: RSA key size in bits
        output_dir: Directory to save files (default: /etc/spaxiom/certs)

    Returns:
        Tuple of (cert_path, key_path)

    Raises:
        ImportError: If cryptography package is not installed
        OSError: If unable to create output directory or write files
    """
    if not HAS_CRYPTOGRAPHY:
        raise ImportError(
            "cryptography package required for certificate generation. "
            "Install with: pip install cryptography"
        )

    # Default output directory
    if output_dir is None:
        output_dir = "/etc/spaxiom/certs"

    output_path = Path(output_dir)

    # Create directory if needed
    output_path.mkdir(parents=True, exist_ok=True)

    cert_path = output_path / "cert.pem"
    key_path = output_path / "key.pem"

    # Generate private key
    logger.info(f"Generating {key_size}-bit RSA private key...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend(),
    )

    # Build certificate subject
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, country),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, state),
            x509.NameAttribute(NameOID.LOCALITY_NAME, locality),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )

    # Build certificate
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=valid_days))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.DNSName("*.local"),
                    x509.IPAddress(__import__("ipaddress").IPv4Address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=0),
            critical=True,
        )
        .sign(private_key, hashes.SHA256(), default_backend())
    )

    # Write private key
    logger.info(f"Writing private key to {key_path}...")
    with open(key_path, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    # Set restrictive permissions on key file
    os.chmod(key_path, 0o600)

    # Write certificate
    logger.info(f"Writing certificate to {cert_path}...")
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    logger.info("Self-signed certificate generated successfully")
    return str(cert_path), str(key_path)


def cert_exists(cert_dir: str = "/etc/spaxiom/certs") -> bool:
    """Check if SSL certificate files exist.

    Args:
        cert_dir: Directory containing cert.pem and key.pem

    Returns:
        True if both files exist
    """
    cert_path = Path(cert_dir) / "cert.pem"
    key_path = Path(cert_dir) / "key.pem"
    return cert_path.exists() and key_path.exists()


def get_cert_info(cert_path: str) -> dict:
    """Get information about a certificate.

    Args:
        cert_path: Path to certificate file

    Returns:
        Dictionary with certificate info

    Raises:
        ImportError: If cryptography package is not installed
        FileNotFoundError: If certificate file doesn't exist
    """
    if not HAS_CRYPTOGRAPHY:
        raise ImportError("cryptography package required")

    with open(cert_path, "rb") as f:
        cert_data = f.read()

    cert = x509.load_pem_x509_certificate(cert_data, default_backend())

    return {
        "subject": cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "serial_number": cert.serial_number,
        "not_valid_before": cert.not_valid_before_utc.isoformat(),
        "not_valid_after": cert.not_valid_after_utc.isoformat(),
        "is_expired": datetime.now(timezone.utc) > cert.not_valid_after_utc,
        "days_until_expiry": (
            cert.not_valid_after_utc - datetime.now(timezone.utc)
        ).days,
    }


def validate_cert(cert_path: str, key_path: str) -> Tuple[bool, str]:
    """Validate that certificate and key match.

    Args:
        cert_path: Path to certificate file
        key_path: Path to private key file

    Returns:
        Tuple of (is_valid, message)
    """
    if not HAS_CRYPTOGRAPHY:
        return False, "cryptography package not installed"

    try:
        with open(cert_path, "rb") as f:
            cert_data = f.read()
        with open(key_path, "rb") as f:
            key_data = f.read()

        cert = x509.load_pem_x509_certificate(cert_data, default_backend())
        key = serialization.load_pem_private_key(
            key_data, password=None, backend=default_backend()
        )

        # Check if key matches certificate
        cert_public_key = cert.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        key_public_key = key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        if cert_public_key != key_public_key:
            return False, "Certificate and key do not match"

        # Check expiration
        if datetime.now(timezone.utc) > cert.not_valid_after_utc:
            return False, "Certificate has expired"

        return True, "Certificate is valid"

    except Exception as e:
        return False, f"Validation error: {str(e)}"


def create_ssl_context(
    cert_path: str,
    key_path: str,
    verify_mode: ssl.VerifyMode = ssl.CERT_NONE,
) -> ssl.SSLContext:
    """Create an SSL context for the server.

    Args:
        cert_path: Path to certificate file
        key_path: Path to private key file
        verify_mode: Client certificate verification mode

    Returns:
        Configured SSLContext
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    context.verify_mode = verify_mode

    # Set minimum TLS version
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    return context


def ensure_certs(cert_dir: str = "/etc/spaxiom/certs") -> Tuple[str, str]:
    """Ensure SSL certificates exist, generating if needed.

    Args:
        cert_dir: Directory for certificates

    Returns:
        Tuple of (cert_path, key_path)
    """
    cert_path = os.path.join(cert_dir, "cert.pem")
    key_path = os.path.join(cert_dir, "key.pem")

    if cert_exists(cert_dir):
        # Validate existing certs
        is_valid, message = validate_cert(cert_path, key_path)
        if is_valid:
            logger.info(f"Using existing SSL certificate: {message}")
            return cert_path, key_path
        else:
            logger.warning(f"Existing certificate invalid: {message}")
            logger.info("Generating new certificate...")

    # Generate new certificate
    return generate_self_signed_cert(output_dir=cert_dir)
