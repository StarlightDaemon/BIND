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
    cleanup_failed_container
    exit 1
}

cleanup_failed_container() {
    if [ -n "$CTID" ] && pct status $CTID &> /dev/null; then
        echo ""
        echo -e "${YW}Installation failed - container $CTID was created but setup failed${CL}"
        echo ""
        read -p "Remove broken container $CTID? (y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            msg_info "Removing container $CTID..."
            pct stop $CTID 2>/dev/null || true
            pct destroy $CTID 2>/dev/null || true
            msg_ok "Container removed"
        else
            msg_info "Container $CTID left for debugging"
            msg_info "To remove later: pct destroy $CTID"
        fi
    fi
}

###############################################################################
# Prerequisites Check
###############################################################################
check_prerequisites() {
    # Check if running on Proxmox
    if ! command -v pct &> /dev/null; then
        msg_error "This script must be run on a Proxmox VE host (pct command not found)"
    fi
    
    # Check if running as root
    if [[ $(id -u) -ne 0 ]]; then
        msg_error "This script must be run as root (try: sudo bash install.sh)"
    fi
    
    # Check internet connectivity
    if ! ping -c 1 8.8.8.8 &> /dev/null; then
        msg_error "No internet connection. Please check network settings."
    fi
}

check_prerequisites

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

###############################################################################
# Network Configuration
###############################################################################
echo ""
read -p "Network type - DHCP or Static? (dhcp/static) [dhcp]: " NET_TYPE
NET_TYPE=${NET_TYPE:-dhcp}

if [[ $NET_TYPE == "static" ]]; then
    read -p "Enter IP address with CIDR (e.g., 192.168.1.100/24): " STATIC_IP
    read -p "Enter Gateway (e.g., 192.168.1.1): " GATEWAY
    NET_CONFIG="name=eth0,bridge=vmbr0,ip=$STATIC_IP,gw=$GATEWAY"
    NET_DISPLAY="Static: $STATIC_IP (Gateway: $GATEWAY)"
else
    NET_CONFIG="name=eth0,bridge=vmbr0,ip=dhcp"
    NET_DISPLAY="DHCP"
fi

###############################################################################
# Storage Detection
###############################################################################
msg_info "Detecting available storage..."

# Try to find local-lvm first (most common)
if pvesm status | grep -q "local-lvm"; then
    STORAGE="local-lvm"
    msg_ok "Using storage: local-lvm"
else
    # Fallback: find first available storage
    STORAGE=$(pvesm status | awk 'NR>1 {print $1; exit}')
    if [ -z "$STORAGE" ]; then
        msg_error "No storage found. Please check Proxmox storage configuration."
    fi
    msg_ok "Using storage: $STORAGE (local-lvm not found, using fallback)"
fi

echo ""
msg_info "Configuration Summary:"
echo "  Container ID: $CTID"
echo "  Hostname: $HOSTNAME"
echo "  Disk: ${DISK_SIZE}GB"
echo "  RAM: ${RAM}MB"
echo "  Cores: $CORES"
echo "  Network: $NET_DISPLAY"
echo "  Storage: $STORAGE"
echo "  RSS Feed Port: $FEED_PORT"
echo ""

read -p "Proceed with installation? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    msg_error "Installation cancelled"
fi

###############################################################################
# Detect or Download Debian Template
###############################################################################
msg_info "Checking for Debian template..."

# Find existing Debian 12 template
TEMPLATE=$(pveam available -section system | grep -o "debian-12-standard.*amd64.tar.zst" | sort -V | tail -1)

if [ -z "$TEMPLATE" ]; then
    msg_info "No Debian 12 template found, downloading latest..."
    # Get latest from available list
    TEMPLATE=$(pveam available | grep "debian-12-standard" | grep -o "debian-12-standard.*amd64.tar.zst" | sort -V | tail -1)
    
    if [ -z "$TEMPLATE" ]; then
        msg_error "Could not find Debian 12 template in repository"
    fi
    
    # Download template
    msg_info "Downloading: $TEMPLATE"
    pveam download local "$TEMPLATE"
    
    if [ $? -ne 0 ]; then
        msg_error "Failed to download template"
    fi
    msg_ok "Template downloaded"
else
    msg_ok "Found template: $TEMPLATE"
fi

###############################################################################
# Create LXC Container
###############################################################################
msg_info "Creating LXC container..."

pct create $CTID local:vztmpl/$TEMPLATE \
    --hostname $HOSTNAME \
    --cores $CORES \
    --memory $RAM \
    --swap 512 \
    --storage $STORAGE \
    --rootfs $STORAGE:$DISK_SIZE \
    --net0 $NET_CONFIG \
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

# Suppress verbose output
export DEBIAN_FRONTEND=noninteractive

# Update system
echo "Updating system packages..."
apt-get update -qq > /dev/null 2>&1
apt-get upgrade -y -qq > /dev/null 2>&1

# Install dependencies
echo "Installing dependencies..."
apt-get install -y -qq \
    python3 \
    python3-venv \
    python3-pip \
    git \
    curl > /dev/null 2>&1

# Clone BIND repository
echo "Cloning BIND repository..."
git clone -q https://github.com/StarlightDaemon/BIND.git /opt/bind 2>&1 | grep -v "^Cloning" || true
cd /opt/bind

# Create virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv venv > /dev/null 2>&1

# Activate and install
echo "Installing Python packages..."
source venv/bin/activate
pip install -q --upgrade pip > /dev/null 2>&1
pip install -q -r requirements.txt > /dev/null 2>&1

# Install systemd services
echo "Installing systemd services..."
cp deployment/bind.service /etc/systemd/system/
cp deployment/bind-rss.service /etc/systemd/system/

# Install update script
echo "Installing update script..."
cp update.sh /opt/bind/
chmod +x /opt/bind/update.sh

# Reload and enable
systemctl daemon-reload
systemctl enable bind.service > /dev/null 2>&1
systemctl enable bind-rss.service > /dev/null 2>&1

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
echo "Update BIND:"
echo "  cd /opt/bind && ./update.sh"
echo ""
echo "Logs:"
echo "  journalctl -u bind.service -f"
echo "  journalctl -u bind-rss.service -f"
echo ""
echo "Troubleshooting:"
echo "  systemctl status bind.service"
echo "  systemctl status bind-rss.service"
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
echo ""
msg_info "Update BIND:"
echo "  pct enter $CTID"
echo "  cd /opt/bind && ./update.sh"
echo ""
msg_info "Check Status:"
echo "  systemctl status bind.service      # Check daemon"
echo "  systemctl status bind-rss.service  # Check RSS server"
echo "  journalctl -u bind.service -f     # View logs"
echo ""
msg_info "Add to your torrent client:"
echo "  Feed URL: http://$CONTAINER_IP:5000/feed.xml"
echo ""
