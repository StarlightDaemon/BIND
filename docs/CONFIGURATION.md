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
Add a single HTTP/SOCKS5 proxy for scraping:
```ini
# Edit /etc/systemd/system/bind.service
Environment="BIND_PROXY=socks5://user:pass@proxy:1080"
```

For proxy rotation, set a comma-separated list via `BIND_PROXIES`.
`BIND_PROXIES` takes precedence over `BIND_PROXY` when both are set:
```ini
Environment="BIND_PROXIES=socks5://proxy1:1080,socks5://proxy2:1080"
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

### Job Timeout
Prevent a hung scrape job from blocking the scheduler indefinitely:
```ini
# Edit /etc/systemd/system/bind.service
Environment="BIND_JOB_TIMEOUT=3600"    # Seconds before the scheduler moves on
```
Default is 3600 seconds (1 hour). After a timeout the scheduler continues
normally; the timed-out job finishes in the background.

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
ExecStart=/opt/bind/venv/bin/python -m src.bind daemon --interval 30 --output-dir /opt/bind/data/magnets
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

## RSS Feed Authentication

`/feed.xml` is **intentionally unauthenticated**. RSS consumers (torrent clients, feed readers)
cannot participate in session-cookie authentication, so requiring a session would break
every downstream client. Instead, `/feed.xml` is protected solely by the IP allowlist
(`BIND_IP_FILTER` / `BIND_ALLOWED_IPS`). Restrict the allowlist to trusted IPs or a
reverse-proxy address to limit who can reach the feed.

All JSON API endpoints under `/api/` (except `/api/login`, `/api/logout`, `/api/me`,
`/api/csrf-token`, and the first-time setup routes) require a valid session cookie.

### Trusted Proxies (`BIND_TRUSTED_PROXIES`)

The IP allowlist evaluates the *real* client IP. When BIND runs behind a reverse
proxy, the real client is carried in the `X-Forwarded-For` (XFF) header, but XFF
can be forged by anyone who can reach the proxy. BIND only trusts XFF hops that
come from a configured trusted-proxy set.

| Key | Default | Format |
|-----|---------|--------|
| `BIND_TRUSTED_PROXIES` | `127.0.0.1/32,::1/128` | Comma-separated CIDRs / IPs |

**Default behavior:** when unset, only loopback (`127.0.0.1`, `::1`) is trusted —
identical to BIND's historical behavior. This is correct for the common
loopback-proxy path (Cloudflare Tunnel → nginx on the same host → gunicorn).

**Parsing model (rightmost-untrusted):** BIND builds the chain
`[XFF entries…, TCP peer]` and walks it from the right, skipping every hop inside
`BIND_TRUSTED_PROXIES`. The first untrusted hop is treated as the real client.
This defeats both XFF spoofing (an attacker prepending a fake IP) and the
containerized-proxy fail-open mode (where the proxy's private IP would otherwise
be treated as every visitor).

**When to set it:**
- **Containerized / Docker-network proxy** (proxy in a separate container, or
  Docker's userland proxy): the TCP peer is the proxy's RFC-1918 address, not
  loopback. Add that source range, e.g. `BIND_TRUSTED_PROXIES=172.18.0.0/16`.
- **Cloudflare Tunnel:** put the `cloudflared` connector's source range in this
  key if it is not loopback. For Cloudflare deployments, the
  `CF-Connecting-IP` header is a more reliable single-hop source of the client
  IP than parsing XFF, and is a candidate for future first-class support.

A malformed XFF entry encountered during the walk is returned verbatim and fails
the allowlist (fail-closed), so the request is denied and the audit log records
exactly what the upstream sent.

`BIND_TRUSTED_PROXIES` is an admin-managed environment variable: set it in
`config.env` or the systemd unit. It is read from the environment at request time
and is intentionally **not** editable from the Settings UI.

### Secure Session Cookie (`BIND_COOKIE_SECURE`)

Controls the `Secure` attribute on the session cookie. When `true`, browsers only
send the cookie over HTTPS, never over a plain-HTTP hop.

| Key | Default | Format |
|-----|---------|--------|
| `BIND_COOKIE_SECURE` | `false` | `true` / `false` |

**Default (`false`)** suits the common LAN-over-HTTP homelab deployment, where the
session cookie must be sent over plain HTTP.

**Set `true`** if you front BIND with TLS — e.g. a Cloudflare Tunnel, an HTTPS
reverse proxy, or any setup where the browser reaches BIND over `https://`.
Without it, the session cookie can leak over an accidental plain-HTTP hop. Like
`BIND_TRUSTED_PROXIES`, this key is admin-managed (set it in `config.env` or the
unit) and is intentionally **not** editable from the Settings UI; a UI save
preserves whatever value is already on disk.

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
