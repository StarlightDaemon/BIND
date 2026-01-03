# BIND - Book Indexing Network Daemon

> **Note**: BIND is a book/audiobook archival tool, NOT the Berkeley Internet Name Domain (DNS server)

A Python-based automated tool for **archiving and preserving audiobook magnet links** from AudioBookBay.

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

This project is for educational and archival purposes only.

## Disclaimer

This tool is intended for accessing public domain and legally distributable content. Users are responsible for ensuring compliance with copyright laws in their jurisdiction. BIND is designed for **archival and preservation** of metadata, not piracy.
