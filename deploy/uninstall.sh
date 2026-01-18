#!/bin/bash
#
# Spaxiom Edge Uninstallation Script
#
# This script removes Spaxiom Edge from the system.
# Run with sudo: sudo ./uninstall.sh
#

set -e

# Configuration
INSTALL_DIR="/opt/spaxiom"
DATA_DIR="/var/lib/spaxiom"
LOG_DIR="/var/log/spaxiom"
CONFIG_DIR="/etc/spaxiom"
SERVICE_USER="spaxiom"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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

echo "========================================"
echo "Spaxiom Edge Uninstallation"
echo "========================================"
echo ""

# Confirm uninstallation
read -p "Are you sure you want to uninstall Spaxiom Edge? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "Uninstallation cancelled"
    exit 0
fi

# Ask about data
read -p "Do you want to remove all data (database, logs)? [y/N] " -n 1 -r
echo
REMOVE_DATA=$REPLY

# Stop service if running
log_info "Stopping Spaxiom service..."
systemctl stop spaxiom 2>/dev/null || true

# Disable service
log_info "Disabling Spaxiom service..."
systemctl disable spaxiom 2>/dev/null || true

# Remove service file
log_info "Removing systemd service..."
rm -f /etc/systemd/system/spaxiom.service
systemctl daemon-reload

# Remove installation directory
log_info "Removing installation directory..."
rm -rf $INSTALL_DIR

# Remove data if requested
if [[ $REMOVE_DATA =~ ^[Yy]$ ]]; then
    log_info "Removing data directory..."
    rm -rf $DATA_DIR
    
    log_info "Removing log directory..."
    rm -rf $LOG_DIR
    
    log_info "Removing config directory..."
    rm -rf $CONFIG_DIR
else
    log_info "Keeping data directories:"
    echo "  Data:   $DATA_DIR"
    echo "  Logs:   $LOG_DIR"
    echo "  Config: $CONFIG_DIR"
fi

# Remove user (optional)
read -p "Do you want to remove the spaxiom system user? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Removing system user..."
    userdel $SERVICE_USER 2>/dev/null || true
fi

echo ""
log_info "Spaxiom Edge has been uninstalled"
