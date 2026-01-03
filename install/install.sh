#!/usr/bin/env bash

# BIND - Book Indexing Network Daemon
# Proxmox LXC Installer Script
# https://github.com/StarlightDaemon/BIND

###############################################################################
# Color Codes
###############################################################################
YW="\033[33m"
RD="\033[01;31m"
BL="\033[36m"
GN="\033[1;92m"
CL="\033[m"

###############################################################################
# Helper Functions
###############################################################################
msg_info() {
    echo -e "${BL}[INFO]${CL} ${GN}$1${CL}"
}

msg_ok() {
    echo -e "${BL}[OK]${CL} ${GN}$1${CL}"
}

msg_error() {
    echo -e "${RD}[ERROR]${CL} ${RD}$1${CL}"
    exit 1
}

###############################################################################
# Default Configuration
###############################################################################
APP="BIND"
INSTALL_DIR="/opt/bind"
FEED_PORT="5000"

# Auto-increment container ID
CTID=$(pct list | awk 'NR>1 {print $1}' | tail -1)
((CTID++))

# Container defaults
HOSTNAME="bind"
DISK_SIZE="4"
RAM="512"
CORES="1"

###############################################################################
# Welcome Message
###############################################################################
clear
cat << 'EOF'
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   BIND - Book Indexing Network Daemon                   ║
║   Audiobook Metadata Archival System                    ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
EOF

echo ""
msg_info "This script will create a Proxmox LXC container for BIND"
echo ""

###############################################################################
# User Input
###############################################################################
read -p "Enter Container ID [$CTID]: " USER_CTID
CTID=${USER_CTID:-$CTID}

read -p "Enter Hostname [$HOSTNAME]: " USER_HOSTNAME
HOSTNAME=${USER_HOSTNAME:-$HOSTNAME}

read -p "Enter Disk Size in GB [$DISK_SIZE]: " USER_DISK
DISK_SIZE=${USER_DISK:-$DISK_SIZE}

read -p "Enter RAM in MB [$RAM]: " USER_RAM
RAM=${USER_RAM:-$RAM}

read -p "Enter CPU Cores [$CORES]: " USER_CORES
CORES=${USER_CORES:-$CORES}

echo ""
msg_info "Configuration Summary:"
echo "  Container ID: $CTID"
echo "  Hostname: $HOSTNAME"
echo "  Disk: ${DISK_SIZE}GB"
echo "  RAM: ${RAM}MB"
echo "  Cores: $CORES"
echo "  RSS Feed Port: $FEED_PORT"
echo ""

read -p "Proceed with installation? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    msg_error "Installation cancelled"
fi

###############################################################################
# Create LXC Container
###############################################################################
msg_info "Creating LXC container..."

pct create $CTID local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
    --hostname $HOSTNAME \
    --cores $CORES \
    --memory $RAM \
    --swap 512 \
    --storage local-lvm \
    --rootfs local-lvm:$DISK_SIZE \
    --net0 name=eth0,bridge=vmbr0,ip=dhcp \
    --unprivileged 1 \
    --features nesting=1 \
    --onboot 1

if [ $? -eq 0 ]; then
    msg_ok "LXC container created (ID: $CTID)"
else
    msg_error "Failed to create LXC container"
fi

###############################################################################
# Start Container
###############################################################################
msg_info "Starting container..."
pct start $CTID
sleep 5
msg_ok "Container started"

###############################################################################
# Install BIND Inside Container
###############################################################################
msg_info "Installing BIND inside container..."

pct exec $CTID -- bash -c "$(cat <<'INSTALL_SCRIPT'
#!/bin/bash
set -e

# Update system
echo "Updating system packages..."
apt-get update
apt-get upgrade -y

# Install dependencies
echo "Installing dependencies..."
apt-get install -y \
    python3 \
    python3-venv \
    python3-pip \
    git \
    curl

# Clone BIND repository
echo "Cloning BIND repository..."
git clone https://github.com/StarlightDaemon/BIND.git /opt/bind
cd /opt/bind

# Create virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Install systemd services
echo "Installing systemd services..."
cp deployment/bind.service /etc/systemd/system/
cp deployment/bind-rss.service /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Enable services
systemctl enable bind.service
systemctl enable bind-rss.service

# Start services
systemctl start bind.service
systemctl start bind-rss.service

# Get container IP
IP=$(hostname -I | awk '{print $1}')

echo ""
echo "============================================"
echo "BIND Installation Complete!"
echo "============================================"
echo ""
echo "RSS Feed: http://$IP:5000/feed.xml"
echo "Web UI:   http://$IP:5000/"
echo ""
echo "Services:"
echo "  - bind.service     (Daemon)"
echo "  - bind-rss.service (RSS Server)"
echo ""
echo "Logs:"
echo "  journalctl -u bind.service -f"
echo "  journalctl -u bind-rss.service -f"
echo ""

INSTALL_SCRIPT
)"

if [ $? -eq 0 ]; then
    msg_ok "BIND installed successfully"
else
    msg_error "BIND installation failed"
fi

###############################################################################
# Get Container IP
###############################################################################
CONTAINER_IP=$(pct exec $CTID -- hostname -I | awk '{print $1}')

###############################################################################
# Summary
###############################################################################
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║            BIND Installation Complete! 🎉               ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
msg_ok "Container ID: $CTID"
msg_ok "Hostname: $HOSTNAME"
msg_ok "IP Address: $CONTAINER_IP"
echo ""
msg_info "Access Points:"
echo "  📡 RSS Feed: http://$CONTAINER_IP:5000/feed.xml"
echo "  🌐 Web UI:   http://$CONTAINER_IP:5000/"
echo ""
msg_info "Useful Commands:"
echo "  pct enter $CTID                    # Enter container"
echo "  pct stop $CTID                     # Stop container"
echo "  pct start $CTID                    # Start container"
echo "  systemctl status bind.service      # Check daemon status"
echo "  systemctl status bind-rss.service  # Check RSS server status"
echo ""
msg_info "Add to your torrent client:"
echo "  Feed URL: http://$CONTAINER_IP:5000/feed.xml"
echo ""
