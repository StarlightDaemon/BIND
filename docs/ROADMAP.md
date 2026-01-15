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

## v2.0 - Feature Expansion (Future)

**Focus**: Enhanced user experience and advanced features

### Planned Features

#### 🎛️ Web UI Configuration Panel
**Priority**: High  
**Complexity**: Medium  
**Description**: Settings page for runtime configuration changes without SSH access

**Features:**
- Change target URL (ABB_URL)
- Adjust scraping interval
- Configure proxy settings  
- Modify circuit breaker thresholds
- Set RSS base URL override

**Implementation:**
- `config.env` file with systemd `EnvironmentFile` directive
- `/settings` route in Flask with Vesper UI styling
- Input validation and error handling
- Auto-restart daemon on save

**Estimated Effort:** 12-15 hours

**See:** `docs/research/web_ui_config_plan.md` for detailed implementation plan

---

#### 📊 Enhanced Metrics Dashboard
**Priority**: Medium  
**Complexity**: Medium  
**Description**: Visual dashboard for monitoring BIND's operation and performance

**Features:**
- Scrape success/failure rates
- Last successful scrape timestamp
- Number of items processed
- RSS feed generation time
- System resource usage (CPU, memory)

**Implementation:**
- Integrate with Prometheus/Grafana or simple Flask-based dashboard
- Expose metrics via `/metrics` endpoint
- Historical data visualization

**Estimated Effort:** 8-10 hours

---

**Status**: Planned  
**Goal**: Universal self-hosted application

v2.0 will expand **distribution** (how users install BIND) AND features (what BIND does).

See [`docs/ROADMAP_v2.0.md`](ROADMAP_v2.0.md) for detailed multi-platform strategy.

**Core Principles**:
- Keep v1.0 Proxmox deployment supported
- Container-first architecture
- No feature bloat - same core functionality
- Universal Docker image powers most platforms

**Timeline**: TBD based on community demand

---

## Rejected Ideas

These features were considered but rejected to keep BIND focused:

❌ **Keyword Filtering** - Use torrent client's RSS filters instead  
❌ **Magnet Deduplication** - Not needed with daily files  
❌ **RSS Pagination** - 100 items is sufficient  
❌ **Database Storage** - Files are simpler and more reliable  
❌ **Web Authentication** - Use reverse proxy if needed  
❌ **Multi-source Support** - Focused on AudioBookBay only  
❌ **Download Management** - That's the torrent client's job  
❌ **Search Interface** - RSS feed is the interface  

---

## Design Principles Going Forward

1. **No Feature Creep** - Reject features that add complexity
2. **Delegate to Client** - Let torrent clients handle filtering/management
3. **Simple > Complex** - Daily text files > databases
4. **Documentation > Code** - Explain well rather than over-engineer
5. **Stability > Features** - Don't fix what isn't broken

---

## Contributing

If you'd like to propose a feature:
1. Open a GitHub issue first
2. Explain the use case
3. Why the torrent client can't handle it
4. Why it can't be a separate tool

We'll likely say no to maintain BIND's focus, but we're happy to discuss!

---

**BIND v1.0 is feature-complete.**

Future work: v1.x = maintenance only, v2.x = multi-platform distribution.
