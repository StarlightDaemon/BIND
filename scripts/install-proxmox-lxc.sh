#!/bin/bash

# Copyright (c) 2026 StarlightDaemon
# Author: StarlightDaemon
# License: MIT
# https://github.com/StarlightDaemon/BIND

set -e

# Colors and formatting (tteck style)
YW='\033[33m'
RD='\033[01;31m'
GN='\033[1;92m'
BL='\033[0;34m'
CL='\033[m'
BFR="\\r\\033[K"
HOLD="⏳"
CM="${GN}✓${CL}"
CROSS="${RD}✗${CL}"
WARN="${YW}⚠${CL}"

msg_info() {
    echo -ne " ${HOLD} ${YW}$1...${CL}"
}

msg_ok() {
    echo -e "${BFR} ${CM} ${GN}$1${CL}"
}

msg_error() {
    echo -e "${BFR} ${CROSS} ${RD}$1${CL}"
    exit 1
}

msg_warn() {
    echo -e " ${WARN} ${YW}$1${CL}"
}

# Check prerequisites
if ! command -v pct &> /dev/null; then
    msg_error "This script must be run on a Proxmox host"
fi

if [ "$EUID" -ne 0 ]; then
    msg_error "Please run as root"
fi

# Header
header_info() {
clear
cat <<"EOF"
 ╔══════════════════════════════════════════╗
 ║                                          ║
 ║   ██████╗ ██╗███╗   ██╗██████╗          ║
 ║   ██╔══██╗██║████╗  ██║██╔══██╗         ║
 ║   ██████╔╝██║██╔██╗ ██║██║  ██║         ║
 ║   ██╔══██╗██║██║╚██╗██║██║  ██║         ║
 ║   ██████╔╝██║██║ ╚████║██████╔╝         ║
 ║   ╚═════╝ ╚═╝╚═╝  ╚═══╝╚═════╝          ║
 ║                                          ║
 ╚══════════════════════════════════════════╝
EOF
echo -e "${BL}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CL}"
echo -e " ${GN}Book Indexing Network Daemon${CL}"
echo -e " ${YW}LXC Container Installer v1.1${CL}"
echo -e "${BL}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CL}"
}

header_info
echo ""
sleep 1

# Configuration
echo -e "${GN}Container Configuration${CL}"
echo -e "${BL}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CL}"

echo -ne " ${YW}Container ID?${CL} [${GN}next available${CL}]: "
read -r CTID_INPUT
CTID=${CTID_INPUT:-$(pvesh get /cluster/nextid)}

echo -ne " ${YW}Hostname?${CL} [${GN}bind${CL}]: "
read -r HOSTNAME
HOSTNAME=${HOSTNAME:-bind}

echo -ne " ${YW}Memory (MB)?${CL} [${GN}512${CL}]: "
read -r MEMORY
MEMORY=${MEMORY:-512}

echo -ne " ${YW}Disk Size (GB)?${CL} [${GN}4${CL}]: "
read -r DISK
DISK=${DISK:-4}

echo -ne " ${YW}Network Bridge?${CL} [${GN}vmbr0${CL}]: "
read -r BRIDGE
BRIDGE=${BRIDGE:-vmbr0}

echo -ne " ${YW}IP Address?${CL} [${GN}dhcp${CL}]: "
read -r IP_CONFIG
IP_CONFIG=${IP_CONFIG:-dhcp}

if [ "$IP_CONFIG" != "dhcp" ]; then
    echo -ne " ${YW}Gateway?${CL} [${GN}auto${CL}]: "
    read -r GATEWAY
fi

