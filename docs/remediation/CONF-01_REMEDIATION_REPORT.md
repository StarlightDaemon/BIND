# CONF-01 Remediation Report

**Issue ID:** CONF-01 (Configuration Pipeline Broken)
**Status:** **RESOLVED**
**Date:** 2026-01-26

---

## 1. Remediation Summary

The configuration pipeline has been repaired to ensure that values written to `config.env` (e.g., by the Web UI) are correctly loaded and respected by the Daemon process. The hardcoded command-line arguments in the systemd service file have been removed, allowing environment variables to function as the primary source of configuration.

## 2. Changes Implemented

### A. Systemd Service Updates
**File:** `deployment/bind.service`
*   **Added:** `EnvironmentFile=-/opt/bind/config.env`
    *   This instructs systemd to load the configuration file into the process environment before starting.
*   **Modified:** `ExecStart`
    *   **Old:** `/opt/bind/venv/bin/python -m src.bind daemon --interval 60 --output-dir /opt/bind/magnets`
    *   **New:** `/opt/bind/venv/bin/python -m src.bind daemon`
    *   **Reason:** Removing hardcoded flags allows the application to fallback to environment variables.

### B. Application Logic Updates
**File:** `src/bind.py`
*   **Updated:** Click Option Binding
    *   `--interval` is now bound to `envvar='SCRAPE_INTERVAL'`
    *   `--output-dir` is now bound to `envvar='MAGNETS_DIR'`
*   **Added:** Environment Injection
    *   Explicitly loads `config.env` at startup to ensure manual runs (outside systemd) also respect the configuration file.

## 3. New Configuration Precedence

The system now follows a standard POSIX-style precedence order (Highest to Lowest):

1.  **Explicit CLI Flags:**
    *   Example: `python -m src.bind daemon --interval 15`
    *   Overrides everything else.
2.  **Environment Variables:**
    *   Loaded from `config.env` by systemd or the application itself.
    *   Example: `SCRAPE_INTERVAL=120` in `config.env`.
3.  **Application Defaults:**
    *   `interval`: 60 minutes
    *   `output-dir`: `magnets`

## 4. Verification

*   **Scenario:** User changes `SCRAPE_INTERVAL` to `120` in UI -> "Save & Restart".
*   **Result:**
    *   `config.env` is updated.
    *   Systemd restarts service, loading `SCRAPE_INTERVAL=120`.
    *   Daemon starts without `--interval` flag.
    *   `src.bind` picks up `SCRAPE_INTERVAL` from env.
    *   Scheduler runs every 120 minutes.

**CONF-01 is Fully Resolved.**
