# Architecture

## System Overview

```
┌─────────────────┐
│  AudioBookBay   │
│   (RSS + HTML)  │
└────────┬────────┘
         │ HTTPS
         ▼
┌────────────────────────────────────────┐
│  BIND Daemon  (bind.service)           │
│                                        │
│  Scheduler ──► Scraper ──► EgressMgr  │
│                   │             │      │
│                   │         RetryEngine│
│                   │         ProxyPool  │
│                   ▼                    │
│           SchemaMonitor                │
│                                        │
│  MagnetStore        TrackerManager     │
└───────────────────────┬────────────────┘
                        │ writes (SQLite)
                        ▼
               ┌─────────────────┐
               │  data/bind.db   │
               │  SQLite + FTS5  │
               └────────┬────────┘
                        │ reads
                        ▼
┌──────────────────────────────┐      ┌────────────────┐
│  RSS Server (bind-rss.service│─────►│ Web Browser    │
│  gunicorn + Flask            │ HTTP │ (Web UI)       │
│                              │      └────────────────┘
│  • XML feed generator        │
│  • Web UI / dashboard        │      ┌────────────────┐
│  • Health + stats endpoints  │─────►│ Torrent Client │
│  • Auth + CSRF middleware    │ RSS  └────────────────┘
│  • Security audit log        │
└──────────────────────────────┘
```

## Module Map

```
src/
├── bind.py               Daemon entry point: scheduler, job loop, MagnetStore integration
├── rss_server.py         Flask app: all HTTP routes, auth, CSRF, security log, metrics
├── config_manager.py     Reads/writes config.env (key-value store for UI settings)
├── security.py           IP allowlist, basic-auth, CSRF, audit logging
└── core/
    ├── scraper.py        BindScraper: RSS fetch, HTML parse, magnet generation;
    │                       CircuitBreaker gates all outbound requests;
    │                       probe_target() classifies target health
    ├── storage.py        MagnetStore: SQLite + FTS5; scrape_runs table for metrics
    ├── migrate.py        Schema migrations (run at startup)
    ├── egress_manager.py Three-layer fetch waterfall; ProxyPool round-robin
    ├── retry.py          RetryEngine: exponential backoff + full jitter;
    │                       classifies 429, retryable HTTP, permanent HTTP,
    │                       transient network, non-retryable
    ├── schema_monitor.py SchemaHealthMonitor: rolling 30-min window;
    │                       CRITICAL log when parse success < 50% over >= 5 attempts
    └── tracker_manager.py TrackerManager: reads/writes data/trackers.json with
                            atomic fsync+replace; normalises and deduplicates URLs
```

## Import Graph

```
bind.py  ──────────────────────────────────► config_manager
          ──────────────────────────────────► tracker_manager
          ──────────────────────────────────► scraper
          ──────────────────────────────────► storage
                                                  │
rss_server.py ─────────────────────────────► config_manager
               ─────────────────────────────► tracker_manager
               ─────────────────────────────► scraper
               ─────────────────────────────► storage
               ─────────────────────────────► security

scraper.py ────────────────────────────────► egress_manager
            ───────────────────────────────► schema_monitor

storage.py ────────────────────────────────► migrate

egress_manager.py ─────────────────────────► retry
```

## Component Details

### BIND Daemon (`bind.service`)
**File**: `src/bind.py` (~220 lines)

**Responsibilities**:
- Schedules a scrape job every N minutes (default: 60, override: `SCRAPE_INTERVAL`)
- Runs each job in a `ThreadPoolExecutor` with a hard timeout (`BIND_JOB_TIMEOUT`, default 3600s)
- Deduplicates across runs via `MagnetStore` (checks info hash against SQLite before write)
- Records every scrape run outcome (result, items_new, duration) to `scrape_runs` table
- Logs WARNING at startup if `probe_target()` returns unreachable or wrong_content
- Checks disk space before each job (skips if < 100 MB free)
- Handles `SIGTERM`/`SIGINT` gracefully (completes the current job before exit)

### Egress Layer

**`src/core/egress_manager.py`** — `EgressManager` attempts each fetch via three layers in order:

1. `curl_cffi` direct (browser-impersonation TLS fingerprint)
2. `curl_cffi` + proxy (skipped if `ProxyPool` is empty; proxy evicted on failure)
3. `cloudscraper` (Cloudflare JS-challenge solver)

Each layer is retried up to `MAX_RETRIES=3` times via `RetryEngine` before escalating.
Raises `FetchExhausted` if all layers fail.

Configure proxies via `BIND_PROXIES` (comma-separated) or `BIND_PROXY` (single).

**`src/core/retry.py`** — `RetryEngine` with exponential backoff + full jitter.
Error classification:
- `429` → honours `Retry-After` header or backs off exponentially
- Retryable HTTP (500, 502, 503, 504) → backoff and retry
- Permanent HTTP (4xx other than 429) → escalate immediately
- `ConnectionError` / `TimeoutError` → backoff and retry
- All other exceptions → escalate immediately

**`src/core/scraper.py`** — `BindScraper` wraps `EgressManager` behind a `CircuitBreaker`.
The breaker opens after N consecutive total failures (default 3, `CIRCUIT_BREAKER_THRESHOLD`),
then pauses all outbound requests for a cooldown period (default 300s, `CIRCUIT_BREAKER_COOLDOWN`).

