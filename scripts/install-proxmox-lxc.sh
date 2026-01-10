#!/bin/bash

# Copyright (c) 2026 BIND Developer
# License: MIT
# https://github.com/StarlightDaemon/BIND

set -e

# Colors (Helper Scripts style)
YW='\033[33m'
RD='\033[01;31m'
GN='\033[1;92m'
BL='\033[0;34m'
CL='\033[m'
BFR="\\r\\033[K"
HOLD="⏳"
CM="${GN}✓${CL}"
CROSS="${RD}✗${CL}"

msg_info() { echo -ne " ${HOLD} ${YW}$1...${CL}"; }
msg_ok() { echo -e "${BFR} ${CM} ${GN}$1${CL}"; }
msg_error() { echo -e "${BFR} ${CROSS} ${RD}$1${CL}"; exit 1; }

# Check prerequisites
if ! command -v pct &> /dev/null; then msg_error "This script must be run on a Proxmox host"; fi
if [ "$EUID" -ne 0 ]; then msg_error "Please run as root"; fi

# Header
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
echo ""

# Simple choice: Default or Advanced
echo -e "${GN}Installation Mode${CL}"
echo -e "${BL}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CL}"
echo -e " ${GN}[1]${CL} Default Settings (Recommended)"
echo -e "     ${BL}→${CL} Next available container ID"
echo -e "     ${BL}→${CL} 512MB RAM, 4GB Disk"
echo -e "     ${BL}→${CL} DHCP networking"
echo ""
echo -e " ${YW}[2]${CL} Advanced (Customize Settings)"
echo ""
echo -ne " ${YW}Select [1/2]:${CL} "
read -r MODE

if [[ $MODE == "2" ]]; then
    # Advanced mode - ask for everything
    echo ""
    echo -e "${YW}Advanced Configuration${CL}"
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
else
    # Default mode - use all defaults
    CTID=$(pvesh get /cluster/nextid)
    HOSTNAME="bind"
    MEMORY=512
    DISK=4
    BRIDGE="vmbr0"
    IP_CONFIG="dhcp"
    GATEWAY=""
fi

# Show configuration
echo ""
echo -e "${GN}Configuration Summary${CL}"
echo -e "${BL}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CL}"
echo -e " ${BL}Container ID:${CL} $CTID"
echo -e " ${BL}Hostname:${CL}     $HOSTNAME"
echo -e " ${BL}Memory:${CL}       ${MEMORY}MB"
echo -e " ${BL}Disk:${CL}         ${DISK}GB"
echo -e " ${BL}Network:${CL}      $BRIDGE ($IP_CONFIG)"
[ -n "$GATEWAY" ] && echo -e " ${BL}Gateway:${CL}      $GATEWAY"
echo -e "${BL}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CL}"
echo ""
echo -ne " ${YW}Proceed? [${GN}Y${CL}/n]: ${CL}"
read -r PROCEED
if [[ $PROCEED =~ ^[Nn]$ ]]; then msg_error "Installation cancelled"; fi

# Start installation
echo ""
echo -e "${GN}Installing BIND${CL}"
echo -e "${BL}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CL}"

# Check/download template
msg_info "Checking for Ubuntu template"
TEMPLATE=$(pveam list local 2>/dev/null | grep -E "ubuntu-22.04.*standard" | awk '{print $1}' | head -1)

if [ -z "$TEMPLATE" ]; then
    msg_ok "Template not found - downloading"
    msg_info "Updating template list"
    pveam update >/dev/null 2>&1
    msg_ok "Template list updated"
    msg_info "Downloading Ubuntu 22.04 (~150MB)"
    pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst
    msg_ok "Template downloaded"
    TEMPLATE=$(pveam list local 2>/dev/null | grep -E "ubuntu-22.04.*standard" | awk '{print $1}' | head -1)
