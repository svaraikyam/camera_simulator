#!/usr/bin/env bash
###############################################################################
# Run Script for MediaMTX RTSP Camera Simulator
# Starts the streaming server in the background and prints connection URLs.
###############################################################################

set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${BASE_DIR}"

# Run setup if bin/mediamtx or videos are missing
if [ ! -f "bin/mediamtx" ] || [ ! -f "videos/ppe_detection.mp4" ]; then
    echo "[!] Initial setup detected. Running setup..."
    bash scripts/setup.sh
fi

# Prefer virtual environment python if available
PYTHON="python3"
if [ -f ".venv/bin/python3" ]; then
    PYTHON=".venv/bin/python3"
fi

# Use stream_manager.py to start cleanly
$PYTHON scripts/stream_manager.py start
