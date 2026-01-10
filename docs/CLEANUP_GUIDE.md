# 🧹 BIND Cleanup & Reinstall Guide

## Problem
You accidentally installed BIND on your Proxmox **host** instead of in an LXC container.

## Solution (2 Steps)

### Step 1: Clean Up Host Installation
Run this on your Proxmox host:
```bash
bash <(curl -sL https://raw.githubusercontent.com/StarlightDaemon/BIND/main/scripts/cleanup-proxmox-host.sh)
```

This comprehensive cleanup script will:
- Stop BIND services
- Remove systemd service files
- Delete `/opt/bind` directory
- **Backup** any magnets to `/root/bind_magnets_backup_*/`

**After cleanup, remove the backup** (if you don't need the magnets):
```bash
rm -rf /root/bind_magnets_backup_*
```

### Step 2: Install in LXC Container (Proper Way)
Run this on your Proxmox host:
```bash
bash <(curl -sL https://raw.githubusercontent.com/StarlightDaemon/BIND/main/scripts/install-proxmox-lxc.sh)
```

This will:
- Create a new LXC container
- Prompt for configuration (ID, hostname, memory, disk, IP)
- Install BIND inside the container automatically
- Start everything and show you the access URL

---

## What the New Script Does

The `install-proxmox-lxc.sh` script:
1. ✅ Creates an LXC container (Ubuntu-based)
2. ✅ Configures networking (DHCP or static IP)
3. ✅ Installs BIND inside the container
4. ✅ Sets up systemd services
5. ✅ Shows you the Web UI URL

This is the proper way to deploy BIND on Proxmox!
