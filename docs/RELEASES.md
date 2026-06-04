# BIND Release Notes

---

## v2.1.0 — Codecov + Coverage Gate

**Release Date**: June 4, 2026

- Integrated Codecov for per-PR coverage reporting
- Coverage gate raised to 75%; new storage and resilience test suites added
- CI pipeline requires coverage threshold to merge
- No behaviour changes from v2.0.0

---

## v2.0.0 — Metrics Dashboard, Domain Resilience Probe, CI Hardening

**Release Date**: June 4, 2026

### New Features

**Metrics Dashboard** (`/metrics`)
- Auth-gated route with Vesper-themed HTML dashboard
- Shows last 30 scrape runs color-coded by result (success / partial / error)
- Displays 7-day and 30-day magnet counts, overall success rate
- `scrape_runs` table added to `MagnetStore` schema; daemon records every run cycle

**Domain Resilience Probe** (`probe_target()`)
- `BindScraper.probe_target()` classifies target health without touching the circuit breaker
- Returns one of: `reachable`, `cloudflare_block`, `wrong_content`, `unreachable`
- Cached for 5 minutes; result exposed in `/health` response
- Daemon logs WARNING at startup for unreachable or wrong_content

**CI: dev-dependency audit**
- `pip-audit` step added for development dependencies to catch CVEs in the test toolchain

### Tests
- 273 tests passing; 77% coverage

---

## v1.7.1 — Docker Hub CI, Secret Key Auto-Gen, Settings UI Polish

**Release Date**: May 13, 2026

- Docker Hub publish workflow with automated push on tag
- `FLASK_SECRET_KEY` auto-generated on first run if absent
- Proxy support for `cloudscraper` layer
- 8 GitHub releases backfilled with changelogs

---

## v1.7.0 — SQLite Storage Migration

**Release Date**: May 12, 2026

- Replaced flat-file storage (`magnets_YYYY-MM-DD.txt` + `history.log`) with `MagnetStore` (SQLite + FTS5)
- Full-text search across all collected magnets
- Schema migration runner (`migrate.py`) for forward-compatible upgrades
- 193 tests passing

---

## v1.6.1 — Audit Backlog Closed

**Release Date**: May 12, 2026

- All findings from security, architecture, and resilience audits resolved
- 131 tests passing, zero open findings

---

## v1.4.0 — Resilience Modules

**Release Date**: May 11, 2026

- `RetryEngine` with exponential back-off and full jitter
- `EgressManager` three-layer waterfall: curl_cffi → proxy → cloudscraper
- `SchemaHealthMonitor` rolling parse-success window

---

## v1.3.0 — Authentication & Settings UI

**Release Date**: May 11, 2026

- Setup wizard on first run
- Password-protected routes with brute-force lockout
- Browser-based settings at `/settings` — no file editing required
- CSRF protection for all POST routes
- Audit log at `/logs`

---

## v1.0.0 — Initial Production Release

**Release Date**: January 9, 2026  
**Project**: BIND - Book Indexing Network Daemon  
**Type**: Production Release (v1.0.0)

---

## 🎉 Welcome to BIND v1.0!

After extensive development and testing, we're releasing the first stable version of BIND - an automated audiobook metadata archival system.

---

## 🚀 What is BIND?

BIND is an automated system for creating local, long-term backups of audiobook metadata from AudioBookBay. It runs as a daemon, collecting magnet links and serving them via RSS feed to your torrent client.

**BIND does NOT download audiobooks** - it archives metadata (magnet links) for personal library indexing and digital preservation.

---

## ✨ Key Features

### Core Functionality
- **Automated Daemon**: Collects new audiobook metadata every 60 minutes
- **Magnet Link Generation**: Complete magnet URIs with comprehensive tracker lists
- **RSS 2.0 Feed**: Valid XML feed compatible with all torrent clients
- **Web UI**: Beautiful, responsive interface to view collected magnets
- **Daily File Rotation**: Separate files per day for reliability and backup ease
- **Health Monitoring**: JSON endpoint for system status

### Deployment
- **One-Click Proxmox Installer**: Automated LXC deployment in ~2 minutes
- **Docker Support**: Full Docker and docker-compose configurations
- **Manual Installation**: Simple pip-based setup for any Linux system

### Reliability
- **Update Mechanism**: Safe updates with automatic rollback
- **Error Recovery**: Cleanup and troubleshooting guidance
- **Network Flexibility**: DHCP or static IP configuration
- **Storage Agnostic**: Works with any Proxmox storage backend

---

## 📊 Technical Specifications

