#!/usr/bin/env python3
"""
MediaMTX RTSP Camera Simulator - Stream Manager CLI
Manage industrial AI video streams, add new videos, detect LAN IPs, and control the simulator.
"""

import os
import sys
import argparse
import subprocess
import socket
import json
import shutil
import time
import signal
import urllib.request

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BIN_PATH = os.path.join(BASE_DIR, "bin", "mediamtx")
CONFIG_PATH = os.path.join(BASE_DIR, "config", "mediamtx.yml")
VIDEOS_DIR = os.path.join(BASE_DIR, "videos")
PID_FILE = os.path.join(BASE_DIR, ".mediamtx.pid")
LOG_FILE = os.path.join(BASE_DIR, "mediamtx.log")

def get_lan_ip():
    """Detects primary LAN IP for sharing RTSP URLs with remote PCs."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        # Using a public DNS address to determine outgoing interface without actually sending packets
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    
    # Fallback to hostname resolution
    try:
        host_ips = socket.gethostbyname_ex(socket.gethostname())[2]
        for ip in host_ips:
            if not ip.startswith("127."):
                return ip
    except Exception:
        pass

    return "127.0.0.1"

def is_server_running():
    """Checks if MediaMTX process is running."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            # Check if PID is alive
            os.kill(pid, 0)
            return pid
        except (OSError, ValueError):
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
    
    # Secondary check using pgrep
    try:
        res = subprocess.run(["pgrep", "-f", "mediamtx config/mediamtx.yml"], stdout=subprocess.PIPE, text=True)
        if res.stdout.strip():
            pids = res.stdout.strip().split()
            return int(pids[0])
    except Exception:
        pass
    return None

