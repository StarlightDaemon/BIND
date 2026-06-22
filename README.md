# BIND - Book Indexing Network Daemon

[![CI](https://github.com/StarlightDaemon/BIND/actions/workflows/ci.yml/badge.svg)](https://github.com/StarlightDaemon/BIND/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/StarlightDaemon/BIND/branch/main/graph/badge.svg)](https://codecov.io/gh/StarlightDaemon/BIND)
[![Version](https://img.shields.io/badge/version-2.2.0-blue.svg)](https://github.com/StarlightDaemon/BIND/releases/tag/v2.2.0)
[![Python](https://img.shields.io/badge/python-3.10+-yellow.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Proxmox](https://img.shields.io/badge/proxmox-ready-orange.svg)](scripts/install-proxmox-lxc.sh)

**v2.2.0** — Self-hosted audiobook metadata archival with SQLite storage, authentication, hybrid Cloudflare defense, metrics dashboard, and domain resilience probe.

## Features

### 📚 What it collects
- **Metadata Archival** - Long-term local backup with 90-day retention and automatic pruning
- **Automated Collection** - Daemon runs every 60 minutes, collecting new releases
- **Magnet Link Generation** - Complete magnet URIs with comprehensive tracker lists
- **SQLite Storage** - MagnetStore with FTS5 full-text search

### 🛡️ How it stays up
- **Cloudflare Defense** - Three-layer waterfall: curl_cffi TLS fingerprint → cloudscraper → proxy
- **Retry Engine** - Exponential back-off with circuit breaker; handles 429s and transient failures
- **Domain Resilience Probe** - Classifies target health: reachable / blocked / wrong content / unreachable
- **Self-Healing** - Deduplication and schema health monitoring; zero manual intervention

### 🌐 How you access it
- **RSS 2.0 Feed** - Valid XML feed compatible with all torrent clients
- **Web UI** - Full-text search across collected magnets
- **Metrics Dashboard** - Color-coded scrape history, 7/30-day counts, and success rate at `/metrics`
- **Settings UI** - Browser-based configuration at `/settings` — no file editing required

### 🔒 Security & deployment
- **Authentication** - Setup wizard, password protection, and brute-force lockout
- **Easy Deployment** - One-line Proxmox installer, Docker Hub image

## Deployment

Runs on any Linux system with Python 3. Tested on Proxmox LXC containers and works with all RSS-capable torrent clients.

> **⚠️ Security Note**: BIND includes a built-in authentication system (Setup Wizard, Password Protection, Bruteforce Lockout). However, for maximum security, we still recommend running behind a reverse proxy (nginx, Caddy, Cloudflare Tunnel) if exposing to the public internet.

## 🚀 Installation

### Proxmox LXC (Recommended)

```bash
bash <(curl -sL https://raw.githubusercontent.com/StarlightDaemon/BIND/main/scripts/install-proxmox-lxc.sh)
```

<details>
<summary><b>What this does + post-install URLs</b></summary>

**What This Does:**
1. Creates a new LXC container with Ubuntu
2. Prompts for configuration (Container ID, hostname, RAM, disk, IP address)
3. Installs Python 3, Git, and all BIND dependencies
4. Configures systemd services for auto-start
5. Displays your Web UI and RSS feed URLs

**Installation Time:** ~3 minutes  
**Default Resources:** 512MB RAM, 4GB disk, 1 CPU core

**After Installation:**
- **RSS Feed**: `http://YOUR-CONTAINER-IP:5050/feed.xml`
- **Web UI**: `http://YOUR-CONTAINER-IP:5050/`
- **View Logs**: `pct exec <CTID> -- journalctl -u bind -f`
- **Enter Container**: `pct enter <CTID>`

> **Note**: Requires Proxmox VE with an Ubuntu 22.04/24.04 template. Download one with:
> ```bash
> pveam update && pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst
> ```

</details>

<details>
<summary><b>Alternative: Already have a container or VM?</b></summary>

If you already have an existing LXC container, VM, or bare-metal Debian/Ubuntu system:

**Option 1: Simple Install** (uses defaults)
```bash
bash <(curl -sL https://raw.githubusercontent.com/StarlightDaemon/BIND/main/scripts/install.sh)
```

**Option 2: Interactive Install** (custom configuration)
```bash
bash <(curl -sL https://raw.githubusercontent.com/StarlightDaemon/BIND/main/scripts/install-interactive.sh)
```

</details>

<details>
<summary><b>Docker</b></summary>

**Option 1: Docker Hub**
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
<summary><b>Manual Installation</b></summary>

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

---

## Adding to qBittorrent

1. In qBittorrent go to **RSS** → **Add feed** and enter your feed URL:
   ```
   http://YOUR-BIND-IP:5050/feed.xml
   ```

2. Open **RSS Downloader** → create a new rule:
   - **Must Contain:** `.*`
   - **Use Regular Expressions:** checked
   - **Save to:** your audiobook download path
   - **Apply Rule to Feeds:** check your BIND feed

3. Click **Save**, then right-click the feed → **Update** to populate existing items.

> ⚠️ **VPN-bound containers (e.g. binhex/qbittorrentvpn on Unraid):** The container needs outbound access to port 5050 on your LAN. Add `VPN_OUTPUT_PORTS=5050` as an environment variable in the container template and recreate it. `LAN_NETWORK` alone is not sufficient with WireGuard — `VPN_OUTPUT_PORTS` is required for the container to initiate outbound connections to local services.

---

## Updating BIND

### Automatic Update (Recommended)

```bash
pct enter <container-id>
cd /opt/bind
scripts/update.sh
```

The update script will:
- Check for updates
- Show what's new
- Backup current version
- Update code and dependencies
- Restart services
- Verify everything works
- Rollback on failure

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
- **[Releases](docs/RELEASES.md)** - Release notes — v1.0 through v2.1
- **[Design System](docs/BIND_IMPLEMENTATION_GUIDE.md)** - Web UI theming reference

---

<details>
<summary><b>Dependencies</b></summary>

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
| **gunicorn** | WSGI server |

All dependencies are actively maintained and essential to BIND's functionality.

</details>

<details>
<summary><b>Project Structure</b></summary>

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
<summary><b>Configuration (Environment Variables)</b></summary>

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
- **Web UI**: Go to `http://YOUR-IP:5050/settings` (Recommended)
- **File**: Edit `/opt/bind/config.env` and run `systemctl restart bind`
- **Systemd**: Override via `systemctl edit bind` (Advanced)

**Environment Variables (Reference)**

| Variable | Default | Description |
|----------|---------|-------------|
| `BIND_PROXY` | `None` | Optional HTTP/SOCKS5 proxy (e.g., `socks5://user:pass@host:1080`) |
| `ABB_URL` | `http://audiobookbay.lu` | Target domain (change if site moves) |
| `BASE_URL` | Auto-detected | Override RSS feed base URL |
| `BIND_DB_PATH` | `data/bind.db` | Path to SQLite database (Packaged: `/opt/bind/data/bind.db`) |
| `PORT` | `5050` | Web UI and RSS feed port (change if conflicting) |
| `CIRCUIT_BREAKER_THRESHOLD` | `3` | Failures before scraper pauses |
| `CIRCUIT_BREAKER_COOLDOWN` | `300` | Seconds to wait after pausing |

> **Security**: `credentials.json` and logs are ignored by git. Do not commit secrets.

</details>

---

<details>
<summary><b>Legal</b></summary>

**License**: MIT — For educational, archival, and preservation purposes.

### What BIND Does
- Archives publicly available metadata for digital preservation
- Creates local backups of torrent magnet links
- Supports audiobook collection management
- Stores metadata only (no copyrighted content)

### What BIND Does NOT Do
- Does not host, provide, or distribute copyrighted content
- Does not store or transmit actual audiobook files
- Does not facilitate piracy or copyright infringement
- Does not link directly to infringing material

### User Responsibility
Ensure compliance with copyright laws in your jurisdiction. BIND archives metadata only — not copyrighted works. Use only for public domain and legally distributable content.

**By using BIND, you agree to use it solely for legal, educational, and archival purposes in accordance with applicable laws.**

</details>

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

**Lightweight and focused**: ~1,700 lines of code, 8 dependencies, minimal resource usage.

BIND archives publicly available audiobook metadata for digital preservation and personal library indexing while respecting intellectual property rights.
