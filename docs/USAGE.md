# Usage Guide

## RSS Feed Setup

### qBittorrent
1. View → RSS Reader (Alt+S)
2. Right-click → New subscription
3. URL: `http://your-server:5050/feed.xml`
4. Set up auto-download rules

### BiglyBT
1. Install RSS Feed Scanner plugin
2. Add feed URL
3. Configure auto-download

### Transmission/Deluge
Similar RSS subscription process - add feed URL in RSS settings.

---

## Storage

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

---

## How It Works

1. **Daemon** checks AudioBookBay RSS feed every 60 minutes
2. **Scraper** extracts info hashes from detail pages
3. **Generator** creates magnet URIs with tracker lists
4. **Writer** saves to `magnets/magnets_YYYY-MM-DD.txt`
5. **RSS Server** reads all files and serves as feed
6. **Torrent Client** auto-downloads from feed

---

## Configuration

**Default Settings**:
- Daemon interval: 60 minutes
- RSS port: 5050
- Output directory: `magnets/`
- Max feed items: 100

**Customization** (edit systemd service):
```ini
# Change interval to 30 minutes:
ExecStart=... daemon --interval 30 --output-dir /opt/bind/magnets
```

---

## Monitoring

**Health Check**:
```bash
curl http://localhost:5050/health
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
