# DOC-01 Documentation Parity Update

## Summary of Documentation Changes

To align the BIND documentation with the v1.2.1 implementation and the remediation of CONF-01, the `README.md` has been updated to accurately reflect the system's capabilities. The previous documentation contained drift, effectively describing a legacy or theoretical version of the system rather than the actual deployed artifact.

## Authentication Documentation Updates

**Previous State (Drifted):**
> "BIND has no authentication and is designed for private LAN use only."

**New State (Parity):**
> "BIND includes a built-in authentication system (Setup Wizard, Password Protection, Bruteforce Lockout)."

**Rationale:**
The source code (`src/security.py`, `src/rss_server.py`) implements a complete Basic Auth flow, including a first-run setup wizard for credentials, bcrypt limits, and lockout policies. The previous statement was factually incorrect and potentially dangerous if it discouraged users from utilizing the built-in protections.

## Configuration Documentation Updates

**Previous State (Drifted):**
Documentation suggested editing systemd unit files manually to set environment variables was the primary configuration method, and implied that the Web UI settings might not persist effectively (a known bug, CONF-01, now fixed).

**New State (Parity):**
A clear precedence order has been established and documented:
1.  **CLI Flags**: Highest priority (manual override).
2.  **Environment Variables**: The standard operating mode (`config.env`).
3.  **Defaults**: Fallback values.

The "To change configuration" section now explicitly prioritizes the Web UI (`http://YOUR-IP:5050/settings`) as the recommended method, aligning with the CONF-01 fix which ensures these changes are respected by the backend.

## Verification Notes

- **README.md**: Lines 26 and 206+ have been modified.
- **Accuracy**: The `Configuration Sources` section now matches the logic implemented in `src/bind.py` (CLI > Env > Default).
- **Safety**: The security note still recommends a reverse proxy for public internet exposure (defense in depth), but correctly acknowledges the existence of application-layer auth.

Documentation no longer contradicts implementation.
