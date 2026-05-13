#!/bin/sh
set -e

python -m src.bind daemon --interval "${BIND_SCRAPE_INTERVAL:-60}" &

exec gunicorn --workers 2 --bind 0.0.0.0:5050 --timeout 30 src.rss_server:app
