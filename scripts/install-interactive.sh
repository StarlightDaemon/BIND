#!/bin/bash
# BIND - Interactive Installer for Proxmox/Debian/Ubuntu
# Usage: bash <(curl -sL https://raw.githubusercontent.com/StarlightDaemon/BIND/main/scripts/install-interactive.sh)

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${BLUE}[BIND]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
prompt() { echo -e "${YELLOW}[INPUT]${NC} $1"; }

# Check for root
if [ "$EUID" -ne 0 ]; then
  error "Please run as root (sudo bash install-interactive.sh)"
fi

clear
cat << "EOF"
╔══════════════════════════════════════════════╗
║   BIND - Book Indexing Network Daemon       ║
║   Interactive Installation                   ║
╚══════════════════════════════════════════════╝
EOF

echo ""
log "This installer will guide you through the setup process."
echo ""

# Configuration Prompts
prompt "Installation directory? [/opt/bind]"
read -r INSTALL_DIR
INSTALL_DIR=${INSTALL_DIR:-/opt/bind}

prompt "Magnets storage directory? [/opt/bind/magnets]"
read -r MAGNETS_DIR
MAGNETS_DIR=${MAGNETS_DIR:-/opt/bind/magnets}

prompt "Scrape interval in minutes? [60]"
read -r INTERVAL
INTERVAL=${INTERVAL:-60}

prompt "RSS server port? [5050]"
read -r RSS_PORT
RSS_PORT=${RSS_PORT:-5050}

prompt "Enable proxy support? (y/N)"
read -r USE_PROXY
if [[ $USE_PROXY =~ ^[Yy]$ ]]; then
    prompt "Proxy URL (e.g., socks5://user:pass@host:1080):"
    read -r PROXY_URL
fi

prompt "Custom AudioBookBay domain? (leave blank for default)"
read -r ABB_DOMAIN

echo ""
log "Configuration Summary:"
echo "  Install Dir:    $INSTALL_DIR"
echo "  Magnets Dir:    $MAGNETS_DIR"
echo "  Interval:       ${INTERVAL}m"
echo "  RSS Port:       $RSS_PORT"
echo "  Proxy:          ${PROXY_URL:-None}"
echo "  ABB Domain:     ${ABB_DOMAIN:-Default (audiobookbay.lu)}"
echo ""

prompt "Proceed with installation? (Y/n)"
read -r PROCEED
if [[ $PROCEED =~ ^[Nn]$ ]]; then
    log "Installation cancelled."
    exit 0
fi

# 1. Install System Dependencies
log "Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git curl

# 2. Clone/Update Repository
REPO_URL="https://github.com/StarlightDaemon/BIND.git"
if [ -d "$INSTALL_DIR" ]; then
    log "Updating existing installation in $INSTALL_DIR..."
    cd "$INSTALL_DIR"
    git pull
else
    log "Cloning repository to $INSTALL_DIR..."
    git clone -b main "$REPO_URL" "$INSTALL_DIR"
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
./venv/bin/pip install curl_cffi==0.7.4 -q

# 5. Create custom service files
log "Creating systemd services with your configuration..."

# Daemon service
cat > /etc/systemd/system/bind.service << EOFS
[Unit]
Description=BIND - Book Indexing Network Daemon
Documentation=https://github.com/StarlightDaemon/BIND
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment="PYTHONPATH=$INSTALL_DIR"
$([ -n "$PROXY_URL" ] && echo "Environment=\"BIND_PROXY=$PROXY_URL\"")
$([ -n "$ABB_DOMAIN" ] && echo "Environment=\"ABB_URL=$ABB_DOMAIN\"")
ExecStart=$INSTALL_DIR/venv/bin/python -m src.bind daemon --interval $INTERVAL --output-dir $MAGNETS_DIR
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOFS

# RSS service
cat > /etc/systemd/system/bind-rss.service << EOFS
[Unit]
Description=BIND RSS Feed Server
Documentation=https://github.com/StarlightDaemon/BIND
After=network.target bind.service

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment="PYTHONPATH=$INSTALL_DIR"
Environment="FLASK_ENV=production"
Environment="MAGNETS_DIR=$MAGNETS_DIR"
Environment="PORT=$RSS_PORT"
ExecStart=$INSTALL_DIR/venv/bin/python -m src.rss_server
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOFS

# 6. Reload systemd
systemctl daemon-reload

# 7. Enable and Start Services
log "Starting services..."
systemctl enable bind bind-rss
systemctl restart bind bind-rss

# 8. Final Status Check
log "Verifying installation..."
sleep 2
if systemctl is-active --quiet bind && systemctl is-active --quiet bind-rss; then
    IP=$(hostname -I | cut -d' ' -f1)
    
    echo ""
    success "BIND installed and running successfully!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  📡 RSS Feed:    http://$IP:$RSS_PORT/feed.xml"
    echo "  🌐 Web UI:      http://$IP:$RSS_PORT/"
    echo "  📂 Magnets:     $MAGNETS_DIR"
    echo "  ⏱️  Interval:    ${INTERVAL}m"
    echo ""
    echo "  📊 Daemon Logs: journalctl -u bind -f"
    echo "  📊 RSS Logs:    journalctl -u bind-rss -f"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    error "Services failed to start. Check logs: journalctl -u bind -n 20"
fi
