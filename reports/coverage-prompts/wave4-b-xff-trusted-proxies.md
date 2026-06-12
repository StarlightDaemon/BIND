# Wave 4-B — XFF Trust Model: Rightmost-Untrusted Parsing

**Model: Claude Opus**
**No dependencies** — no prereqs, but do NOT run concurrently with Wave 4-C (both edit `src/security.py`; different regions, same file).
**Working directory:** `/Users/dante/Citadel/BIND`
**Activate the venv before any shell commands:** `source .venv/bin/activate`
**Finding remediated:** SEC-3 from `BIND_FULL_AUDIT_REPORT.md` (repo root — read it in full first).

## Why Opus for this task

Trust-chain parsing is classically easy to get subtly wrong: off-by-one on chain direction, trusting the wrong end, or mishandling malformed entries each silently re-opens the spoofing hole. The fix must be proven against three distinct network topologies.

## The bug (two failure modes)

`get_client_ip()` (`src/security.py:454-472`) trusts `X-Forwarded-For` only when the TCP peer is loopback, then takes the **first** element.

1. **Loopback proxy** (Cloudflare Tunnel → nginx on the same host → gunicorn): nginx `$proxy_add_x_forwarded_for` and Cloudflare both *append* to the client-supplied XFF, so the first element is **attacker-controlled**. `X-Forwarded-For: 192.168.1.10` from the internet returns a private IP → IP allowlist bypassed, audit log forged.
2. **Containerized proxy** (proxy in another container / Docker userland proxy): TCP peer is the proxy's RFC-1918 address — not loopback — so XFF is ignored AND every visitor is evaluated as the proxy's private IP → the allowlist passes everyone.

## Required behavior

Implement **rightmost-untrusted** parsing with a configurable trusted-proxy set:

1. New env/config key `BIND_TRUSTED_PROXIES`: comma-separated CIDRs. Default `"127.0.0.1/32,::1/128"` — **exactly preserves current behavior when unset**. Read it the same way `BIND_ALLOWED_IPS` is read (env at request time via `os.getenv`, parsed/cached sensibly — a module-level parse cache invalidated on value change is fine).
2. Algorithm in `get_client_ip()`:
   - If the direct peer (`request.remote_addr`) is NOT in the trusted set → return the peer (unchanged from today).
   - If it IS trusted → build the chain `[XFF entries..., peer]` and walk **from the right**, skipping every address inside the trusted set; return the first untrusted address encountered.
   - If the entire chain is trusted (or XFF is empty) → return the leftmost XFF entry if present, else the peer.
   - Malformed entry (unparseable as an IP) encountered during the walk → **stop and return it verbatim**. This is safe because `is_ip_allowed` already returns `False` for unparseable input (`src/security.py:432-434`) — the request is denied, and the audit log records what was actually sent. Confirm that behavior with a test rather than assuming it; document the choice in the docstring.
3. Add `BIND_TRUSTED_PROXIES` to `ConfigManager.DEFAULTS` and `VALIDATORS` (`src/config_manager.py:19-47`) with a `cidr_list` validator (new validator type, modeled on `proxy_list`). Do NOT add it to the Settings UI — it is an admin-managed key; the existing preserved-keys mechanism (`config_manager.py:122-137`) already round-trips it. **Caution:** once it is in `DEFAULTS`, `write_config` will emit it on every save — verify the default value survives a UI settings save unchanged (see the BIND_DB_PATH clobber bug, ARCH-4, for the failure shape; your addition must not recreate it — the route builds its payload from a fixed dict, so carry the key through from `read_config()` in `api_settings_post` (`src/rss_server.py:533-545`) the same way ARCH-4's fix will for BIND_DB_PATH, OR keep the key out of DEFAULTS entirely and read it from env only — choose the env-only route if the clobber interaction looks risky; document the decision in your summary).
4. Update the docstring and `docs/CONFIGURATION.md` (new key, default, and a note that Cloudflare users should put their tunnel/connector's source range in it, with `CF-Connecting-IP` mentioned as the more reliable alternative header for future work).

## Tests (append to `tests/test_security.py`, do not modify existing tests)

Cover at minimum, using a mock request object (pattern exists in the file already):

| Topology | peer | XFF | trusted set | expected |
|---|---|---|---|---|
| No proxy | `203.0.113.7` | `192.168.1.1` (spoof attempt) | default | `203.0.113.7` |
| Loopback nginx, honest client | `127.0.0.1` | `203.0.113.7` | default | `203.0.113.7` |
| Loopback nginx, spoofing client | `127.0.0.1` | `192.168.1.10, 203.0.113.7` | default | `203.0.113.7` ← the fix |
| Container proxy | `172.18.0.5` | `203.0.113.7` | `172.18.0.0/16` | `203.0.113.7` ← the fix |
| Container proxy + spoof | `172.18.0.5` | `10.0.0.1, 203.0.113.7` | `172.18.0.0/16` | `203.0.113.7` |
| Chain fully trusted | `127.0.0.1` | `127.0.0.1` | default | `127.0.0.1` |
| Empty XFF, trusted peer | `127.0.0.1` | (none) | default | `127.0.0.1` |
| Malformed XFF entry | `127.0.0.1` | `garbage, 203.0.113.7` | default | per your documented choice |

Also assert: spoofed-private-IP case no longer passes `is_ip_allowed` end-to-end (one Flask test-client request with `environ_base={"REMOTE_ADDR": ...}` and the XFF header, asserting 403).

## Constraints

- Touch only `src/security.py`, `src/config_manager.py` (optional, per your DEFAULTS decision), `src/rss_server.py` (only if carrying the key through settings), `tests/test_security.py`, `tests/test_config_manager.py` (validator test), `docs/CONFIGURATION.md`.
- Behavior with `BIND_TRUSTED_PROXIES` unset must be byte-identical to today for the loopback-honest-client and no-proxy cases.

## Verification

```bash
source .venv/bin/activate
python -m pytest tests/test_security.py tests/test_config_manager.py -q
python -m pytest tests/ -q
ruff check src/ tests/ && mypy src/
```

## Done criteria

All eight topology cases pass; the two "← the fix" rows fail against the pre-change code (verify by stashing once); full suite green.
