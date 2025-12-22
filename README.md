# ABMG - AudioBookBay Media Grabber

A Python-based automated tool for discovering and managing audiobook torrents from AudioBookBay.

## Features

- 🔍 **Search functionality** - Search for specific audiobooks
- 🤖 **Daemon mode** - Automatically monitor and grab new releases
- 🧲 **Magnet link generation** - Creates magnet links with comprehensive tracker lists
- 🐳 **Docker support** - Easy deployment with Docker and Docker Compose
- 🖥️ **GUI interface** - User-friendly graphical interface (via `gui.py`)

## Project Structure

```
ABMG/
├── src/
│   ├── core/         # Core scraping functionality
│   ├── clients/      # qBittorrent client integration
│   └── gui.py        # GUI application
├── requirements.txt  # Python dependencies
├── Dockerfile        # Docker configuration
├── docker-compose.yml
└── linux_run.sh      # Linux startup script
```

## Installation

### Using Virtual Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/ABMG.git
cd ABMG

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Using Docker

```bash
docker-compose up -d
```

## Usage

### Search for Audiobooks

```bash
python -m src.abmg search "book title"
```

### Run in Daemon Mode

```bash
python -m src.abmg daemon --interval 60 \
  --qb-host localhost \
  --qb-port 8080 \
  --qb-user admin \
  --qb-pass adminadmin
```

### GUI Mode

```bash
python src/gui.py
```

## Environment Variables

Configure qBittorrent connection via environment variables:

- `QB_HOST` - qBittorrent host (default: localhost)
- `QB_PORT` - qBittorrent port (default: 8080)
- `QB_USER` - qBittorrent username (default: admin)
- `QB_PASS` - qBittorrent password (default: adminadmin)

## Dependencies

- cloudscraper - Bypass Cloudflare protection
- beautifulsoup4 - HTML parsing
- requests - HTTP requests
- click - CLI framework
- qbittorrent-api - qBittorrent integration
- lxml - XML/HTML processing
- schedule - Task scheduling
- pyyaml - Configuration management

## License

This project is for educational and archival purposes only.

## Disclaimer

This tool is intended for accessing public domain and legally distributable content. Users are responsible for ensuring compliance with copyright laws in their jurisdiction.
