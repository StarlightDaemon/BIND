# Frequently Asked Questions

## General

### What is BIND?
BIND (Book Indexing Network Daemon) is an automated system that archives audiobook metadata from AudioBookBay. It collects magnet links, stores them in daily files, and serves them via RSS feed to your torrent client.

### Is this the same as BIND DNS server?
No. BIND DNS is a nameserver. This BIND is an audiobook archival tool. Completely different projects with the same acronym.

### Does BIND download audiobooks?
No. BIND only archives **metadata** (magnet links). Your torrent client downloads the actual audiobooks using those magnet links.

### Is BIND legal?
BIND archives publicly available metadata (magnet links), which is legal. However, downloading copyrighted content may not be legal in your jurisdiction. BIND is for archival and educational purposes only. Use responsibly.

---

## Installation

### What are the system requirements?
- **Minimum**: Any Linux system with Python 3.8+
- **Recommended**: Proxmox LXC with 4GB disk, 512MB RAM, 1 CPU core
- **Docker**: Docker + docker-compose

### Can I run this on Windows/Mac?
Not officially supported, but it should work with Python 3.8+ installed. Manual installation only (no one-click installer).

### How long does installation take?
~2 minutes on Proxmox LXC (automated installer).

### Can I customize the container specs during install?
Yes. The installer prompts for:
- Container ID
- Hostname
- Disk size
- RAM
- CPU cores
- Network (DHCP or static IP)

---

## Usage

### How often does BIND check for new audiobooks?
Every 60 minutes by default. Configurable by editing the systemd service file.

### Where are magnet links stored?
In the `magnets/` directory as daily text files:
- `magnets_2026-01-03.txt`
- `magnets_2026-01-04.txt`
- etc.

### How do I access the RSS feed?
Navigate to `http://YOUR-CONTAINER-IP:5050/feed.xml` in your torrent client's RSS reader.

### Can I change the RSS port?
Yes. Edit `/etc/systemd/system/bind-rss.service` and change the port, then:
```bash
systemctl daemon-reload
systemctl restart bind-rss.service
```

### How do I view collected magnets?
- **Web UI**: http://YOUR-CONTAINER-IP:5050/
- **Files**: `ls /opt/bind/magnets/`
- **RSS Feed**: http://YOUR-CONTAINER-IP:5050/feed.xml

---

## Storage

### How much disk space do I need?
- **Base install**: ~2GB (Debian + BIND + venv)
- **Per 100k magnets**: ~35-40MB
- **Recommended**: 4GB (provides safety margin)

### Will magnet files fill up my disk?
Unlikely. Even at 1 magnet per hour for a year, you'd only use ~12MB. You can also prune old files as needed.

### How do I clean up old magnet files?
```bash
cd /opt/bind/magnets
rm magnets_2025-*.txt  # Remove 2025 files
```

### Can I backup the magnets?
Yes! Just copy the `magnets/` directory:
```bash
cp -r /opt/bind/magnets /path/to/backup/
```

---

## Updates

### How do I update BIND?
```bash
pct enter <container-id>
cd /opt/bind
./update.sh
```

The script handles everything automatically.

### What if an update breaks something?
The update script creates git tags before updating. Rollback:
```bash
cd /opt/bind
git tag  # Find backup tag
git checkout backup-20260103-123456
systemctl restart bind.service bind-rss.service
```

### Can I test updates before applying?
Not currently. The update script updates in-place. Consider taking a container snapshot first:
```bash
pct snapshot <container-id> before-update
```

---

## Troubleshooting

### RSS feed shows no magnets
1. Check if daemon is running: `systemctl status bind.service`
2. Check if magnet files exist: `ls /opt/bind/magnets/`
3. Check daemon logs: `journalctl -u bind.service -f`

### Web UI not accessible
1. Check RSS service: `systemctl status bind-rss.service`
2. Check port is open: `ss -tulpn | grep 5050`
3. Check firewall rules (if any)

### Port 5050 already in use
Find what's using it:
```bash
ss -tulpn | grep 5050
```
Either stop that service or change BIND's port.

### Services won't start after reboot
Check if services are enabled:
```bash
systemctl is-enabled bind.service
systemctl is-enabled bind-rss.service
```

If not:
```bash
systemctl enable bind.service bind-rss.service
```

---

## Performance

### How much CPU does BIND use?
- Idle: <1%
- Scraping: ~5-10% (brief spike every 60 min)

### How much RAM does BIND use?
- Daemon: 50-100MB
- RSS server: 30-50MB
- Total: <150MB

### Does BIND slow down my system?
No. BIND is very lightweight and only scrapes once per hour.

### Can I run multiple instances?
Technically yes, but not recommended. Use one BIND instance per site/source.

---

## Torrent Clients

### Which torrent clients work with BIND?
Any client with RSS support:
- qBittorrent ✅
- BiglyBT ✅
- Transmission ✅
- Deluge ✅
- ruTorrent ✅

### How do I set up auto-download in qBittorrent?
1. View → RSS Reader (Alt+S)
2. Right-click → New subscription
3. Add feed URL: `http://BIND-IP:5050/feed.xml`
4. Right-click feed → Download Rule
5. Set filters and auto-download

### Can I filter which audiobooks to download?
Yes, in your torrent client's RSS rules. BIND provides all magnets; your client filters.

---

## Advanced

### Can I change the scraping interval?
Yes. Edit `/etc/systemd/system/bind.service`:
```ini
ExecStart=... daemon --interval 30 --output-dir /opt/bind/magnets
```
Change 30 to desired minutes.

### Can I add other audiobook sources?
Not without code changes. BIND is designed specifically for AudioBookBay. Adding other sources requires modifying the scraper.

### Can I run BIND on a different port?
Yes. Edit `bind-rss.service` and change the port. Don't forget to update firewall rules.

### Is there a Docker Compose file?
Yes! See `docker-compose.yml` in the repository.

### Can I expose BIND to the internet?
**Not recommended**. BIND has no authentication. If you must, use a reverse proxy with auth (nginx, Caddy).

---

## Development

### Can I contribute to BIND?
Yes! BIND is open source (MIT license). Pull requests welcome on GitHub.

### Where are the source files?
- `src/bind.py` - Main daemon
- `src/rss_server.py` - RSS server and web UI
- `src/core/scraper.py` - AudioBookBay scraper

### How do I run BIND for development?
```bash
git clone https://github.com/StarlightDaemon/BIND.git
cd BIND
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m src.bind daemon --interval 60 --output-dir magnets/
```

### Can I add features?
Yes! See `FUTURE_ENHANCEMENTS.md` for planned features.

---

## Miscellaneous

### Why is it called BIND?
**B**ook **I**ndexing **N**etwork **D**aemon. It archives (indexes) book metadata.

### Is BIND actively maintained?
Yes. Check GitHub for latest updates and releases.

### Where can I get help?
- Check [Troubleshooting](TROUBLESHOOTING.md)
- Check [Usage Guide](USAGE.md)
- Open a GitHub issue
- Review existing GitHub issues

### Can I donate/support the project?
BIND is a free, open-source homelab tool. No donations accepted. If you find it useful, star the repo on GitHub!
