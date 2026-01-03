# BIND - Book Indexing Network Daemon

> **Note**: BIND is a book/audiobook archival tool, NOT the Berkeley Internet Name Domain (DNS server)

**A Python-based automated tool for creating local, long-term backups of audiobook metadata from AudioBookBay** (with potential expansion to other sources in the future).

## Mission

BIND creates a **personal, local archive** of magnet link metadata from audiobook sources. This tool is designed for:
- 📚 **Archival & Preservation**: Long-term backup of audiobook metadata
- 🔍 **Personal Indexing**: Build your own searchable catalog
- 🏛️ **Digital Preservation**: Maintain historical records of available content

**Important**: BIND does NOT host, provide, link to, or distribute any copyrighted content. It archives metadata only.

## Features

- 🤖 **Daemon mode** - Automatically monitor and collect new releases
- 📚 **Archival Purpose** - Long-term preservation of audiobook metadata
- 🧲 **Magnet link generation** - Creates magnet links with comprehensive tracker lists  
- 📝 **File-based output** - Saves magnet links to `magnets.txt` for use with any client
- 📡 **RSS Feed Server** - Serves collected links via RSS for torrent clients
- 🌐 **Web UI** - Beautiful interface to view and manage collected magnets
- 🐳 **Docker support** - Easy deployment with Docker and Docker Compose
- 📦 **Proxmox LXC** - One-click installer for Proxmox containers

## What It Does

BIND runs in the background, archiving audiobook magnet links from AudioBookBay. When found, it:
1. Extracts the info hash from the audiobook page
2. Generates a magnet link with public trackers
3. Saves the magnet link to `magnets.txt`
4. Serves them via RSS feed for automatic importing

**What happens next is up to you** - the RSS feed can be consumed by any torrent client (qBittorrent, Transmission, Deluge, etc.) for automated downloading.

## Project Structure

```
BIND/
├── src/
│   ├── core/         # Core scraping functionality
│   ├── clients/      # Download client integrations (legacy)
│   ├── bind.py       # Main daemon
│   └── rss_server.py # RSS feed + web UI
├── deployment/       # Systemd service files
├── requirements.txt  # Python dependencies
├── Dockerfile        # Docker configuration
├── docker-compose.yml
└── linux_run.sh      # Linux startup script
```

## Installation

### Using Virtual Environment

```bash
# Clone the repository
git clone https://github.com/StarlightDaemon/BIND.git
cd BIND

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt
```

### Using Docker

```bash
docker-compose up -d
```

### Proxmox LXC (One-Click)

```bash
# Coming soon - one-click Proxmox installer
bash -c "$(wget -qLO - https://github.com/StarlightDaemon/BIND/raw/main/install/install.sh)"
```

## Usage

### Run Daemon Mode

```bash
# Basic usage - archives magnet links to magnets.txt
python -m src.bind daemon --interval 60
```

### Run RSS Feed Server

```bash
# Start RSS server (serves magnets via HTTP)
python -m src.rss_server

# Access at:
# Web UI: http://localhost:5000
# RSS Feed: http://localhost:5000/feed.xml
```

### Add to Torrent Client

**qBittorrent**:
1. Tools → RSS Reader → New subscription
2. URL: `http://your-server-ip:5000/feed.xml`
3. Enable "Auto-download" with filters if desired

**Transmission / Deluge**: Similar RSS subscription process

## Dependencies

- cloudscraper - Bypass Cloudflare protection
- beautifulsoup4 - HTML parsing
- requests - HTTP requests
- click - CLI framework
- lxml - XML/HTML processing
- schedule - Task scheduling
- pyyaml - Configuration management
- flask - RSS feed server and web UI

## Planned Features

- 📋 **Category filtering** - Select which AudioBookBay categories to monitor (Fiction, Non-Fiction, etc.)
- 🎯 **Keyword filtering** - Only collect magnet links matching specific authors or titles
- 📊 **Statistics tracking** - Monitor collection activity and success rates

## License

MIT License - For educational, archival, and preservation purposes.

## Legal Disclaimer & Usage Policy

### What BIND Does
- ✅ Creates **local backups** of publicly available metadata (magnet links)
- ✅ Enables **personal archival** and indexing of book/audiobook information
- ✅ Provides **tools for preservation** of digital library catalogs

### What BIND Does NOT Do
- ❌ Does NOT host, provide, or distribute copyrighted content
- ❌ Does NOT link directly to infringing material
- ❌ Does NOT facilitate piracy or copyright infringement
- ❌ Does NOT store or transmit actual audiobook files

### Intended Use
BIND is designed exclusively for:
1. **Educational purposes** - Learning about metadata archival systems
2. **Personal archival** - Creating local backups of publicly available metadata
3. **Preservation** - Maintaining historical records of digital library catalogs
4. **Legal content only** - Accessing public domain and legally distributable materials

### User Responsibility
**Users are solely responsible for**:
- Ensuring all content accessed is legal in their jurisdiction
- Complying with copyright laws and terms of service
- Using this tool only for legitimate archival and educational purposes
- Verifying content licensing before downloading or distributing

### Copyright Compliance
This tool respects copyright law. BIND archives only **metadata** (titles, descriptions, identifiers) - not copyrighted works themselves. Users must ensure compliance with:
- Local and international copyright laws
- Terms of service of source websites
- Licensing requirements for any content accessed

**By using BIND, you agree to use it only for legal, educational, and archival purposes in accordance with applicable laws.**

---

**Project Goal**: To provide a local, long-term backup solution for audiobook metadata, supporting digital preservation efforts while respecting intellectual property rights.
