# BIND - Book Indexing Network Daemon

[![CI](https://github.com/StarlightDaemon/BIND/actions/workflows/ci.yml/badge.svg)](https://github.com/StarlightDaemon/BIND/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-1.7.1-blue.svg)](https://github.com/StarlightDaemon/BIND/releases/tag/v1.7.1)
[![Python](https://img.shields.io/badge/python-3.10+-yellow.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Proxmox](https://img.shields.io/badge/proxmox-ready-orange.svg)](scripts/install-proxmox-lxc.sh)

**v1.7.1** — Production-ready audiobook metadata archival with SQLite storage, authentication, and hybrid Cloudflare defense.

## Features

- 📚 **Archival & Preservation** - Long-term backup of audiobook metadata with 90-day retention and automatic pruning
- 🤖 **Automated Daemon** - Runs every 60 minutes collecting new releases
- 🧲 **Magnet Link Generation** - Complete magnet URIs with comprehensive tracker lists
- 📡 **RSS 2.0 Feed** - Valid XML feed compatible with all torrent clients
- 🌐 **Web UI** - Gradient interface with full-text search across collected magnets
- 🔒 **Authentication** - Setup wizard, password protection, and brute-force lockout
- ⚙️ **Settings UI** - Browser-based configuration at `/settings` — no file editing required
- 🗄️ **SQLite Storage** - MagnetStore with FTS5 full-text search; replaces flat-file storage
- 🔁 **Resilient Scraping** - RetryEngine with exponential back-off and circuit breaker
- 🛡️ **Cloudflare Resistant** - Multi-layer defense: curl_cffi → cloudscraper → proxy fallback
- ♻️ **Zero Maintenance** - Self-healing with deduplication and schema monitoring
- 🐳 **Easy Deployment** - One-line Proxmox installer, Docker Hub image

## Deployment

Runs on any Linux system with Python 3. Tested on Proxmox LXC containers and works with all RSS-capable torrent clients.

> **⚠️ Security Note**: BIND includes a built-in authentication system (Setup Wizard, Password Protection, Bruteforce Lockout). However, for maximum security, we still recommend running behind a reverse proxy (nginx, Caddy, Cloudflare Tunnel) if exposing to the public internet.

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
- 📡 **RSS Feed**: `http://YOUR-CONTAINER-IP:5050/feed.xml`
- 🌐 **Web UI**: `http://YOUR-CONTAINER-IP:5050/`
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

**Option 1: Docker Hub (Recommended)**
```bash
docker run -d \
  --name bind \
  -p 5050:5050 \
  -v bind_data:/opt/bind/data \
  starlightdaemon/bind:latest
```

**Option 2: Build from source**
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
python -m src.bind daemon --interval 60

# Run RSS server (separate terminal)
python -m src.rss_server
```

</details>

## Updating BIND

### Automatic Update (Recommended)

```bash
pct enter <container-id>
cd /opt/bind
scripts/update.sh
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

BIND uses 8 carefully chosen dependencies:

| Package | Purpose |
|---------|---------|
| **curl_cffi** | TLS fingerprinting for Cloudflare bypass (Layer 1) |
| **cloudscraper** | Fallback Cloudflare bypass (Layer 2) |
| **beautifulsoup4** | Parses HTML to extract magnet links |
| **lxml** | Fast XML/HTML parser backend for BeautifulSoup |
| **click** | Command-line interface framework |
| **schedule** | Lightweight daemon scheduling (cron alternative) |
| **flask** | RSS server and web UI |
| **gunicorn** | Production WSGI server |

All dependencies are actively maintained and essential to BIND's functionality.

</details>

<details>
<summary><b>📁 Project Structure</b></summary>

```
BIND/
├── src/
│   ├── core/
│   │   ├── scraper.py          # Hybrid Waterfall scraper (curl_cffi → cloudscraper)
│   │   ├── storage.py          # MagnetStore — SQLite + FTS5
│   │   ├── retry.py            # RetryEngine — exponential back-off
│   │   ├── magnet.py           # Magnet URI construction
│   │   ├── egress_manager.py   # Proxy / egress routing
│   │   ├── tracker_manager.py  # Tracker list management
│   │   ├── schema_monitor.py   # DB schema health checks
│   │   └── migrate.py          # SQLite migrations
│   ├── bind.py                 # Daemon with circuit breaker & deduplication
│   ├── rss_server.py           # RSS feed + Web UI + Settings UI
│   ├── config_manager.py       # Environment / config.env loading
│   └── security.py             # Auth, setup wizard, brute-force lockout
├── docker/
│   └── Dockerfile.single       # Single-container Docker image
├── deployment/
│   ├── bind.service            # Systemd daemon service
│   └── bind-rss.service        # Systemd RSS service
├── scripts/
│   ├── install.sh              # One-line installer
│   ├── install-proxmox-lxc.sh  # Proxmox LXC installer
│   └── update.sh               # In-place updater
└── requirements.txt            # Pinned dependencies
```

</details>

<details>
<summary><b>⚙️ Configuration (Environment Variables)</b></summary>

BIND is configured via environment variables in systemd service files. See [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) for complete guide.

**Common settings:**
- `ABB_URL` - Target domain (default: `http://audiobookbay.lu`)
- `BIND_PROXY` - HTTP/SOCKS5 proxy for scraping
- `BASE_URL` - RSS feed base URL override
- `BIND_DB_PATH` - SQLite database path (default: `data/bind.db`)
- `CIRCUIT_BREAKER_THRESHOLD` - Failures before circuit opens (default: 3)
- `CIRCUIT_BREAKER_COOLDOWN` - Cooldown period in seconds (default: 300)

**Configuration Sources (Precedence Order):**
1. **CLI Flags** (e.g. `--interval 120` manually) - Highest priority
2. **Environment Variables** (from `config.env` or systemd)
3. **Defaults** (Hardcoded fallback)

**To change configuration:**
- 🌐 **Web UI**: Go to `http://YOUR-IP:5050/settings` (Recommended)
- 📝 **File**: Edit `/opt/bind/config.env` and run `systemctl restart bind`
- 🖥️ **Systemd**: Override via `systemctl edit bind` (Advanced)

### Operational Defaults
- **Runtime Data**: `data/bind.db` (SQLite database)
- **Config Key**: `BIND_DB_PATH`
- **Precedence**: Environment Variables > `config.env` > Hardcoded Defaults
- **Security**: `credentials.json` and logs are ignored by git. Do not commit secrets.

## Environment Variables (Reference)

BIND is configured via environment variables in `bind.service` or `bind-rss.service`:

| Variable | Default | Description |
|----------|---------|-------------|
| `BIND_PROXY` | `None` | Optional HTTP/SOCKS5 proxy (e.g., `socks5://user:pass@host:1080`) |
| `ABB_URL` | `http://audiobookbay.lu` | Target domain (change if site moves) |
| `BASE_URL` | Auto-detected | Override RSS feed base URL |
| `BIND_DB_PATH` | `data/bind.db` | Path to SQLite database (Packaged: `/opt/bind/data/bind.db`) |
| `PORT` | `5050` | Web UI and RSS feed port (change if conflicting) |
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

## Development

```bash
# Setup
git clone https://github.com/StarlightDaemon/BIND.git && cd BIND
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-cov pytest-mock ruff

# Run Tests
pytest -v                    # All tests
pytest --cov=src             # With coverage

# Linting
ruff check src/ tests/       # Check issues
ruff format src/ tests/      # Auto-format
```

---

## About

**Lightweight and focused**: ~2,400 lines of code, 8 dependencies, minimal resource usage.

BIND archives publicly available audiobook metadata for digital preservation and personal library indexing while respecting intellectual property rights.
