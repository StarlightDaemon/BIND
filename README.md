# BIND - Book Indexing Network Daemon

> **Note**: BIND is an audiobook archival tool, NOT the DNS server

**Local, long-term backup system for audiobook metadata** from AudioBookBay (with future expansion to other sources).

## Features

- 📚 **Archival & Preservation** - Long-term backup of audiobook metadata
- 🤖 **Automated Daemon** - Background monitoring and collection
- 🧲 **Magnet Link Generation** - Complete links with tracker lists
- 📡 **RSS Feed** - Serve via HTTP for any torrent client
- 🌐 **Web UI** - View and manage collected magnets
- 🐳 **Easy Deployment** - Docker and Proxmox LXC support

## Quick Start

### Proxmox LXC (Recommended)
```bash
bash -c "$(wget -qLO - https://raw.githubusercontent.com/StarlightDaemon/BIND/main/install/install.sh)"
```

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

# Run daemon
python -m src.bind daemon --interval 60

# Run RSS server (separate terminal)
python -m src.rss_server
```

## Usage

**Access Points**:
- RSS Feed: `http://your-server:5000/feed.xml`
- Web UI: `http://your-server:5000/`

**Add to Torrent Client**:
- qBittorrent: Tools → RSS → New subscription
- Paste feed URL and enable auto-download

## How It Works

1. Daemon monitors AudioBookBay for new releases
2. Extracts info hash and generates magnet links
3. Saves to `magnets.txt` file
4. RSS server reads file and serves as feed
5. Torrent client auto-downloads from feed

## Project Structure

```
BIND/
├── src/
│   ├── core/         # Scraping engine
│   ├── bind.py       # Daemon
│   └── rss_server.py # RSS + Web UI
├── deployment/       # Systemd services
├── install/          # Proxmox installer
└── requirements.txt
```

## Dependencies

- cloudscraper - Cloudflare bypass
- beautifulsoup4 + lxml - HTML parsing
- click - CLI framework
- schedule - Task scheduling
- flask - RSS server

## Planned Features

- 📋 Category filtering (Fiction, Non-Fiction, etc.)
- 🎯 Keyword filtering (authors, titles)
- 📊 Statistics tracking

## Legal

**License**: MIT - For educational, archival, and preservation purposes.

**What BIND Does**:
- ✅ Archives publicly available metadata (magnet links)
- ✅ Enables personal library indexing
- ✅ Supports digital preservation

**What BIND Does NOT Do**:
- ❌ Host, provide, or distribute copyrighted content
- ❌ Store or transmit audiobook files
- ❌ Facilitate piracy

**User Responsibility**: Ensure compliance with copyright laws in your jurisdiction. BIND archives metadata only - not copyrighted works. Use only for public domain and legally distributable content.

**By using BIND, you agree to use it solely for legal, educational, and archival purposes.**

---

**Project Goal**: Local, long-term backup of audiobook metadata supporting digital preservation while respecting intellectual property rights.
