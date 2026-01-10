#!/bin/bash
# BIND Proxmox Host Cleanup Script
# Removes BIND installation from Proxmox host and any test containers

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  BIND Proxmox Host Cleanup Script         ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo ""

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}✗ Please run as root${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Running as root${NC}"
echo ""

# 1. Stop and disable BIND services on host
echo -e "${BLUE}[1/6]${NC} Stopping BIND services on host..."
systemctl stop bind bind-rss 2>/dev/null && echo -e "${GREEN}  ✓ Services stopped${NC}" || echo -e "${YELLOW}  ⚠ No services running${NC}"
systemctl disable bind bind-rss 2>/dev/null && echo -e "${GREEN}  ✓ Services disabled${NC}" || echo -e "${YELLOW}  ⚠ No services to disable${NC}"

# 2. Remove systemd service files
echo -e "${BLUE}[2/6]${NC} Removing systemd service files..."
if [ -f /etc/systemd/system/bind.service ] || [ -f /etc/systemd/system/bind-rss.service ]; then
    rm -f /etc/systemd/system/bind.service
    rm -f /etc/systemd/system/bind-rss.service
    systemctl daemon-reload
    echo -e "${GREEN}  ✓ Service files removed${NC}"
else
    echo -e "${YELLOW}  ⚠ No service files found${NC}"
fi

# 3. Remove /opt/bind directory (with backup option)
echo -e "${BLUE}[3/6]${NC} Removing /opt/bind directory..."
if [ -d /opt/bind ]; then
    # Check if magnets directory exists and has files
    if [ -d /opt/bind/magnets ] && [ "$(ls -A /opt/bind/magnets 2>/dev/null)" ]; then
        BACKUP_DIR="/root/bind_host_cleanup_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        cp -r /opt/bind/magnets "$BACKUP_DIR/"
        echo -e "${YELLOW}  ⚠ Backed up magnets to: $BACKUP_DIR${NC}"
    fi
    rm -rf /opt/bind
    echo -e "${GREEN}  ✓ /opt/bind removed${NC}"
else
    echo -e "${YELLOW}  ⚠ /opt/bind not found${NC}"
fi

# 4. Remove old backup directories
echo -e "${BLUE}[4/6]${NC} Checking for old backup directories..."
BACKUP_COUNT=$(find /root -maxdepth 1 -type d -name "bind_magnets_backup_*" 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}  Found $BACKUP_COUNT backup directories:${NC}"
    find /root -maxdepth 1 -type d -name "bind_magnets_backup_*" 2>/dev/null
    echo ""
    echo -ne "${YELLOW}  Remove these? (y/N): ${NC}"
    read -r REMOVE_BACKUPS
    if [[ $REMOVE_BACKUPS =~ ^[Yy]$ ]]; then
        rm -rf /root/bind_magnets_backup_*
        echo -e "${GREEN}  ✓ Backup directories removed${NC}"
    else
        echo -e "${BLUE}  ⓘ Keeping backup directories${NC}"
    fi
else
    echo -e "${YELLOW}  ⚠ No backup directories found${NC}"
fi

# 5. List any BIND containers
echo -e "${BLUE}[5/6]${NC} Checking for BIND containers..."
BIND_CONTAINERS=$(pct list 2>/dev/null | grep -i bind | awk '{print $1}' || true)
if [ -n "$BIND_CONTAINERS" ]; then
    echo -e "${YELLOW}  Found BIND containers:${NC}"
    pct list | grep -i bind
    echo ""
    echo -ne "${YELLOW}  Remove these containers? (y/N): ${NC}"
    read -r REMOVE_CT
    if [[ $REMOVE_CT =~ ^[Yy]$ ]]; then
        for CT in $BIND_CONTAINERS; do
            echo -e "${BLUE}  Stopping container $CT...${NC}"
            pct stop "$CT" 2>/dev/null || true
            sleep 2
            echo -e "${BLUE}  Destroying container $CT...${NC}"
            pct destroy "$CT"
            echo -e "${GREEN}  ✓ Container $CT removed${NC}"
        done
    else
        echo -e "${BLUE}  ⓘ Keeping containers${NC}"
    fi
else
    echo -e "${YELLOW}  ⚠ No BIND containers found${NC}"
fi

# 6. Clean up /tmp
echo -e "${BLUE}[6/6]${NC} Cleaning up temporary files..."
rm -rf /tmp/BIND 2>/dev/null && echo -e "${GREEN}  ✓ /tmp/BIND removed${NC}" || echo -e "${YELLOW}  ⚠ No temp files${NC}"
rm -f /tmp/test-lxc-create.sh /tmp/fix-template.sh 2>/dev/null

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Cleanup Complete!                 ║${NC}"
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo ""
echo -e "${BLUE}Summary:${NC}"
echo -e "  • BIND services removed from host"
echo -e "  • Systemd service files deleted"
echo -e "  • /opt/bind directory cleaned"
echo -e "  • Container check completed"
echo ""
echo -e "${GREEN}Your Proxmox host is now clean!${NC}"
echo ""