def start_server():
    """Starts MediaMTX in background."""
    pid = is_server_running()
    if pid:
        print(f"[!] MediaMTX is already running (PID: {pid}).")
        return

    if not os.path.isfile(BIN_PATH) or not os.access(BIN_PATH, os.X_OK):
        print(f"[!] Binary not found or not executable at {BIN_PATH}")
        print("    Run ./scripts/setup.sh to download MediaMTX.")
        sys.exit(1)

    print("[+] Starting MediaMTX RTSP Camera Simulator...")
    log_f = open(LOG_FILE, "a")
    try:
        proc = subprocess.Popen(
            [BIN_PATH, CONFIG_PATH],
            cwd=BASE_DIR,
            stdin=subprocess.DEVNULL,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        pid = proc.pid
        with open(PID_FILE, "w") as f:
            f.write(str(pid))
    except Exception as e:
        print(f"[x] Failed to start MediaMTX: {e}")
        sys.exit(1)

    time.sleep(1.5)
    # Check if process is still alive
    if not is_server_running():
        print(f"[x] MediaMTX stopped unexpectedly. Check {LOG_FILE} for details.")
        sys.exit(1)

    lan_ip = get_lan_ip()
    print(f"[✓] MediaMTX is running in background (PID: {pid})")
    print(f"    RTSP Server:  0.0.0.0:8554 (LAN IP: {lan_ip})")
    print(f"    WebRTC Server: 0.0.0.0:8889")
    print(f"    Logs:         {LOG_FILE}\n")
    list_streams()

def stop_server():
    """Stops the running MediaMTX instance and associated ffmpeg processes."""
    pid = is_server_running()
    if not pid:
        print("[!] MediaMTX is not currently running.")
        return

    print(f"[+] Stopping MediaMTX (PID: {pid})...")
    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    except Exception:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass

    time.sleep(1)
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

    # Clean up any orphan ffmpeg streaming loops for this server
    try:
        subprocess.run(["pkill", "-f", "ffmpeg -re -stream_loop"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    print("[✓] Server stopped successfully.")

def get_available_videos():
    """Scans videos/ directory for media files."""
    if not os.path.exists(VIDEOS_DIR):
        return []
    valid_exts = {".mp4", ".mkv", ".avi", ".mov", ".ts", ".flv"}
    files = []
    for f in sorted(os.listdir(VIDEOS_DIR)):
        ext = os.path.splitext(f)[1].lower()
        if ext in valid_exts and not f.startswith("temp_"):
            files.append(f)
    return files

def query_api_paths():
    """Queries MediaMTX REST API for live path info if running."""
    try:
        req = urllib.request.Request("http://127.0.0.1:9997/v3/paths/list")
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            data = json.loads(resp.read().decode())
            items = data.get("items", [])
            live_map = {}
            for item in items:
                name = item.get("name")
                ready = item.get("ready", False)
                readers = len(item.get("readers", []))
                live_map[name] = {"ready": ready, "readers": readers}
            return live_map
    except Exception:
        return {}

def list_streams():
    """Prints all configured and dynamic RTSP stream endpoints."""
    lan_ip = get_lan_ip()
    pid = is_server_running()
    status_str = f"ONLINE (PID {pid})" if pid else "OFFLINE"

    print("=========================================================================================")
    print(f"               MEDIA MTX RTSP CAMERA SIMULATOR - STREAM DIRECTORY")
    print(f"  Server Status: {status_str} | Host LAN IP: {lan_ip} | RTSP Port: 8554")
    print("=========================================================================================")

    predefined_paths = [
        ("ppe", "videos/ppe_detection.mp4", "PPE Detection (Helmets, Safety Vests, PPE AI)"),
        ("fire-smoke", "videos/fire_smoke_detection.mp4", "Fire & Smoke Detection (Hazard/Flame AI)"),
        ("industrial-iot", "videos/industrial_iot.mp4", "Industrial IoT / Facility Surveillance"),
    ]

    api_info = query_api_paths() if pid else {}

    print(f"{'STREAM NAME':<18} | {'LOCAL RTSP URL':<32} | {'REMOTE PC RTSP URL (LAN)':<36}")
    print("-" * 92)

    for stream_name, rel_file, desc in predefined_paths:
        file_path = os.path.join(BASE_DIR, rel_file)
        exists = "[Available]" if os.path.exists(file_path) else "[Missing File]"
        local_url = f"rtsp://127.0.0.1:8554/{stream_name}"
        remote_url = f"rtsp://{lan_ip}:8554/{stream_name}"
        webrtc_url = f"http://{lan_ip}:8889/{stream_name}"

        live_tag = ""
        if stream_name in api_info and api_info[stream_name]["ready"]:
            readers = api_info[stream_name]["readers"]
            live_tag = f" [LIVE • {readers} viewers]"

        print(f" {stream_name:<17} | {local_url:<32} | {remote_url:<36}{live_tag}")
        print(f"   ↳ Description: {desc} {exists}")
        print(f"   ↳ WebRTC / Browser URL: {webrtc_url}")
        print()

    # Dynamic on-demand videos in videos/ folder
    all_videos = get_available_videos()
    predefined_filenames = {os.path.basename(f) for _, f, _ in predefined_paths}
    other_videos = [v for v in all_videos if v not in predefined_filenames]

    if other_videos:
        print("-" * 92)
        print(" DYNAMIC ON-DEMAND STREAMS (Auto-converted from videos/ directory):")
        for vid in other_videos:
            stem = os.path.splitext(vid)[0]
            local_url = f"rtsp://127.0.0.1:8554/{stem}"
            remote_url = f"rtsp://{lan_ip}:8554/{stem}"
            webrtc_url = f"http://{lan_ip}:8889/{stem}"
            print(f" {stem:<17} | {local_url:<32} | {remote_url:<36}")
            print(f"   ↳ File: videos/{vid}")
            print(f"   ↳ WebRTC / Browser URL: {webrtc_url}")
            print()

    print("=========================================================================================")
    print(" QUICK CONNECT GUIDE FOR OTHER PC ON SAME NETWORK:")
    print(f" 1. Web Browser (Instant WebRTC - zero install):")
    print(f"    Navigate to: http://{lan_ip}:8889/ppe/  (or /fire-smoke/ or /industrial-iot/)")
    print(f" 2. VLC Media Player:")
    print(f"    • RTSP Stream: rtsp://{lan_ip}:8554/ppe  (Do NOT add trailing slash '/')")
    print(f"      (Settings Tip: In VLC Tools -> Preferences -> All -> Demuxers -> RTP/RTSP, check 'Use RTP over RTSP (TCP)')")
    print(f"    • HLS Stream (Works on all platforms): http://{lan_ip}:8888/ppe/index.m3u8")
    print(f" 3. FFplay (Command-line player):")
    print(f"    ffplay -rtsp_transport tcp rtsp://{lan_ip}:8554/ppe")
    print(f" 4. OpenCV / Python AI Script:")
    print(f'    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"')
    print(f'    cap = cv2.VideoCapture("rtsp://{lan_ip}:8554/ppe")')
    print("=========================================================================================\n")

def add_video(src_path: str, stream_name: str = None):
    """Adds a new downloaded video file and converts it if needed."""
    if not os.path.exists(src_path):
        print(f"[!] Error: Source file not found: {src_path}")
        sys.exit(1)

    filename = os.path.basename(src_path)
    stem, ext = os.path.splitext(filename)
    stream_name = stream_name or stem

    # Normalize name (replace spaces/special chars with hyphens)
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in stream_name)
    target_mp4 = f"{safe_name}.mp4"
    dest_path = os.path.join(VIDEOS_DIR, target_mp4)

    os.makedirs(VIDEOS_DIR, exist_ok=True)

    print(f"[+] Processing input video: {src_path}")
    print(f"    Target stream name: {safe_name}")
    print(f"    Target file: {dest_path}")

    # Check if already H.264 MP4
    is_h264 = False
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", src_path],
            stdout=subprocess.PIPE, text=True, check=True
        )
        if "h264" in probe.stdout.lower() and ext.lower() == ".mp4":
            is_h264 = True
    except Exception:
        pass

    if is_h264 and os.path.abspath(src_path) != os.path.abspath(dest_path):
        print("    File is already H.264 MP4. Copying directly...")
        shutil.copy2(src_path, dest_path)
    elif not is_h264:
        print("    Transcoding to RTSP-optimized H.264 MP4 using ffmpeg...")
        cmd = [
            "ffmpeg", "-y", "-i", src_path,
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-an", dest_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    lan_ip = get_lan_ip()
    print(f"\n[✓] Video successfully added!")
    print(f"    Stream is immediately live on-demand at:")
    print(f"    Local RTSP:      rtsp://127.0.0.1:8554/{safe_name}")
    print(f"    Remote PC (LAN): rtsp://{lan_ip}:8554/{safe_name}")
    print(f"    Web Browser:     http://{lan_ip}:8889/{safe_name}")

def test_stream(stream_name: str):
    """Probes a stream using ffprobe to verify video packets."""
    url = f"rtsp://127.0.0.1:8554/{stream_name}"
    print(f"[+] Probing stream: {url} via TCP transport...")
    cmd = [
        "ffprobe", "-v", "error", "-rtsp_transport", "tcp",
        "-show_entries", "stream=codec_name,width,height,r_frame_rate",
        "-of", "default=noprint_wrappers=1",
        url
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        if res.returncode == 0:
            print("[✓] Stream is active and broadcasting healthy video packets!")
            print(res.stdout.strip())
        else:
            print(f"[!] Stream probe returned error:\n{res.stderr.strip()}")
    except subprocess.TimeoutExpired:
        print("[!] Timeout probing stream. Is MediaMTX running and video accessible?")
    except Exception as e:
        print(f"[!] Error probing stream: {e}")

def stream_logs(lines: int = 50):
    """Watches live RTSP and WebRTC connection logs in real time."""
    if not os.path.exists(LOG_FILE):
        open(LOG_FILE, "a").close()

    lan_ip = get_lan_ip()
    print("=========================================================================================")
    print("               MEDIA MTX RTSP CAMERA SIMULATOR - LIVE CONNECTION LOGS")
    print(f"  Monitoring streams on LAN IP: {lan_ip} | RTSP: 8554 | WebRTC: 8889")
    print(f"  Log file: {LOG_FILE}")
    print("  Showing real-time events when clients open RTSP streams (VLC, OpenCV) or WebRTC...")
    print("  Press Ctrl+C to exit.")
    print("=========================================================================================\n")

    cmd = ["tail", f"-n{lines}", "-f", LOG_FILE]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for raw_line in proc.stdout:
            line = raw_line.strip()
            if not line:
                continue
            # Filter out noisy ffmpeg stats lines
            if "frame=" in line and "fps=" in line and "bitrate=" in line:
                continue
            # Colorize key events
            if any(k in line for k in ["opened", "is reading", "established", "created by"]):
                print(f"\033[92m● [STREAM ACTIVE] {line}\033[0m")
            elif any(k in line for k in ["closed", "disconnected", "terminated"]):
                print(f"\033[93m○ [STREAM CLOSED] {line}\033[0m")
            elif any(k in line for k in ["ERR", "error", "WAR", "warning", "failed"]):
                print(f"\033[91m! [ALERT] {line}\033[0m")
            elif "stream is available and online" in line:
                print(f"\033[96m★ [ONLINE] {line}\033[0m")
            else:
                print(f"  {line}")
    except KeyboardInterrupt:
        print("\n[+] Exited log monitor.")

def main():
    parser = argparse.ArgumentParser(description="MediaMTX RTSP Camera Simulator CLI Manager")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("start", help="Start the MediaMTX camera simulator in background")
    subparsers.add_parser("stop", help="Stop the MediaMTX camera simulator")
    subparsers.add_parser("restart", help="Restart the MediaMTX camera simulator")
    subparsers.add_parser("status", help="Check server status and active streams")
    subparsers.add_parser("list", help="List all available RTSP stream URLs")
    logs_parser = subparsers.add_parser("logs", help="View live stream access logs (when streams are opened/closed)")
    logs_parser.add_argument("-n", "--lines", type=int, default=50, help="Number of initial log lines (default: 50)")

    add_parser = subparsers.add_parser("add", help="Add a new video file to convert to RTSP")
    add_parser.add_argument("file", help="Path to downloaded video file (.mp4, .mkv, .avi, etc.)")
    add_parser.add_argument("--name", help="Custom RTSP stream path name (default: filename without extension)")

    test_parser = subparsers.add_parser("test", help="Test an RTSP stream locally")
    test_parser.add_argument("stream", nargs="?", default="ppe", help="Stream name to probe (default: ppe)")

    args = parser.parse_args()

    if args.command == "start":
        start_server()
    elif args.command == "stop":
        stop_server()
    elif args.command == "restart":
        stop_server()
        time.sleep(1)
        start_server()
    elif args.command in ("list", None):
        list_streams()
    elif args.command == "logs":
        stream_logs(args.lines)
    elif args.command == "status":
        pid = is_server_running()
        if pid:
            print(f"[✓] MediaMTX is ONLINE (PID: {pid})")
            list_streams()
        else:
            print("[x] MediaMTX is OFFLINE.")
    elif args.command == "add":
        add_video(args.file, args.name)
    elif args.command == "test":
        test_stream(args.stream)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
