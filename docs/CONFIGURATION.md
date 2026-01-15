# BIND Configuration Guide

BIND uses **environment variables** for all configuration. No web UI needed - just edit the systemd service files.

## Configuration Location

**Inside the container:**
```bash
/etc/systemd/system/bind.service       # Daemon config
/etc/systemd/system/bind-rss.service   # RSS server config
```

## Available Settings

### Target Domain
Change the audiobook site URL (if it moves domains):
```ini
# Edit /etc/systemd/system/bind.service
Environment="ABB_URL=http://audiobookbay.new-domain"
```

### Proxy Settings
Add HTTP/SOCKS5 proxy for scraping:
```ini
# Edit /etc/systemd/system/bind.service
Environment="BIND_PROXY=socks5://user:pass@proxy:1080"
```

### RSS Server Base URL
Override auto-detected RSS feed URLs:
```ini
# Edit /etc/systemd/system/bind-rss.service
Environment="BASE_URL=http://bind.mydomain.com"
```

### Web UI / RSS Port
Change the listening port (default: 5050) if conflicts occur:
```ini
# Edit /etc/systemd/system/bind-rss.service
Environment="PORT=8080"
```

### Magnet Storage Directory
Change where magnet files are saved:
```ini
# Edit /etc/systemd/system/bind.service
Environment="MAGNETS_DIR=/custom/path/magnets"
```

### Circuit Breaker Settings
Fine-tune Cloudflare resilience:
```ini
# Edit /etc/systemd/system/bind.service
Environment="CIRCUIT_BREAKER_THRESHOLD=5"      # Failures before tripping
Environment="CIRCUIT_BREAKER_COOLDOWN=600"     # Seconds to wait
```

## How to Apply Changes

1. **Edit the service file:**
   ```bash
   pct enter <CTID>
   nano /etc/systemd/system/bind.service
   ```

2. **Reload systemd:**
   ```bash
   systemctl daemon-reload
   ```

3. **Restart the service:**
   ```bash
   systemctl restart bind
   # or for RSS changes:
   systemctl restart bind-rss
   ```

4. **Verify:**
   ```bash
   systemctl status bind
   journalctl -u bind -f
   ```

## Quick Examples

### Change Scraping Interval
Edit the service file and modify the `ExecStart` line:
```ini
# Default: scrapes every 60 minutes
ExecStart=/opt/bind/venv/bin/python -m src.bind daemon --interval 30 --output-dir /opt/bind/magnets
```

### Enable Proxy
```bash
pct enter <CTID>
nano /etc/systemd/system/bind.service

# Add this line under [Service]:
Environment="BIND_PROXY=http://proxy.example.com:8080"

# Reload and restart:
systemctl daemon-reload
systemctl restart bind
```

### Change Target Site
```bash
pct enter <CTID>
nano /etc/systemd/system/bind.service

# Add this line under [Service]:
Environment="ABB_URL=http://new-audiobook-site.com"

# Reload and restart:
systemctl daemon-reload
systemctl restart bind
```

## See Current Configuration

View active environment variables:
```bash
systemctl show bind --property=Environment
```

View complete service file:
```bash
systemctl cat bind
```

---

**Note**: All changes require systemd reload + service restart to take effect. Configuration is persistent across reboots.
