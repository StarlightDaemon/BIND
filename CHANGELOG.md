# Changelog

All notable changes to BIND will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-09

### Added
- Initial production release of BIND (Book Indexing Network Daemon)
- Automated daemon for AudioBookBay metadata scraping (60-minute intervals)
- RSS 2.0 feed generation with valid XML
- Web UI with gradient design for magnet link viewing
- Health monitoring endpoint (`/health`)
- Proxmox LXC one-line installer script
- Comprehensive documentation (README, ARCHITECTURE, FAQ, TROUBLESHOOTING)
- systemd service definitions for daemon and RSS server
- Docker and docker-compose support
- Daily magnet file rotation for archival

### Changed
- **BREAKING**: Renamed from ABMG (AudioBookBay Magnet Grabber) to BIND
- Renamed `AbmgScraper` class to `BindScraper`
- Updated all documentation to reflect BIND branding

### Fixed
- Pinned all Python dependencies to specific versions for reproducible builds:
  - `cloudscraper==1.2.71`
  - `beautifulsoup4==4.12.3`
  - `click==8.1.7`
  - `lxml==6.0.2`
  - `schedule==1.2.2`
  - `flask==3.0.0`

### Security
- Unprivileged LXC container deployment by default
- No authentication (designed for private LAN use only)
- Clear security warnings in documentation

## [Unreleased]

### Planned for v1.1 (Optional)
- Screenshots in README
- Example RSS feed XML
- Video walkthrough of setup

### Planned for v2.0 (Future)
- Multi-platform support (Docker Hub, Unraid, TrueNAS, Synology, Home Assistant)
- See `docs/ROADMAP_v2.0.md` for detailed plans

---

## Release Notes Format

### Added
New features or functionality

### Changed
Changes to existing functionality

### Deprecated  
Features that will be removed in future releases

### Removed
Features that have been removed

### Fixed
Bug fixes

### Security
Security-related changes
