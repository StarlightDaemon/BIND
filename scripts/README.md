# BIND Installation Scripts

This directory contains installer scripts for deploying BIND on various platforms.

## 🚀 Primary Installer (Recommended)

### `install-proxmox-lxc.sh`
**One-line Proxmox LXC installer** - Creates container and installs BIND automatically.

**Usage:**
```bash
bash <(curl -sL https://raw.githubusercontent.com/StarlightDaemon/BIND/main/scripts/install-proxmox-lxc.sh)
```

**Features:**
- ✅ Auto-creates LXC container
- ✅ Auto-downloads Ubuntu template if missing
- ✅ Two modes: Default (zero prompts) or Advanced (full customization)
- ✅ Professional tteck-style UI
- ✅ ~3 minute installation

**Default Settings:**
- Container ID: Next available
- Hostname: `bind`
- Memory: 512MB
- Disk: 4GB
- Network: DHCP on vmbr0

---

## 📦 Alternative Installers

### `install.sh`
**Simple installer** for existing containers/VMs or bare-metal systems.

**Usage:**
```bash
bash <(curl -sL https://raw.githubusercontent.com/StarlightDaemon/BIND/main/scripts/install.sh)
```

Uses default settings (60m interval, port 5000, `/opt/bind`).

### `install-interactive.sh`
**Interactive installer** with full customization prompts.

**Usage:**
```bash
bash <(curl -sL https://raw.githubusercontent.com/StarlightDaemon/BIND/main/scripts/install-interactive.sh)
```

Prompts for: install directory, scrape interval, RSS port, proxy settings, custom domain.

---

## 🧹 Utilities

### `cleanup-proxmox-host.sh`
**Comprehensive cleanup script** for removing BIND from Proxmox host.

**Usage:**
```bash
bash <(curl -sL https://raw.githubusercontent.com/StarlightDaemon/BIND/main/scripts/cleanup-proxmox-host.sh)
```

**What it does:**
- Stops and removes BIND services
- Deletes systemd service files
- Removes `/opt/bind` directory (with backup)
- Interactive prompts for old backups and containers

---

## 📝 Which Script Should I Use?

| Scenario | Script | Command |
|----------|--------|---------|
| **Proxmox VE** (fresh install) | `install-proxmox-lxc.sh` | `bash <(curl -sL ...)` |
| **Existing Container/VM** | `install.sh` | `bash <(curl -sL ...)` |
| **Need Customization** | `install-interactive.sh` | `bash <(curl -sL ...)` |
| **Cleanup/Remove** | `cleanup-proxmox-host.sh` | `bash <(curl -sL ...)` |

---

**For more details, see the main [README.md](../README.md)**
