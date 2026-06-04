# BIND Roadmap

## Project Philosophy

**BIND is designed to stay slim, focused, and maintainable.**

We prioritize:
- 📦 **Simplicity** - Do one thing well
- 🎯 **Focus** - Archive metadata, nothing more
- 🧹 **Minimal** - Keep codebase small and clean
- 📚 **Documentation** - Over feature bloat

---

## v1.0 - Proxmox LXC Production Release ✅

**Status**: Feature-complete and production-ready  
**Focus**: Proxmox LXC deployment with one-line installer  
**Goal**: Stable, well-documented, single-platform release

This release establishes BIND as a production-ready Proxmox application. No new features planned.

---

## v1.1 - Stability Overhaul ✅

**Status**: Complete  
**Focus**: Hybrid Cloudflare defense and reliability improvements

- ✅ Circuit breaker pattern for rate limiting
- ✅ curl_cffi TLS masquerading
- ✅ Global deduplication
- ✅ Graceful shutdown handling
- ✅ File retention policy (90-day auto-cleanup)

---

## v1.2 - Long-Term Support (LTS) ✅

**Status**: Current LTS Release  
**Focus**: Hardening and cleanup for long-term maintenance

### Completed
- ✅ Fixed Docker Compose (dual-service architecture)
- ✅ Added missing `curl_cffi` dependency
- ✅ Removed development artifacts
- ✅ Source directory cleanup

### Maintenance Mode
BIND v1.x is now in **maintenance-only mode**:
- ✅ Critical bug fixes only
- ✅ Security patches as needed
- ❌ No new features (deferred to v2.0)

---

## v2.0 / v2.1 - Feature Expansion ✅

**Status**: Complete (shipped June 2026)  
**Focus**: Metrics visibility, operational health, and CI hardening

### Delivered

#### 🎛️ Web UI Configuration Panel ✅
- `/settings` route with Vesper UI styling
- Change target URL, scraping interval, proxy settings, circuit breaker thresholds
- `config.env` file-backed; no SSH required

#### 🗄️ SQLite Storage (v1.7.0) ✅
- `MagnetStore` with FTS5 full-text search replaced flat-file storage
- Schema migrations via `migrate.py`

#### 🔒 Authentication (v1.3.0) ✅
- Setup wizard, password protection, brute-force lockout
- IP allowlist, CSRF protection, audit log

#### 📊 Metrics Dashboard (v2.0.0) ✅
- Color-coded scrape history at `/metrics`
- 7/30-day counts, success rate
- `scrape_runs` table in SQLite

#### 🔍 Domain Resilience Probe (v2.0.0) ✅
- `probe_target()` classifies target as reachable / cloudflare_block / wrong_content / unreachable
- Cached result in `/health`; daemon warns at startup

#### 📈 Codecov Integration (v2.1.0) ✅
- Public coverage badge, per-PR delta reporting
- Coverage gate at 75%

---

## Rejected Ideas

These features were considered but rejected to keep BIND focused:

❌ **Keyword Filtering** - Use torrent client's RSS filters instead  
❌ **RSS Pagination** - 100 items is sufficient  
❌ **Multi-source Support** - Focused on AudioBookBay only  
❌ **Download Management** - That's the torrent client's job  

---

## Design Principles

1. **No Feature Creep** - Reject features that add complexity
2. **Delegate to Client** - Let torrent clients handle filtering/management
3. **Documentation > Code** - Explain well rather than over-engineer
4. **Stability > Features** - Don't fix what isn't broken

---

## Contributing

If you'd like to propose a feature:
1. Open a GitHub issue first
2. Explain the use case and why the torrent client can't handle it

---

**BIND v2.1 is feature-complete.**
