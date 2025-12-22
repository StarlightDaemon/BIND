# ABMG - AudioBookBay Magnet Grabber

A Python-based automated tool for discovering and collecting audiobook magnet links from AudioBookBay.

## Features

- 🤖 **Daemon mode** - Automatically monitor and grab new releases
- 🧲 **Magnet link generation** - Creates magnet links with comprehensive tracker lists  
- 📝 **File-based output** - Saves magnet links to `magnets.txt` for use with any client
- 🐳 **Docker support** - Easy deployment with Docker and Docker Compose
- 🖥️ **GUI interface** - User-friendly graphical interface (via `gui.py`)

## What It Does

ABMG runs in the background, monitoring AudioBookBay for new audiobook releases. When found, it:
1. Extracts the info hash from the audiobook page
2. Generates a magnet link with public trackers
3. Saves the magnet link to `magnets.txt`

**What happens next is up to you** - import the magnet links into your preferred download client, RSS reader, or automation tool.

## Project Structure

```
ABMG/
├── src/
│   ├── core/         # Core scraping functionality
│   ├── clients/      # Download client integrations
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
git clone https://github.com/StarlightDaemon/ABMG.git
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

### Run in Daemon Mode

```bash
# Basic usage - saves magnet links to magnets.txt
python -m src.abmg daemon --interval 60
```

### GUI Mode

```bash
python src/gui.py
```

## Dependencies

- cloudscraper - Bypass Cloudflare protection
- beautifulsoup4 - HTML parsing
- requests - HTTP requests
- click - CLI framework
- lxml - XML/HTML processing
- schedule - Task scheduling
- pyyaml - Configuration management

## Planned Features

- 📋 **Category filtering** - Select which AudioBookBay categories to monitor (Fiction, Non-Fiction, etc.)
- 🎯 **Keyword filtering** - Only grab magnet links matching specific authors or titles
- 📊 **Statistics tracking** - Monitor collection activity and success rates

## License

This project is for educational and archival purposes only.

## Disclaimer

This tool is intended for accessing public domain and legally distributable content. Users are responsible for ensuring compliance with copyright laws in their jurisdiction.
