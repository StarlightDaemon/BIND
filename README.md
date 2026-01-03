# BIND - Book Indexing Network Daemon

[![Version](https://img.shields.io/badge/version-1.0-blue.svg)](https://github.com/StarlightDaemon/BIND/releases/tag/v1.0)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Proxmox](https://img.shields.io/badge/proxmox-ready-orange.svg)](install/install.sh)

> **Note**: BIND is an audiobook archival tool, NOT the DNS server

**v1.0 Release** - Automated audiobook metadata archival system. Stable, tested, and ready to use.

## Features

- 📚 **Archival & Preservation** - Long-term backup of audiobook metadata with daily file rotation
- 🤖 **Automated Daemon** - Runs every 60 minutes collecting new releases
- 🧲 **Magnet Link Generation** - Complete magnet URIs with comprehensive tracker lists
- 📡 **RSS 2.0 Feed** - Valid XML feed compatible with all torrent clients
- 🌐 **Web UI** - Beautiful gradient interface to view collected magnets
- 🔍 **Health Monitoring** - JSON endpoint for system status
- 🐳 **Easy Deployment** - One-click Proxmox installer, Docker support

## Tested With

✅ Proxmox LXC (Debian 12)  
✅ BiglyBT RSS Feed Scanner  
✅ qBittorrent RSS Reader  
✅ Production deployment (8+ magnets collected)

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

## Usage

### RSS Feed Setup

**qBittorrent**:
1. View → RSS Reader (Alt+S)
2. Right-click → New subscription
3. URL: `http://your-server:5000/feed.xml`
4. Set up auto-download rules

**BiglyBT**:
1. Install RSS Feed Scanner plugin
2. Add feed URL
3. Configure auto-download

**Transmission/Deluge**: Similar RSS subscription process

### Storage

Magnets saved to daily files:
```
magnets/
├── magnets_2026-01-03.txt
├── magnets_2026-01-04.txt
└── magnets_2026-01-05.txt
```

**Storage Requirements**:
- 100,000 magnets ≈ 35-40 MB
- Daily files prevent corruption
- Easy backup and pruning

## How It Works

1. **Daemon** checks AudioBookBay RSS feed every 60 minutes
2. **Scraper** extracts info hashes from detail pages
3. **Generator** creates magnet URIs with tracker lists
4. **Writer** saves to `magnets/magnets_YYYY-MM-DD.txt`
5. **RSS Server** reads all files and serves as feed
6. **Torrent Client** auto-downloads from feed

## Project Structure

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

## Dependencies

| Package | Purpose | Size |
|---------|---------|------|
| cloudscraper | Cloudflare bypass | Essential |
| beautifulsoup4 | HTML parsing | Essential |
| lxml | BeautifulSoup parser | Essential |
| click | CLI framework | Essential |
| schedule | Daemon scheduling | Essential |
| flask | RSS server | Essential |

**All 6 dependencies are actively used and justified.**

## Configuration

**Default Settings**:
- Daemon interval: 60 minutes
- RSS port: 5000
- Output directory: `magnets/`
- Max feed items: 100

**Customization** (edit systemd service):
```ini
# Change interval to 30 minutes:
ExecStart=... daemon --interval 30 --output-dir /opt/bind/magnets
```

## Monitoring

**Health Check**:
```bash
curl http://localhost:5000/health
```

**Response**:
```json
{
  "status": "ok",
  "magnet_count": 8,
  "magnets_dir": "/opt/bind/magnets",
  "magnet_files_count": 1,
  "latest_file": "magnets_2026-01-03.txt"
}
```

**View Logs**:
```bash
# Daemon logs
journalctl -u bind.service -f

# RSS server logs
journalctl -u bind-rss.service -f
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

## Troubleshooting

### Installer Issues

**Script fails with "pct command not found"**:
- You're not on a Proxmox host
- Run this only on Proxmox VE servers

**Script fails with "must be run as root"**:
```bash
sudo bash install.sh
```

**Container creation fails**:
- Check storage is available: `pvesm status`
- Check network: `ping 8.8.8.8`

**Template download fails**:
```bash
pveam update  # Update template list
# Then retry installation
```

**Installation fails inside container**:
- Installer will offer to remove broken container
- Choose 'y' to clean up and retry

### Runtime Issues

**RSS feed not accessible**:
```bash
pct enter <container-id>
systemctl status bind-rss.service
ss -tulpn | grep 5000
curl http://localhost:5000/feed.xml
```

**No magnets collected**:
```bash
pct enter <container-id>
journalctl -u bind.service -n 50
ls -lh /opt/bind/magnets/
```

**Services won't start**:
```bash
systemctl status bind.service
systemctl status bind-rss.service
journalctl -xe
```

**Update failed / rollback needed**:
```bash
cd /opt/bind
git tag  # Find backup tags
git checkout backup-YYYYMMDD-HHMMSS
systemctl restart bind.service bind-rss.service
```

**Port 5000 already in use**:
```bash
# Find what's using it
ss -tulpn | grep 5000

# Change BIND's port (edit bind-rss.service)
# Or stop the conflicting service
```

**BiglyBT XML parsing error**: Fixed in latest version (ampersands properly escaped - update to latest)

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

## Project Stats

**Code**: 531 lines (down from 710 - 27% reduction)  
**Dependencies**: 6 (down from 8)  
**Storage**: 35MB per 100k magnets  
**Deployment**: Production-ready  
**Testing**: Fully verified

**Project Goal**: Local, long-term backup of audiobook metadata supporting digital preservation while respecting intellectual property rights.