fi
msg_ok "Template ready"

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
msg_info "Creating LXC container"
pct create "$CTID" "$TEMPLATE" \
    --hostname "$HOSTNAME" \
    --memory "$MEMORY" \
    --cores 1 \
    --rootfs "local-lvm:$DISK" \
    --net0 "$NET_CONFIG" \
    --onboot 1 \
    --unprivileged 1 \
    --features nesting=1 >/dev/null 2>&1
msg_ok "LXC container $CTID created"

# Start container
msg_info "Starting container"
pct start "$CTID"
sleep 5
msg_ok "Container started"

# Install BIND
msg_info "Installing BIND (2-3 minutes)"
pct exec "$CTID" -- bash -c "
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq python3 python3-venv python3-pip git curl
    git clone -q https://github.com/StarlightDaemon/BIND.git /opt/bind
    cd /opt/bind
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip -q
    ./venv/bin/pip install -r requirements.txt -q
    cp deployment/bind.service /etc/systemd/system/
    cp deployment/bind-rss.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable bind bind-rss
    systemctl start bind bind-rss
" >/dev/null 2>&1
msg_ok "BIND installed successfully"

# Setup MOTD
msg_info "Configuring login banner"
pct exec "$CTID" -- bash -c "
cat > /etc/motd << 'MOTD_END'
BIND LXC Container

📡 Provided by: BIND Developer | GitHub: https://github.com/StarlightDaemon/BIND

💻 OS: Debian GNU/Linux - Version: 12
🏠 Hostname: $(hostname)
💡 IP Address: $(hostname -I | awk '{print \$1}')

🌐 Web UI:     http://$(hostname -I | awk '{print \$1}'):5000/
📡 RSS Feed:   http://$(hostname -I | awk '{print \$1}'):5000/feed.xml
📂 Magnets:    /opt/bind/magnets/

📊 Status:     journalctl -u bind -f
🔧 Manage:     systemctl status bind bind-rss
MOTD_END
" >/dev/null 2>&1
msg_ok "Login banner configured"

# Set Proxmox Notes
msg_info "Setting Proxmox container notes"
pct set "$CTID" --description "# BIND - Book Indexing Network Daemon

**Status**: Running
**Version**: v1.1.0

## Quick Links
- 🌐 [Web UI](http://$CONTAINER_IP:5000/)
- 📡 [RSS Feed](http://$CONTAINER_IP:5000/feed.xml)
- 📖 [GitHub](https://github.com/StarlightDaemon/BIND)
- 💬 [Discussions](https://github.com/StarlightDaemon/BIND/discussions)
- 🐛 [Issues](https://github.com/StarlightDaemon/BIND/issues)

## Container Info
- **Hostname**: $HOSTNAME
- **IP Address**: $CONTAINER_IP
- **Memory**: ${MEMORY}MB
- **Disk**: ${DISK}GB

## Management Commands
\`\`\`bash
pct enter $CTID
journalctl -u bind -f
systemctl status bind bind-rss
\`\`\`
" >/dev/null 2>&1
msg_ok "Proxmox notes updated"

# Get IP
sleep 2
CONTAINER_IP=$(pct exec "$CTID" -- hostname -I | awk '{print $1}')

# Success
echo ""
echo -e "${GN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CL}"
echo -e "${GN}          ✓ Installation Complete!${CL}"
echo -e "${GN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CL}"
echo ""
echo -e " ${BL}Container:${CL}  $CTID ($HOSTNAME)"
echo -e " ${BL}IP Address:${CL} $CONTAINER_IP"
echo ""
echo -e " ${GN}📡 RSS Feed:${CL}   http://$CONTAINER_IP:5000/feed.xml"
echo -e " ${GN}🌐 Web UI:${CL}     http://$CONTAINER_IP:5000/"
echo ""
echo -e "${YW}Management Commands:${CL}"
echo -e " pct enter $CTID"
echo -e " pct exec $CTID -- journalctl -u bind -f"
echo -e " pct stop $CTID"
echo ""
echo -e "${GN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${CL}"
