# Architecture

## System Overview

```
┌─────────────────┐
│  AudioBookBay   │
│   (RSS Feed)    │
└────────┬────────┘
         │ HTTP requests
         │ Every 60 min
         ▼
┌─────────────────┐
│  BIND Daemon    │
│  (bind.service) │
│                 │
│  • Scheduler    │
│  • Scraper      │
│  • Parser       │
│  • Generator    │
└────────┬────────┘
         │ Writes
         ▼
┌─────────────────┐
│  magnets/       │
│  *.txt files    │
│  (Daily files)  │
└────────┬────────┘
         │ Reads
         ▼
┌──────────────────────┐      ┌──────────────┐
│  RSS Server          │─────►│ Web Browser  │
│  (bind-rss.service)  │ HTTP │ (Web UI)     │
│                      │      └──────────────┘
│  • Flask app         │
│  • XML generator     │      ┌──────────────┐
│  • Health endpoint   │─────►│ Torrent      │
└──────────────────────┘ RSS  │ Client       │
                               └──────────────┘
```

## Component Details

### BIND Daemon (bind.service)
**File**: `src/bind.py` (65 lines)

**Responsibilities**:
- Checks AudioBookBay RSS feed every 60 minutes
- Scrapes detail pages for info hashes
- Generates magnet URIs with tracker lists
- Writes to daily files (`magnets_YYYY-MM-DD.txt`)

**Tech Stack**:
- `schedule` - Cron-like scheduling
- `cloudscraper` - Bypasses Cloudflare
- `beautifulsoup4` + `lxml` - HTML parsing

### Storage Layer
**Location**: `magnets/` directory

**Format**: Plain text, one magnet per line
**Rotation**: Daily files prevent corruption
**Size**: ~350 bytes per magnet

**Example**:
```
magnets/
├── magnets_2026-01-03.txt  (147 magnets)
├── magnets_2026-01-04.txt  (53 magnets)
└── magnets_2026-01-05.txt  (8 magnets)
```

### RSS Server (bind-rss.service)
**File**: `src/rss_server.py` (324 lines)

**Endpoints**:
- `/` - Web UI (HTML)
- `/feed.xml` - RSS 2.0 feed (XML)
- `/health` - Status endpoint (JSON)

**Features**:
- Reads all magnet files
- Generates valid RSS 2.0 XML
- Serves responsive web UI
- Provides health monitoring

**Tech Stack**:
- `flask` - Web framework
- Template rendering for UI
- XML generation for feed

## Data Flow

1. **Collection** (Every 60 min)
   ```
   AudioBookBay RSS → Scraper → Info Hash → Magnet URI → File
   ```

2. **Storage**
   ```
   magnets_YYYY-MM-DD.txt (append-only, one per day)
   ```

3. **Distribution**
   ```
   Files → RSS Server → {XML Feed, Web UI, Health Check}
   ```

4. **Consumption**
   ```
   RSS Feed → Torrent Client → Auto-download
   ```

## Deployment Architecture

### Proxmox LXC
```
┌─────────────────────────────────┐
│  Proxmox Host                   │
│                                 │
│  ┌───────────────────────────┐  │
│  │ LXC Container (bind)      │  │
│  │ Debian 12, 4GB disk       │  │
│  │                           │  │
│  │  • Python 3.11            │  │
│  │  • venv (~150MB)          │  │
│  │  • BIND code (~5MB)       │  │
│  │  • magnets/ (growing)     │  │
│  │                           │  │
│  │  Services:                │  │
│  │  ├─ bind.service          │  │
│  │  └─ bind-rss.service      │  │
│  └───────────┬───────────────┘  │
│              │ Port 5000        │
└──────────────┼──────────────────┘
               │
               ▼
        Network (vmbr0)
               │
               ▼
     LAN Clients (RSS feeds)
```

### Docker
```
┌─────────────────────────────┐
│  Docker Host                │
│                             │
│  ┌───────────────────────┐  │
│  │ bind_daemon           │  │
│  │ (runs src.bind)       │  │
│  └─────────┬─────────────┘  │
│            │ volume         │
│            ▼                │
│      magnets/              │
│            │                │
│  ┌─────────┴─────────────┐  │
│  │ bind_rss              │  │
│  │ (runs src.rss_server) │  │
│  └───────────┬───────────┘  │
│              │ Port 5000    │
└──────────────┼──────────────┘
               ▼
         Network bridge
```

## Security Model

**No authentication** - Designed for private LAN use
**No encryption** - HTTP only (use reverse proxy for HTTPS)
**No external access** - Bind to localhost or private network

**Recommended Setup**:
- Keep LXC on private VLAN
- Do not expose port 5000 to internet
- Use firewall rules to restrict access
- Only Proxmox host and LAN clients should reach port 5000

## Resource Usage

**Typical**:
- CPU: <1% (idle), ~5% (scraping)
- RAM: 50-100MB (daemon), 30-50MB (RSS server)
- Disk I/O: Minimal (append-only writes)
- Network: <100KB per scrape cycle

**Growth**:
- Storage: ~12MB per year (1 magnet/hour)
- No memory leaks (tested 7+ days uptime)
- No CPU creep

## Scalability

**Not designed for**:
- High traffic (single-user or small homelab)
- Large-scale deployments
- Public internet access

**Works well for**:
- 1-10 users on LAN
- Personal homelab use
- Light torrent client usage

## Monitoring

**Systemd Integration**:
```bash
systemctl status bind.service
systemctl status bind-rss.service
journalctl -u bind.service -f
```

**Health Endpoint**:
```bash
curl http://localhost:5000/health
```

**Response**:
```json
{
  "status": "ok",
  "magnet_count": 147,
  "magnets_dir": "/opt/bind/magnets",
  "magnet_files_count": 3,
  "latest_file": "magnets_2026-01-03.txt"
}
```

## Technology Choices

**Why Python?**
- Excellent scraping libraries
- Simple deployment
- Easy to maintain

**Why Flask?**
- Lightweight
- Built-in templating
- Perfect for RSS/API

**Why daily files?**
- Prevents corruption
- Easy backup/restore
- Simple to prune old data
- No database overhead

**Why systemd?**
- Standard on modern Linux
- Reliable auto-restart
- Easy log management
- Boot-time startup
