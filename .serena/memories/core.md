# BIND — Core

**What it is:** Book Indexing Network Daemon — scrapes audiobook magnet links, stores them in SQLite, serves them via RSS + REST API with a React SPA frontend.

**Entrypoint:** `src/bind.py` → CLI (`bind` script), `daemon` sub-command runs the scheduling loop.

## Source map

```
src/
  bind.py            CLI + daemon loop (Click, scheduling, signal handling)
  rss_server.py      Flask app: RSS feed, full REST API, SPA proxy
  config_manager.py  ConfigManager (file I/O), LiveConfig (live-reload, no restart)
  security.py        Auth: credentials, per-IP + global lockout, network allowlist, @requires_auth
  healthcheck.py     Container health check — reads heartbeat freshness
  __main__.py        python -m src entry

  core/
    egress_manager.py   ProxyPool + EgressManager (curl_cffi / cloudscraper, proxy rotation)
    scraper.py          BindScraper + CircuitBreaker (web scraping, hash extraction)
    storage.py          MagnetStore (SQLite CRUD, schema DDL/upgrade, heartbeat)
    tracker_manager.py  TrackerManager (announce URL list, normalize, persist)
    magnet.py           generate_magnet() — builds magnet URI from hash + trackers
    retry.py            RetryConfig + RetryEngine (jitter, Retry-After, transient error set)
    schema_monitor.py   SchemaHealthMonitor + ParseAttempt (parse drift detection)
    migrate.py          One-time migration of legacy flat-file records into SQLite
```

See `mem:tech_stack`, `mem:conventions`, `mem:suggested_commands`, `mem:task_completion`.