**Codebase**:
- Total: 531 lines (focused, minimal design)
- Main daemon: 65 lines
- RSS server: 324 lines
- Scraper engine: Well-tested and reliable

**Dependencies**: 6 essential packages
- cloudscraper (Cloudflare bypass)
- beautifulsoup4 (HTML parsing)
- lxml (Parser backend)
- click (CLI framework)
- schedule (Daemon scheduling)
- flask (RSS server)

**Storage Efficiency**:
- 100,000 magnets ≈ 35-40 MB
- Daily file rotation prevents corruption
- Easy backup and pruning

**Performance**:
- Deployment: ~2 minutes
- Updates: ~1 minute
- Resource usage: 512MB RAM, 1 CPU core, 4GB disk

---

## 🎯 Tested and Verified

BIND v1.0 has been tested in real homelab deployments:

- ✅ **Proxmox LXC** (Debian 12) - Primary deployment
- ✅ **BiglyBT** RSS Feed Scanner - Verified compatible
- ✅ **qBittorrent** RSS Reader - Verified compatible
- ✅ **Homelab Deployment** - Running stable, 8+ magnets collected

---

## 📦 Installation

### Quick Start (Proxmox LXC)
```bash
bash -c "$(wget -qLO - https://raw.githubusercontent.com/StarlightDaemon/BIND/main/install/install.sh)"
```

### Docker
```bash
git clone https://github.com/StarlightDaemon/BIND.git
cd BIND
docker-compose up -d
```

### Manual
```bash
git clone https://github.com/StarlightDaemon/BIND.git
cd BIND
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m src.bind daemon --interval 60 --output-dir magnets/
```

---

## 🔄 Updating

BIND includes a built-in update mechanism:

```bash
pct enter <container-id>
cd /opt/bind
./update.sh
```

Features automatic backup, rollback, and service verification.

---

## 📚 Documentation

Comprehensive documentation includes:
- Installation guide (Proxmox, Docker, Manual)
- RSS feed setup for qBittorrent, BiglyBT, Transmission
- Troubleshooting (installer and runtime issues)
- Update procedures with rollback
- Architecture and design decisions
- Legal disclaimers and responsible use

---

## 🛡️ What's Included

### Installer Features
- ✅ Prerequisites check (Proxmox, root, internet)
- ✅ Network configuration (DHCP or static IP)
- ✅ Smart storage detection
- ✅ Automatic template download
- ✅ Clean, quiet installation
- ✅ Cleanup on failure
- ✅ Clear error messages

### Runtime Features
- ✅ Cloudflare bypass for scraping
- ✅ Daily magnet file rotation
- ✅ RSS 2.0 feed with proper XML escaping
- ✅ Web UI with responsive design
- ✅ Health check endpoint
- ✅ Systemd service integration
- ✅ Auto-start on boot

### Operational Features
- ✅ Update script with git tagging
- ✅ Automatic rollback on update failure
- ✅ Service verification after updates
- ✅ Comprehensive logging
- ✅ Easy troubleshooting

---

## 🔮 Future Roadmap

While v1.0 is feature-complete and production-ready, planned enhancements include:

**v1.1-v1.2** (Polish):
- Web UI improvements (StarlightDaemon design system implemented)
- Screenshots in documentation
- FAQ section
- Architecture diagrams

**v2.0** (Features):
- Keyword filtering (`--include`/`--exclude`)
- Configurable daemon interval
- Magnet deduplication
- RSS feed pagination

See `FUTURE_ENHANCEMENTS.md` for details.

---

## 📜 License & Legal

**License**: MIT

BIND is for educational, archival, and preservation purposes. It archives publicly available metadata (magnet links) only - not copyrighted content.

**Users must**:
- Comply with copyright laws in their jurisdiction
- Use only for legal, educational, and archival purposes
- Respect intellectual property rights

BIND does not host, provide, or distribute copyrighted content.

---

## 🙏 Acknowledgments

- **AudioBookBay** - Source of metadata
- **Proxmox Community** - Inspiration for installer standards
- **tteck/Proxmox** - Reference for LXC deployment best practices

---

## 🐛 Known Issues

None! 🎉

All critical issues have been resolved. See GitHub Issues for feature requests.

---

## 📞 Support

- **Documentation**: See README.md
- **Issues**: GitHub Issues tracker
- **Updates**: Use built-in `./update.sh` script

---

## 🎊 Thank You

Thank you for using BIND v1.0. This release represents months of development, testing, and refinement to create a reliable, production-ready audiobook metadata archival system.

We hope BIND helps you maintain your personal library index and supports digital preservation efforts.

**Happy archiving!** 📚

---

**BIND v1.0** - Digital preservation made simple.