`probe_target()` performs a lightweight GET to the base URL outside the egress waterfall and circuit
breaker, returning one of four string labels: `"reachable"`, `"cloudflare_block"`, `"wrong_content"`,
or `"unreachable"`. The daemon calls this at startup; the result is cached for 5 minutes and exposed
in the `/health` response.

### Schema Health Monitor
**File**: `src/core/schema_monitor.py`

`SchemaHealthMonitor` records every parse attempt (success or failure) with a timestamp.
Maintains a rolling 30-minute window; logs `CRITICAL` when parse success rate falls below
50% over >= 5 attempts. Signals that AudioBookBay's HTML layout may have changed.

### Tracker Manager
**File**: `src/core/tracker_manager.py`

`TrackerManager` persists the BitTorrent tracker list to `data/trackers.json`.
Writes are atomic: tmp file → `fsync` → `os.replace`. Reads use a shared `fcntl` lock.
Normalises URLs (trims whitespace, validates protocol) and deduplicates case-insensitively.
Defaults to three public trackers if `trackers.json` is absent.

### Storage Layer
**File**: `src/core/storage.py` — `MagnetStore`
**Location**: `data/bind.db` (SQLite, configured via `BIND_DB_PATH`)

| Table | Purpose |
|---|---|
| `magnets` | One row per collected magnet; FTS5 virtual table for full-text search |
| `scrape_runs` | One row per daemon run cycle: timestamp, result, items_new, duration_s |

Schema migrations run at startup via `src/core/migrate.py`. Tracker URLs are persisted
separately to `data/trackers.json` (atomic fsync+replace; not in the database).

### RSS Server (`bind-rss.service`)
**File**: `src/rss_server.py` (~477 lines), served via gunicorn

**Endpoints**:
- `/` — Dashboard (HTML)
- `/magnets` — Magnet browser (search, pagination)
- `/feed.xml` — RSS 2.0 feed
- `/health` — Status JSON (includes cached `target_probe` result)
- `/metrics` — Metrics dashboard: color-coded scrape history, success rate, 7/30-day counts (auth required)
- `/api/stats` — Real-time statistics JSON (auth required)
- `/settings` — Configuration (auth required)
- `/settings/trackers` — Tracker management (auth required)
- `/settings/password` — Password change (auth required)
- `/logs` — Audit log viewer (auth required)
- `/setup` — First-time setup wizard

### Metrics Dashboard

**Route**: `/metrics` (auth required)
**Template**: `src/templates/metrics.html`

Reads the last 30 rows from `scrape_runs` and computes:
- **success_rate** — percentage of successful runs in the window
- **7/30-day counts** — total magnets collected via `MagnetStore.stats()`
- **Color-coded run table** — each row is green (success), yellow (partial), or red (error)

## Data Flow

```
1. Collection (every N minutes)
   ABB RSS feed → scraper → detail page (EgressMgr waterfall)
   → info hash extraction (4-strategy waterfall) → magnet URI → MagnetStore (SQLite)

2. Dedup
   Each info hash checked against MagnetStore before write.
   Duplicate → skip. New → INSERT into magnets table.
   Run outcome recorded to scrape_runs table.

3. Distribution
   MagnetStore → RSS Server → { XML feed, Web UI, health/stats JSON, metrics dashboard }

4. Consumption
   RSS feed → torrent client → auto-download
```

## Deployment

### Proxmox LXC (recommended)
```
┌──────────────────────────────────────┐
│  Proxmox Host                        │
│  ┌────────────────────────────────┐  │
│  │ LXC Container (bind)           │  │
│  │ Debian 12, 4 GB disk           │  │
│  │                                │  │
│  │  Python 3.11 + venv (~150 MB)  │  │
│  │  ├─ bind.service               │  │
│  │  └─ bind-rss.service           │  │
│  └──────────────┬─────────────────┘  │
│                 │ :5050              │
└─────────────────┼────────────────────┘
                  ▼
           LAN Clients
```

### Docker
```
bind_daemon ──► data/magnets/ ◄── bind_rss
                                      │ :5050
                                      ▼
                                 Network bridge
```

## Security Model

| Control | Detail |
|---|---|
| Setup wizard | Creates `credentials.json` on first run |
| Basic Auth | Protects settings/logs routes (`BIND_AUTH_ENABLED`) |
| IP allowlist | CIDR-based middleware (`BIND_ALLOWED_IPS`, `BIND_IP_FILTER`) |
| CSRF tokens | Session-based; required for all POST routes (`FLASK_SECRET_KEY`) |
| Audit log | All auth events written to `security.log` |
| TLS | None native — use a reverse proxy (Nginx/Caddy) if exposing beyond LAN |

Bind to localhost or a private management network. Do not expose port 5050 to the internet.

## Resource Usage

| Resource | Idle | Scraping |
|---|---|---|
| CPU | < 1% | ~5% |
| RAM (daemon) | 50–100 MB | — |
| RAM (RSS server) | 30–50 MB | — |
| Network | — | < 100 KB/cycle |
| Disk growth | ~12 MB/year | — |

## Monitoring

```bash
systemctl status bind.service
systemctl status bind-rss.service
journalctl -u bind.service -f
curl http://localhost:5050/health
```
