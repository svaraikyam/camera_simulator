#!/usr/bin/env bash
###############################################################################
# MediaMTX RTSP Camera Simulator - Setup Script
# Checks dependencies, installs MediaMTX, and downloads sample AI videos.
###############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${BASE_DIR}"

echo "========================================================="
echo "   MediaMTX Industrial RTSP Camera Simulator Setup       "
echo "========================================================="

# 1. Check prerequisites
echo "[+] Checking system dependencies..."
for cmd in ffmpeg ffprobe python3 curl tar; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "[!] Error: '$cmd' is not installed. Please install it with: sudo apt update && sudo apt install -y $cmd"
        exit 1
    fi
    echo "    - $cmd: OK"
done

# 2. Ensure directories
mkdir -p bin config videos scripts

# 3. Download MediaMTX if not present
if [ ! -f "bin/mediamtx" ]; then
    echo "[+] Downloading MediaMTX v1.21.2..."
    ARCH="linux_amd64"
    MTX_URL="https://github.com/bluenviron/mediamtx/releases/download/v1.21.2/mediamtx_v1.21.2_${ARCH}.tar.gz"
    curl -L -s "${MTX_URL}" -o /tmp/mediamtx.tar.gz
    tar -xzf /tmp/mediamtx.tar.gz -C bin/ mediamtx
    chmod +x bin/mediamtx
    rm -f /tmp/mediamtx.tar.gz
    echo "    [OK] MediaMTX installed in bin/mediamtx"
else
    echo "[~] MediaMTX binary already exists in bin/mediamtx"
fi

# 4. Download sample videos
echo "[+] Checking and downloading sample videos..."
python3 scripts/download_samples.py

# 5. Make scripts executable
chmod +x scripts/*.py scripts/*.sh run.sh stop.sh 2>/dev/null || true

echo "========================================================="
echo "  [✓] Setup Complete!"
echo "  To start the simulator, run:  ./run.sh"
echo "  To manage or view streams:    python3 scripts/stream_manager.py list"
echo "========================================================="