echo ""
echo -e "${GN}Summary${CL}"
echo -e "${BL}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CL}"
echo -e " ${BL}ID:${CL}       $CTID"
echo -e " ${BL}Host:${CL}     $HOSTNAME"
echo -e " ${BL}RAM:${CL}      ${MEMORY}MB"
echo -e " ${BL}Disk:${CL}     ${DISK}GB"
echo -e " ${BL}Network:${CL}  $BRIDGE"
echo -e " ${BL}IP:${CL}       $IP_CONFIG"
[ -n "$GATEWAY" ] && echo -e " ${BL}Gateway:${CL}  $GATEWAY"
echo -e "${BL}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CL}"
echo ""

echo -ne " ${YW}Proceed with installation? (Y/n):${CL} "
read -r PROCEED
if [[ $PROCEED =~ ^[Nn]$ ]]; then
    msg_error "Installation cancelled"
fi

echo ""
echo -e "${GN}Starting Installation${CL}"
echo -e "${BL}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CL}"

# Check/download template
msg_info "Checking for Ubuntu template"
TEMPLATE=$(pveam list local 2>/dev/null | grep -E "ubuntu-22.04.*standard" | awk '{print $1}' | head -1)

if [ -z "$TEMPLATE" ]; then
    msg_ok "Template not found - downloading"
    
    msg_info "Updating template list"
    pveam update >/dev/null 2>&1
    msg_ok "Template list updated"
    
    msg_info "Downloading Ubuntu 22.04 (~150MB, 2-3 min)"
    pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst
    msg_ok "Template downloaded"
    
    TEMPLATE=$(pveam list local 2>/dev/null | grep -E "ubuntu-22.04.*standard" | awk '{print $2}' | head -1)
fi

msg_ok "Using: $TEMPLATE"

# Network config
if [ "$IP_CONFIG" = "dhcp" ]; then
    NET_CONFIG="name=eth0,bridge=$BRIDGE,ip=dhcp"
else
    if [ -n "$GATEWAY" ]; then
        NET_CONFIG="name=eth0,bridge=$BRIDGE,ip=$IP_CONFIG,gw=$GATEWAY"
    else
        NET_CONFIG="name=eth0,bridge=$BRIDGE,ip=$IP_CONFIG"
    fi
fi

# Create container
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
    --password "$(openssl rand -base64 32)" >/dev/null 2>&1
msg_ok "Container $CTID created"

# Start container
msg_info "Starting container"
pct start "$CTID"
sleep 5
msg_ok "Container started"

# Install BIND
msg_info "Installing BIND (2-3 minutes)"
pct exec "$CTID" -- bash -c "
    apt-get update -qq
    apt-get install -y -qq python3 python3-venv python3-pip git curl
    git clone -q https://github.com/StarlightDaemon/BIND.git /opt/bind
    cd /opt/bind
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip -q
    ./venv/bin/pip install -r requirements.txt -q
    ./venv/bin/pip install curl_cffi==0.7.4 -q
    cp deployment/bind.service /etc/systemd/system/
    cp deployment/bind-rss.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable bind bind-rss
    systemctl start bind bind-rss
" >/dev/null 2>&1
msg_ok "BIND installed successfully"

# Get IP
sleep 2
CONTAINER_IP=$(pct exec "$CTID" -- hostname -I | awk '{print $1}')

# Success message
echo ""
echo -e "${GN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CL}"
echo -e "${GN}          Installation Complete!${CL}"
echo -e "${GN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CL}"
echo ""
echo -e " ${BL}Container:${CL}  $CTID ($HOSTNAME)"
echo -e " ${BL}IP:${CL}         $CONTAINER_IP"
echo ""
echo -e " ${GN}📡 RSS Feed:${CL}   http://$CONTAINER_IP:5000/feed.xml"
echo -e " ${GN}🌐 Web UI:${CL}     http://$CONTAINER_IP:5000/"
echo ""
echo -e "${YW}Quick Commands:${CL}"
echo -e " pct enter $CTID                 # Enter container"
echo -e " pct exec $CTID -- journalctl -u bind -f  # View logs"
echo -e " pct stop $CTID                  # Stop container"
echo ""
echo -e "${GN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CL}"
