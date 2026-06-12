#!/bin/bash
# Single-container supervisor: run the daemon and gunicorn together. If either
# exits, stop the other and exit non-zero so Docker's restart policy recycles
# the pair (DEP-6). The scrape interval comes from SCRAPE_INTERVAL (env/config),
# not a hardcoded flag (ARCH-6). tini is PID 1 and forwards signals to this
# script; the trap re-forwards them to both children for a graceful drain.

term() {
  kill -TERM "$daemon_pid" "$gunicorn_pid" 2>/dev/null || true
}
trap term TERM INT

python -m src.bind daemon &
daemon_pid=$!

gunicorn --workers 2 --bind 0.0.0.0:5050 --timeout 30 src.rss_server:app &
gunicorn_pid=$!

# Wait for whichever process exits first and capture its status.
wait -n "$daemon_pid" "$gunicorn_pid"
status=$?

# Stop the survivor and reap it, then propagate the failed child's status.
kill -TERM "$daemon_pid" "$gunicorn_pid" 2>/dev/null || true
wait 2>/dev/null || true

exit "$status"
