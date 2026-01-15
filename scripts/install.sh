#!/bin/bash
# BIND - One-Line Installer for Proxmox/Debian/Ubuntu
# Usage: bash <(curl -sL https://raw.githubusercontent.com/StarlightDaemon/BIND/main/scripts/install.sh)

set -e

# Configuration
REPO_URL="https://github.com/StarlightDaemon/BIND.git"
INSTALL_DIR="/opt/bind"
BRANCH="main"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${BLUE}[BIND]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Check for root
if [ "$EUID" -ne 0 ]; then
  error "Please run as root (sudo bash install.sh)"
fi

log "Starting BIND Installation..."

# 1. Install System Dependencies
log "Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git curl

# 2. Clone/Update Repository
if [ -d "$INSTALL_DIR" ]; then
    log "Updating existing installation in $INSTALL_DIR..."
    cd "$INSTALL_DIR"
    git pull
else
    log "Cloning repository to $INSTALL_DIR..."
    git clone -b "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 3. Setup Python Virtual Environment
log "Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# 4. Install Python Dependencies
log "Installing Python requirements..."
./venv/bin/pip install --upgrade pip -q
./venv/bin/pip install -r requirements.txt -q
# Explicitly install curl_cffi to be safe
./venv/bin/pip install curl_cffi==0.7.4 -q

# 5. Install Systemd Services
log "Configuring systemd services..."
cp -f deployment/bind.service /etc/systemd/system/
cp -f deployment/bind-rss.service /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# 6. Enable and Start Services
log "Starting services..."
systemctl enable bind bind-rss
systemctl restart bind bind-rss

# 7. Final Status Check
log "Verifying installation..."
sleep 2
if systemctl is-active --quiet bind && systemctl is-active --quiet bind-rss; then
    IP=$(hostname -I | cut -d' ' -f1)
    
    echo ""
    success "BIND installed and running successfully!"
    echo "-----------------------------------------------------"
    echo -e "RSS Feed:    http://$IP:5050/feed.xml"
    echo -e "Web UI:      http://$IP:5050/"
    echo -e "Logs:        journalctl -u bind -f"
    echo "-----------------------------------------------------"
else
    error "Services failed to start. Check logs with: journalctl -u bind -n 20"
fi
