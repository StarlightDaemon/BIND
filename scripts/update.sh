#!/bin/bash
# BIND Update Script
# https://github.com/StarlightDaemon/BIND

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║           BIND Update Utility                           ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check we're in the right directory
if [ ! -f "/opt/bind/src/bind.py" ]; then
    echo "[ERROR] Must be run from /opt/bind directory"
    echo "Usage: cd /opt/bind && ./update.sh"
    exit 1
fi

# Check for updates
echo "[INFO] Checking for updates..."
cd /opt/bind
git fetch origin main 2>/dev/null

LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "[OK] Already up to date!"
    echo ""
    echo "Current version: $(git log -1 --format='%h - %s')"
    exit 0
fi

echo "[INFO] Updates available!"
echo ""

# Show what's new
echo "Recent changes:"
git log --oneline --decorate HEAD..origin/main | head -10
echo ""

# Confirm update
read -p "Update BIND? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "[INFO] Update cancelled"
    exit 0
fi

# Backup current version
echo "[INFO] Backing up current version..."
BACKUP_TAG="backup-$(date +%Y%m%d-%H%M%S)"
git tag $BACKUP_TAG
echo "[OK] Created backup tag: $BACKUP_TAG"

# Pull updates
echo "[INFO] Pulling updates..."
git pull origin main

# Update Python dependencies
echo "[INFO] Updating dependencies..."
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Restart services
echo "[INFO] Restarting services..."
systemctl restart bind.service
systemctl restart bind-rss.service

# Verify services
sleep 2
if systemctl is-active --quiet bind.service && systemctl is-active --quiet bind-rss.service; then
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║         Update Successful! 🎉                           ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""
    echo "Updated to: $(git log -1 --format='%h - %s')"
    echo ""
    echo "Services:"
    echo "  ✓ bind.service (Daemon)"
    echo "  ✓ bind-rss.service (RSS Server)"
    echo ""
    echo "To rollback: git checkout $BACKUP_TAG && systemctl restart bind.service bind-rss.service"
    echo ""
else
    echo ""
    echo "[ERROR] Services failed to start after update!"
    echo "[INFO] Rolling back to previous version..."
    git checkout $BACKUP_TAG
    systemctl restart bind.service 2>/dev/null || true
    systemctl restart bind-rss.service 2>/dev/null || true
    echo "[OK] Rolled back to: $(git log -1 --format='%h - %s')"
    echo ""
    echo "Please check logs:"
    echo "  journalctl -u bind.service -n 50"
    echo "  journalctl -u bind-rss.service -n 50"
    exit 1
fi
