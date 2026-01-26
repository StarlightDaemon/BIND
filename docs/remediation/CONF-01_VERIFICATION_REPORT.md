# CONF-01 Verification Report

## Scenario Walkthrough

**STEP 1: User Action**
User sets `SCRAPE_INTERVAL=120` via the Web UI.

**STEP 2: Write to Disk**
System writes to `/opt/bind/config.env`:
`SCRAPE_INTERVAL=120`

**STEP 3: Restart Mechanism**
The application executes `systemctl restart bind.service`.

**STEP 4: Service Configuration Loading**
Systemd reads the `bind.service` unit.
*   **Directive:** `EnvironmentFile=-/opt/bind/config.env`
*   **Result:** The process environment is populated with `SCRAPE_INTERVAL=120`.

**STEP 5: Runtime Execution Arguments**
Systemd executes the start command.
*   **Command:** `/opt/bind/venv/bin/python -m src.bind daemon`
*   **Observation:** The command contains **NO** `--interval` flag.

**STEP 6: Click Option Resolution**
The `daemon` function in `src/bind.py` is invoked.
*   **Decorator:** `@click.option('--interval', envvar='SCRAPE_INTERVAL', ...)`
*   **Resolution:** Click checks for `--interval` flag (absent). Click checks for `SCRAPE_INTERVAL` env var (present: `120`).
*   **Result:** `interval` variable is set to `120`.

**STEP 7: Scheduling**
The daemon logic executes.
*   **Code:** `schedule.every(interval).minutes.do(job)`
*   **Result:** Scheduler is configured for **120 minutes**.

## Evidence Map

| Component | File Path | Line Reference | Observed State |
| :--- | :--- | :--- | :--- |
| **Service Env** | `deployment/bind.service` | Line 11 | `EnvironmentFile=-/opt/bind/config.env` |
| **Service Args** | `deployment/bind.service` | Line 12 | `ExecStart=... src.bind daemon` (Clean) |
| **Env Binding** | `src/bind.py` | Line 70 | `envvar='SCRAPE_INTERVAL'` |
| **Defaulting** | `src/bind.py` | Line 70 | `default=60` (Ignored when envvar present) |

## Verification Result

CONF-01 VERIFIED
