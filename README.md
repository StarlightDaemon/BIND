# BIND - Book Indexing Network Daemon

[![Version](https://img.shields.io/badge/version-1.0-blue.svg)](https://github.com/StarlightDaemon/BIND/releases/tag/v1.0)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Proxmox](https://img.shields.io/badge/proxmox-ready-orange.svg)](install/install.sh)

**v1.0 Release** - Automated audiobook metadata archival system. Stable, tested, and ready to use.

## Features

- 📚 **Archival & Preservation** - Long-term backup of audiobook metadata with daily file rotation
- 🤖 **Automated Daemon** - Runs every 60 minutes collecting new releases
- 🧲 **Magnet Link Generation** - Complete magnet URIs with comprehensive tracker lists
- 📡 **RSS 2.0 Feed** - Valid XML feed compatible with all torrent clients
- 🌐 **Web UI** - Beautiful gradient interface to view collected magnets
- 🔍 **Health Monitoring** - JSON endpoint for system status
- 🐳 **Easy Deployment** - One-click Proxmox installer, Docker support

## Deployment

Runs on any Linux system with Python 3. Tested on Proxmox LXC containers and works with all RSS-capable torrent clients.

## Quick Start

### Proxmox LXC (Recommended)
```bash
bash -c "$(wget -qLO - https://raw.githubusercontent.com/StarlightDaemon/BIND/main/install/install.sh)"
```

**Installation takes ~2 minutes** and creates:
- Container with 4GB disk, 512MB RAM, 1 CPU core
- Auto-start on boot
- RSS feed at `http://CONTAINER-IP:5000/feed.xml`
- Web UI at `http://CONTAINER-IP:5000/`

### Docker
```bash
git clone https://github.com/StarlightDaemon/BIND.git
cd BIND
docker-compose up -d
```

### Manual Installation
```bash
git clone https://github.com/StarlightDaemon/BIND.git
cd BIND
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run daemon (collects magnets every 60 minutes)
python -m src.bind daemon --interval 60 --output-dir magnets/

# Run RSS server (separate terminal)
python -m src.rss_server
```

## Updating BIND

### Automatic Update (Recommended)

```bash
pct enter <container-id>
cd /opt/bind
./update.sh
```

The update script will:
- ✅ Check for updates
- ✅ Show what's new
- ✅ Backup current version
- ✅ Update code and dependencies
- ✅ Restart services
- ✅ Verify everything works
- ✅ Rollback on failure

### Manual Update

```bash
pct enter <container-id>
cd /opt/bind
git pull
source venv/bin/activate
pip install -r requirements.txt
systemctl restart bind.service bind-rss.service
```

---

## Documentation

- **[Usage Guide](docs/USAGE.md)** - RSS setup, storage info, configuration
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Design System](docs/BIND_IMPLEMENTATION_GUIDE.md)** - Web UI theming reference

---

<details>
<summary><b>📦 Dependencies</b></summary>

BIND uses only 6 carefully chosen dependencies, totaling ~50MB installed:

| Package | Size | Purpose |
|---------|------|---------|
| **cloudscraper** | ~8MB | Bypasses Cloudflare protection on AudioBookBay |
| **beautifulsoup4** | ~500KB | Parses HTML to extract magnet links |
| **lxml** | ~15MB | Fast XML/HTML parser backend for BeautifulSoup |
| **click** | ~800KB | Command-line interface framework |
| **schedule** | ~50KB | Lightweight daemon scheduling (cron alternative) |
| **flask** | ~3MB | RSS server and web UI |

**Total installed size**: ~50MB (including dependencies)  
**Virtual environment**: ~150MB with all packages

All dependencies are actively maintained and essential to BIND's functionality.

</details>

<details>
<summary><b>📁 Project Structure</b></summary>

```
BIND/
├── src/
│   ├── core/
│   │   └── scraper.py      # AudioBookBay scraping engine
│   ├── bind.py             # Main daemon (65 lines)
│   └── rss_server.py       # RSS + Web UI (324 lines)
├── deployment/
│   ├── bind.service        # Systemd daemon service
│   └── bind-rss.service    # Systemd RSS service
├── install/
│   └── install.sh          # Proxmox one-click installer
└── requirements.txt        # 6 dependencies
```

</details>

---

## Legal

**License**: MIT - For educational, archival, and preservation purposes.

### What BIND Does
- ✅ Creates local backups of publicly available metadata
- ✅ Enables personal audiobook library indexing
- ✅ Supports digital preservation efforts
- ✅ Archives magnet links only (no content)

### What BIND Does NOT Do
- ❌ Host, provide, or distribute copyrighted content
- ❌ Store or transmit actual audiobook files
- ❌ Facilitate piracy or copyright infringement
- ❌ Link directly to infringing material

### User Responsibility
Ensure compliance with copyright laws in your jurisdiction. BIND archives metadata only - not copyrighted works. Use only for public domain and legally distributable content.

**By using BIND, you agree to use it solely for legal, educational, and archival purposes in accordance with applicable laws.**

---

## About

**Lightweight and focused**: 531 lines of code, 6 dependencies, minimal resource usage.

BIND archives publicly available audiobook metadata for digital preservation and personal library indexing while respecting intellectual property rights.
