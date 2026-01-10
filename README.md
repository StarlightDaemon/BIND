# BIND - Book Indexing Network Daemon

[![Version](https://img.shields.io/badge/version-1.1-blue.svg)](https://github.com/StarlightDaemon/BIND/releases/tag/v1.1.0)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Proxmox](https://img.shields.io/badge/proxmox-ready-orange.svg)](install/install.sh)

**v1.1 Release** - Production-ready audiobook metadata archival with hybrid Cloudflare defense. Stable, battle-tested, and ready for long-term deployment.

## Features

- 📚 **Archival & Preservation** - Long-term backup of audiobook metadata with daily file rotation
- 🤖 **Automated Daemon** - Runs every 60 minutes collecting new releases
- 🧲 **Magnet Link Generation** - Complete magnet URIs with comprehensive tracker lists
- 📡 **RSS 2.0 Feed** - Valid XML feed compatible with all torrent clients
- 🌐 **Web UI** - Beautiful gradient interface to view collected magnets
- 🛡️ **Cloudflare Resistant** - Multi-layer defense against blocking and rate limits
- ♻️ **Zero Maintenance** - Self-healing with auto-cleanup and deduplication
- 🐳 **Easy Deployment** - One-line Proxmox installer, Docker support

## Deployment

Runs on any Linux system with Python 3. Tested on Proxmox LXC containers and works with all RSS-capable torrent clients.

> **⚠️ Security Note**: BIND has no authentication and is designed for **private LAN use only**. Do not expose port 5000 to the internet. If external access is needed, use a reverse proxy with authentication (nginx, Caddy, Cloudflare Tunnel).

## 🚀 Installation

### Proxmox LXC (Recommended)

The easiest and most reliable way to deploy BIND is through our **automated Proxmox LXC installer**. This single command creates a fully isolated container, installs all dependencies, and configures BIND for production use.

**One-Line Installation:**
```bash
bash <(curl -sL https://raw.githubusercontent.com/StarlightDaemon/BIND/main/scripts/install-proxmox-lxc.sh)
```

**What This Does:**
1. ✅ Creates a new LXC container with Ubuntu
2. ✅ Prompts for configuration (Container ID, hostname, RAM, disk, IP address)
3. ✅ Installs Python 3, Git, and all BIND dependencies
4. ✅ Configures systemd services for auto-start
5. ✅ Displays your Web UI and RSS feed URLs

**Installation Time:** ~3 minutes  
**Default Resources:** 512MB RAM, 4GB disk, 1 CPU core

**After Installation:**
- 📡 **RSS Feed**: `http://YOUR-CONTAINER-IP:5000/feed.xml`
- 🌐 **Web UI**: `http://YOUR-CONTAINER-IP:5000/`
- 📊 **View Logs**: `pct exec <CTID> -- journalctl -u bind -f`
- 🔧 **Enter Container**: `pct enter <CTID>`

> **Note**: Requires Proxmox VE with an Ubuntu 22.04/24.04 template. Download one with:
> ```bash
> pveam update && pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst
> ```

---

<details>
<summary><b>📦 Alternative: Already Have a Container/VM?</b></summary>

If you already have an existing LXC container, VM, or bare-metal Debian/Ubuntu system:

**Option 1: Simple Install** (uses defaults)
```bash
bash <(curl -sL https://raw.githubusercontent.com/StarlightDaemon/BIND/main/scripts/install.sh)
```

**Option 2: Interactive Install** (custom configuration)
```bash
bash <(curl -sL https://raw.githubusercontent.com/StarlightDaemon/BIND/main/scripts/install-interactive.sh)
```


<details>
<summary><b>🐳 Docker Installation</b></summary>

```bash
git clone https://github.com/StarlightDaemon/BIND.git
cd BIND
docker-compose up -d
```

</details>

<details>
<summary><b>⚙️ Manual Installation</b></summary>

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

</details>

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
- **[Architecture](docs/ARCHITECTURE.md)** - System design and data flow diagrams
- **[FAQ](docs/FAQ.md)** - Frequently asked questions
- **[Roadmap](docs/ROADMAP.md)** - Future enhancements and features
- **[Releases](docs/RELEASES.md)** - v1.0 release notes and changelog
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
│   │   └── scraper.py      # Scraper with Hybrid Waterfall (cloudscraper -> curl_cffi)
│   ├── bind.py             # Daemon with Circuit Breaker & Deduplication
│   └── rss_server.py       # RSS + Web UI
├── deployment/
│   ├── bind.service        # Systemd daemon service
│   └── bind-rss.service    # Systemd RSS service
├── scripts/
│   └── install.sh          # One-line installer
└── requirements.txt        # Pinned dependencies
```

</details>

<details>
<summary><b>⚙️ Configuration (Environment Variables)</b></summary>

BIND is configured via environment variables in `bind.service` or `bind-rss.service`:

| Variable | Default | Description |
|----------|---------|-------------|
| `BIND_PROXY` | `None` | Optional HTTP/SOCKS5 proxy (e.g., `socks5://user:pass@host:1080`) |
| `ABB_URL` | `http://audiobookbay.lu` | Target domain (change if site moves) |
| `BASE_URL` | Auto-detected | Override RSS feed base URL |
| `MAGNETS_DIR` | `/opt/bind/magnets` | Storage directory for magnet files |
| `CIRCUIT_BREAKER_THRESHOLD` | `3` | Failures before scraper pauses |
| `CIRCUIT_BREAKER_COOLDOWN` | `300` | Seconds to wait after pausing |

</details>
</details>

---

## Legal

**License**: MIT - For educational, archival, and preservation purposes.

### What BIND Does
- ✅ Archives publicly available metadata for digital preservation
- ✅ Creates local backups of torrent magnet links
- ✅ Supports audiobook collection management
- ✅ Stores metadata only (no copyrighted content)

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
