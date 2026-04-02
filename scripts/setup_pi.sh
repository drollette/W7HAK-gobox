#!/usr/bin/env bash
# W7HAK Go Box — Raspberry Pi Zero W Setup Script
# Run as root or with sudo on a fresh Raspberry Pi OS Lite image.

set -euo pipefail

# ---------------------------------------------------------------------------
# BEFORE RUNNING THIS SCRIPT:
#   1. Enable I2C via raspi-config:
#        sudo raspi-config → Interface Options → I2C → Enable
#   2. Enable 1-Wire via raspi-config:
#        sudo raspi-config → Interface Options → 1-Wire → Enable
#      (Or manually add "dtoverlay=w1-gpio" to /boot/config.txt)
#   3. Reboot the Pi after making those changes.
# ---------------------------------------------------------------------------

echo "==> Updating package lists..."
apt update

echo "==> Installing system dependencies..."
apt install -y \
    python3-pip \
    i2c-tools \
    python3-smbus

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"


# ---------------------------------------------------------------------------
# Python dependencies
# ---------------------------------------------------------------------------

echo "==> Installing Python dependencies from requirements.txt..."
pip3 install -r "$REPO_DIR/requirements.txt"

# ---------------------------------------------------------------------------
# Install and enable the systemd service
# ---------------------------------------------------------------------------

SERVICE_SRC="$REPO_DIR/systemd/gobox_telemetry.service"
SERVICE_DST="/etc/systemd/system/gobox_telemetry.service"

echo "==> Installing systemd service from $SERVICE_SRC..."
cp "$SERVICE_SRC" "$SERVICE_DST"

# Update ExecStart path to match actual repo location.
# Support both the placeholder template and historical hardcoded paths.
sed -i \
    -e "s|__REPO_DIR__|$REPO_DIR|g" \
    -e "s|/home/pi/goBox|$REPO_DIR|g" \
    -e "s|/home/pi/W7HAK-gobox|$REPO_DIR|g" \
    "$SERVICE_DST"

if ! grep -q "$REPO_DIR/scripts/telemetry.py" "$SERVICE_DST"; then
    echo "[ERROR] Failed to configure ExecStart path in $SERVICE_DST"
    exit 1
fi

systemctl daemon-reload
systemctl enable gobox_telemetry.service
systemctl start gobox_telemetry.service

echo ""
echo "==> Setup complete. Service status:"
systemctl status gobox_telemetry.service --no-pager
