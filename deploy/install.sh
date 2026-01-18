#!/bin/bash
#
# Spaxiom Edge Installation Script
#
# This script installs Spaxiom Edge on a Linux system (Raspberry Pi, Ubuntu, etc.)
# Run with sudo: sudo ./install.sh
#

set -e

# Configuration
INSTALL_DIR="/opt/spaxiom"
DATA_DIR="/var/lib/spaxiom"
LOG_DIR="/var/log/spaxiom"
CONFIG_DIR="/etc/spaxiom"
SERVICE_USER="spaxiom"
PYTHON_VERSION="python3"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root (use sudo)"
    exit 1
fi

# Check for Python 3
if ! command -v $PYTHON_VERSION &> /dev/null; then
    log_error "Python 3 is required but not installed"
    exit 1
fi

PYTHON_VER=$($PYTHON_VERSION --version 2>&1 | cut -d' ' -f2)
log_info "Found Python $PYTHON_VER"

# Check Python version >= 3.8
PYTHON_MAJOR=$($PYTHON_VERSION -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$($PYTHON_VERSION -c "import sys; print(sys.version_info.minor)")
if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 8 ]]; then
    log_error "Python 3.8 or higher is required (found $PYTHON_VER)"
    exit 1
fi

log_info "Starting Spaxiom Edge installation..."

# Create system user if it doesn't exist
if ! id -u $SERVICE_USER &>/dev/null; then
    log_info "Creating system user: $SERVICE_USER"
    useradd --system --no-create-home --shell /bin/false $SERVICE_USER
else
    log_info "User $SERVICE_USER already exists"
fi

# Create directories
log_info "Creating directories..."
mkdir -p $INSTALL_DIR
mkdir -p $DATA_DIR
mkdir -p $LOG_DIR
mkdir -p $CONFIG_DIR

# Set ownership
chown -R $SERVICE_USER:$SERVICE_USER $DATA_DIR
chown -R $SERVICE_USER:$SERVICE_USER $LOG_DIR

# Create virtual environment
log_info "Creating Python virtual environment..."
$PYTHON_VERSION -m venv $INSTALL_DIR/venv

# Upgrade pip
log_info "Upgrading pip..."
$INSTALL_DIR/venv/bin/pip install --upgrade pip

# Install spaxiom
log_info "Installing Spaxiom..."
$INSTALL_DIR/venv/bin/pip install spaxiom

# Verify installation
if $INSTALL_DIR/venv/bin/python -c "import spaxiom.edge" 2>/dev/null; then
    log_info "Spaxiom Edge installed successfully"
else
    log_error "Spaxiom Edge installation verification failed"
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Install systemd service
log_info "Installing systemd service..."
if [[ -f "$SCRIPT_DIR/spaxiom.service" ]]; then
    cp "$SCRIPT_DIR/spaxiom.service" /etc/systemd/system/
else
    log_warn "spaxiom.service not found in script directory, skipping service install"
fi

# Reload systemd
systemctl daemon-reload

# Enable service
log_info "Enabling Spaxiom service..."
systemctl enable spaxiom

# Create default config if it doesn't exist
if [[ ! -f "$CONFIG_DIR/config.yaml" ]]; then
    log_info "Creating default configuration..."
    cat > $CONFIG_DIR/config.yaml << EOF
# Spaxiom Edge Configuration
# See documentation at https://joescanlin.github.io/spaxiom-dsl/

# Logging
log_level: INFO

# API Server
api:
  host: 0.0.0.0
  port: 8080

# Database
database:
  path: /var/lib/spaxiom/spaxiom.db

# Event retention (days)
event_retention_days: 30
EOF
    chown $SERVICE_USER:$SERVICE_USER $CONFIG_DIR/config.yaml
fi

# Add spaxiom user to gpio group (for Raspberry Pi)
if getent group gpio &>/dev/null; then
    log_info "Adding $SERVICE_USER to gpio group..."
    usermod -a -G gpio $SERVICE_USER
fi

# Print success message
echo ""
echo "========================================"
log_info "Spaxiom Edge installation complete!"
echo "========================================"
echo ""
echo "Installation paths:"
echo "  Application: $INSTALL_DIR"
echo "  Data:        $DATA_DIR"
echo "  Logs:        $LOG_DIR"
echo "  Config:      $CONFIG_DIR"
echo ""
echo "To start Spaxiom Edge:"
echo "  sudo systemctl start spaxiom"
echo ""
echo "To check status:"
echo "  sudo systemctl status spaxiom"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u spaxiom -f"
echo ""
echo "Web UI will be available at:"
echo "  http://$(hostname -I | awk '{print $1}'):8080"
echo ""
