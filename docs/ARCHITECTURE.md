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
│  data/magnets/  │
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
**Location**: `data/magnets/` directory (canonical default)

**Path Configuration**:
- Canonical Default: `data/magnets/`
- Override: Supported via `MAGNETS_DIR` environment variable
- Legacy Fallback: `magnets/` (only used if `data/magnets/` is missing and legacy path exists)

**Format**: Plain text, one magnet per line
**Rotation**: Daily files prevent corruption
**Size**: ~350 bytes per magnet

**Example**:
```
data/magnets/
├── magnets_2026-01-03.txt  (147 magnets)
├── magnets_2026-01-04.txt  (53 magnets)
└── magnets_2026-01-05.txt  (8 magnets)
```

### RSS Server (bind-rss.service)
**File**: `src/rss_server.py` (324 lines)

**Endpoints**:
- `/` - Dashboard (HTML)
- `/magnets` - Management View (Search/Pagination)
- `/feed.xml` - RSS 2.0 Feed (XML)
- `/health` - Status Endpoint (JSON)
- `/settings` - Configuration (Auth Required)
- `/settings/trackers` - Tracker Management (Auth Required)
- `/settings/password` - Security Configuration (Auth Required)
- `/logs` - Audit Logs (Auth Required)
- `/setup` - First-time Setup Wizard
- `/api/stats` - Real-time Statistics

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
│  │  • data/magnets/ (growing)│  │
│  │                           │  │
│  │  Services:                │  │
│  │  ├─ bind.service          │  │
│  │  └─ bind-rss.service      │  │
│  └───────────┬───────────────┘  │
│              │ Port 5050        │
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
│      data/magnets/         │
│            │                │
│  ┌─────────┴─────────────┐  │
│  │ bind_rss              │  │
│  │ (runs src.rss_server) │  │
│  └───────────┬───────────┘  │
│              │ Port 5050    │
└──────────────┼──────────────┘
               ▼
         Network bridge
```

## Security Model

**Authentication & Access Control**:
- **Setup Wizard**: First-time access triggers a setup wizard to create admin credentials stored in `credentials.json`.
- **Basic Auth**: Protected routes (Settings, Logs) require Basic Authentication (configurable via `BIND_AUTH_ENABLED`).
- **IP Allowlist**: Integrated middleware restricts access to trusted networks (configurable via `BIND_ALLOWED_IPS` and `BIND_IP_FILTER`). Supports CIDR notation.
- **CSRF Protection**: POST requests are protected by session-based CSRF tokens (requires `FLASK_SECRET_KEY`).
- **Audit Logging**: All security events (logins, failures, changes) are recorded in `security.log`.

**Encryption & Exposure**:
- **No Native TLS**: HTTP only. A reverse proxy (Nginx, Caddy) is **highly recommended** for TLS termination if exposing beyond a private LAN.
- **Network Binding**: Defaults to `0.0.0.0:5050`. Recommended to bind to localhost or a private management network only.

**Recommended Setup**:
- Keep LXC on private VLAN
- Do not expose port 5050 to internet
- Use firewall rules to restrict access
- Only Proxmox host and LAN clients should reach port 5050

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
curl http://localhost:5050/health
```

**Response**:
```json
{
  "status": "ok",
  "magnet_count": 147,
  "magnets_dir": "data/magnets",
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
