#!/usr/bin/env bash
###############################################################################
# Live Log Viewer for MediaMTX RTSP Camera Simulator
# Displays live events when clients open or close RTSP / WebRTC streams.
###############################################################################

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${BASE_DIR}"

PYTHON="python3"
if [ -f ".venv/bin/python3" ]; then
    PYTHON=".venv/bin/python3"
fi

$PYTHON scripts/stream_manager.py logs "$@"
