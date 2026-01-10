#!/bin/bash
# BIND Cleanup Script - Remove Installation from Proxmox Host
# Run this on your Proxmox host to remove BIND

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}BIND Cleanup - Removing from Proxmox Host${NC}"
echo ""

# 1. Stop services
echo -e "${GREEN}[1/4]${NC} Stopping BIND services..."
systemctl stop bind bind-rss 2>/dev/null || true

# 2. Disable services
echo -e "${GREEN}[2/4]${NC} Disabling services..."
systemctl disable bind bind-rss 2>/dev/null || true

# 3. Remove service files
echo -e "${GREEN}[3/4]${NC} Removing systemd service files..."
rm -f /etc/systemd/system/bind.service
rm -f /etc/systemd/system/bind-rss.service
systemctl daemon-reload

# 4. Remove installation directory
echo -e "${GREEN}[4/4]${NC} Removing /opt/bind directory..."
if [ -d "/opt/bind" ]; then
    # Backup magnets if they exist
    if [ -d "/opt/bind/magnets" ] && [ "$(ls -A /opt/bind/magnets)" ]; then
        BACKUP_DIR="/root/bind_magnets_backup_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        cp -r /opt/bind/magnets/* "$BACKUP_DIR/" || true
        echo -e "${YELLOW}  → Magnets backed up to: $BACKUP_DIR${NC}"
    fi
    
    rm -rf /opt/bind
fi

echo ""
echo -e "${GREEN}✓ BIND removed from Proxmox host${NC}"
echo ""
echo "Next step: Run the Proxmox LXC installer to create a proper container"
echo "  bash <(curl -sL https://raw.githubusercontent.com/StarlightDaemon/BIND/main/scripts/install-proxmox-lxc.sh)"
