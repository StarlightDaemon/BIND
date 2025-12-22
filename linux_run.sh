#!/bin/bash
set -e

echo "--- ABMG Linux Setup ---"

# 1. Create venv if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 2. Activate venv
source venv/bin/activate

# 3. Install deps
echo "Installing dependencies..."
pip install -r requirements.txt

# 4. Run Daemon
echo "Starting Daemon..."
export PYTHONPATH=$(pwd)
python src/abmg.py daemon
