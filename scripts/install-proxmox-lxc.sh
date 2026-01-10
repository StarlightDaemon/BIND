#!/bin/bash

# Copyright (c) 2026 StarlightDaemon
# Author: StarlightDaemon
# License: MIT
# https://github.com/StarlightDaemon/BIND

set -e

# Colors (Proxmox Helper Scripts style)
YW='\033[33m' # Yellow
RD='\033[01;31m' # Red  
GN='\033[1;92m' # Green
CL='\033[m' # Clear
BFR="\\r\\033[K"
HOLD="⏳"
CM="${GN}✓${CL}"
CROSS="${RD}✗${CL}"

msg_info() {
    echo -ne " ${HOLD} ${YW}$1...${CL}"
}

msg_ok() {
    echo -e "${BFR} ${CM} ${GN}$1${CL}"
}

msg_error() {
    echo -e "${BFR} ${CROSS} ${RD}$1${CL}"
}

# Check if running on Proxmox
if ! command -v pct &> /dev/null; then
    msg_error "This script must be run on a Proxmox host"
    exit 1
fi

# Check for root
if [ "$EUID" -ne 0 ]; then
    msg_error "Please run as root"
    exit 1
fi

header_info() {
clear
cat <<"EOF"
    ____  ______   ________ 
   / __ )/  _/ | / / __ \ \
  / __  |/ //    / / / / /
 / /_/ // // /|  / /_/ /  
/_____/___/_/ |_/_____/   
                          
Book Indexing Network Daemon
LXC Container Installer
EOF
}

header_info
echo -e "\n ${YW}Loading...${CL}"
sleep 1

# Configuration with prompts
prompt "LXC Container ID? [default: next available]"
read -r CTID_INPUT
if [ -z "$CTID_INPUT" ]; then
    CTID=$(pvesh get /cluster/nextid)
else
    CTID="$CTID_INPUT"
fi

prompt "Container hostname? [bind]"
read -r HOSTNAME
HOSTNAME=${HOSTNAME:-bind}

prompt "Memory (MB)? [512]"
read -r MEMORY
MEMORY=${MEMORY:-512}

prompt "Disk size (GB)? [4]"
read -r DISK
DISK=${DISK:-4}

prompt "Network bridge? [vmbr0]"
read -r BRIDGE
BRIDGE=${BRIDGE:-vmbr0}

prompt "IP address (CIDR) or 'dhcp'? [dhcp]"
read -r IP_CONFIG
IP_CONFIG=${IP_CONFIG:-dhcp}

prompt "Gateway IP? [leave blank for DHCP]"
read -r GATEWAY

echo ""
log "Configuration Summary:"
echo "  Container ID:   $CTID"
echo "  Hostname:       $HOSTNAME"
echo "  Memory:         ${MEMORY}MB"
echo "  Disk:           ${DISK}GB"
echo "  Bridge:         $BRIDGE"
echo "  IP:             $IP_CONFIG"
echo "  Gateway:        ${GATEWAY:-auto}"
echo ""

# Find or download Ubuntu template
msg_info "Checking for Ubuntu template"
TEMPLATE=$(pveam list local | grep -E "ubuntu-22.04.*standard" | awk '{print $2}' | head -1)

if [ -z "$TEMPLATE" ]; then
    msg_ok "Ubuntu template not found, downloading now"
    
    msg_info "Updating template list"
    pveam update >/dev/null 2>&1
    msg_ok "Template list updated"
    
    msg_info "Downloading Ubuntu 22.04 template (this may take 2-3 minutes)"
    pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst
    msg_ok "Template downloaded successfully"
    
    # Get the template name again
    TEMPLATE=$(pveam list local | grep -E "ubuntu-22.04.*standard" | awk '{print $2}' | head -1)
fi

msg_ok "Using template: $TEMPLATE"

# Build network config
if [ "$IP_CONFIG" = "dhcp" ]; then
    NET_CONFIG="name=eth0,bridge=$BRIDGE,ip=dhcp"
else
    if [ -n "$GATEWAY" ]; then
        NET_CONFIG="name=eth0,bridge=$BRIDGE,ip=$IP_CONFIG,gw=$GATEWAY"
    else
        NET_CONFIG="name=eth0,bridge=$BRIDGE,ip=$IP_CONFIG"
    fi
fi

# Create LXC Container
msg_info "Creating LXC container $CTID"
pct create "$CTID" "local:vztmpl/$TEMPLATE" \
    --hostname "$HOSTNAME" \
    --memory "$MEMORY" \
    --cores 1 \
    --rootfs "local-lvm:$DISK" \
    --net0 "$NET_CONFIG" \
    --onboot 1 \
    --unprivileged 1 \
    --features nesting=1 \
    --password "$(openssl rand -base64 32)" \
    --ssh-public-keys ~/.ssh/authorized_keys 2>/dev/null || true

success "Container $CTID created"

# Start container
log "Starting container..."
pct start "$CTID"
sleep 5

# Install BIND inside container
log "Installing BIND inside container (this may take 2-3 minutes)..."
pct exec "$CTID" -- bash -c "
    # Update system
    apt-get update -qq
    apt-get install -y -qq python3 python3-venv python3-pip git curl

    # Clone BIND
    git clone -q https://github.com/StarlightDaemon/BIND.git /opt/bind
    cd /opt/bind

    # Setup venv and install dependencies
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip -q
    ./venv/bin/pip install -r requirements.txt -q
    ./venv/bin/pip install curl_cffi==0.7.4 -q

    # Install systemd services
    cp deployment/bind.service /etc/systemd/system/
    cp deployment/bind-rss.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable bind bind-rss
    systemctl start bind bind-rss
"

# Get container IP
sleep 2
CONTAINER_IP=$(pct exec "$CTID" -- hostname -I | awk '{print $1}')

echo ""
success "BIND installed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  📦 Container ID: $CTID"
echo "  🌐 IP Address:   $CONTAINER_IP"
echo "  📡 RSS Feed:     http://$CONTAINER_IP:5000/feed.xml"
echo "  🖥️  Web UI:       http://$CONTAINER_IP:5000/"
echo ""
echo "  🔧 Enter container:  pct enter $CTID"
echo "  📊 View logs:        pct exec $CTID -- journalctl -u bind -f"
echo "  🛑 Stop container:   pct stop $CTID"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
