#!/bin/bash
set -e

echo "============================================"
echo "  File Encryption Tool - Starting up"
echo "============================================"

# Create a virtual environment on first run only
if [ ! -d "venv" ]; then
    echo "Setting up environment for the first time, this may take a minute..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip >/dev/null
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "Launching app - your browser will open automatically..."
python3 app.py