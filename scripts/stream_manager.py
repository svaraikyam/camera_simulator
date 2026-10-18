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
            pass
    
    # Secondary check using pgrep
    try:
        res = subprocess.run(["pgrep", "-f", "mediamtx.*mediamtx.yml"], stdout=subprocess.PIPE, text=True)
        if res.stdout.strip():
            pids = res.stdout.strip().split()
            found_pid = int(pids[0])
            with open(PID_FILE, "w") as f:
                f.write(str(found_pid))
            return found_pid
    except Exception:
        pass

    # Tertiary check: probe REST API port 9997
    try:
        req = urllib.request.Request("http://127.0.0.1:9997/v3/paths/list")
        with urllib.request.urlopen(req, timeout=0.5) as resp:
            if resp.status == 200:
                return -1 # Running (PID unknown)
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
        # Standard Primary Streams
        ("ppe", "videos/ppe_detection.mp4", "PPE Detection (Helmets, Safety Vests, PPE AI)"),
        ("ppe-detection", "videos/ppe-detection.mp4", "PPE Detection Camera 2"),
        ("fire-smoke", "videos/fire_smoke_detection.mp4", "Fire & Smoke Detection (Hazard/Flame AI)"),
        ("house-fire", "videos/house-fire.mp4", "House Fire Incident Camera"),
        ("house-fire-worker", "videos/house-fire-worker.mp4", "House Fire & Worker Hazard Camera"),
        ("industrial-iot", "videos/industrial_iot.mp4", "Industrial IoT / Facility Surveillance"),
        ("transformer-monitoring", "videos/transofmer-monitoring.mp4", "Transformer & Substation Surveillance"),
        
        # PPE Detection Multi-Camera (ppe-detect-1 to 4)
        ("ppe-detect-1", "videos/ppe-video-4.mp4", "PPE Detection Cam 1 (Video 4)"),
        ("ppe-detect-2", "videos/ppe-video-6.mp4", "PPE Detection Cam 2 (Video 6)"),
        ("ppe-detect-3", "videos/ppe-video-7.mp4", "PPE Detection Cam 3 (Video 7)"),
        ("ppe-detect-4", "videos/ppe-video-9.mp4", "PPE Detection Cam 4 (Video 9)"),

        # PPE Violations Multi-Camera (ppe-violate-1 to 3)
        ("ppe-violate-1", "videos/ppe-video-8.mp4", "PPE Violation Cam 1 (Video 8)"),
        ("ppe-violate-2", "videos/ppe-violation-2.mp4", "PPE Violation Cam 2 (Violation 2)"),
        ("ppe-violate-3", "videos/ppe-video-5.mp4", "PPE Violation Cam 3 (Video 5)"),

        # Direct Video Filename Feeds (Direct Edge Gateway Ingest)
        ("ppe-video-4", "videos/ppe-video-4.mp4", "PPE Video 4 Direct Feed"),
        ("ppe-video-5", "videos/ppe-video-5.mp4", "PPE Video 5 Direct Feed"),
        ("ppe-video-6", "videos/ppe-video-6.mp4", "PPE Video 6 Direct Feed"),
        ("ppe-video-7", "videos/ppe-video-7.mp4", "PPE Video 7 Direct Feed"),
        ("ppe-video-8", "videos/ppe-video-8.mp4", "PPE Video 8 Direct Feed"),
        ("ppe-video-9", "videos/ppe-video-9.mp4", "PPE Video 9 Direct Feed"),
        ("ppe-violation-1", "videos/ppe-violation-1.mp4", "PPE Violation 1 Direct Feed"),
        ("ppe-violation-2", "videos/ppe-violation-2.mp4", "PPE Violation 2 Direct Feed"),
        ("ppe-violation-3", "videos/ppe-violation-3.mp4", "PPE Violation 3 Direct Feed"),
        ("ppe-no-helmet-1", "videos/ppe-no-helmet-1.mp4", "PPE No-Helmet Detection Feed 1"),
        ("ppe-video-10", "videos/ppe-video-10.mp4", "PPE Video 10 Direct Feed"),
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
    """Adds a new downloaded video file and converts it to RTSP streaming-ready format."""
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

    # Optimize using scripts/optimize_videos.py
    optimize_script = os.path.join(BASE_DIR, "scripts", "optimize_videos.py")
    if os.path.exists(optimize_script):
        # First copy to temp or target if different
        if os.path.abspath(src_path) != os.path.abspath(dest_path):
            shutil.copy2(src_path, dest_path)
        cmd = [sys.executable, optimize_script, "--file", dest_path]
        subprocess.run(cmd, check=True)
    else:
        # Fallback transcoding to RTSP-optimized H.264 MP4 using ffmpeg
        print("    Transcoding to RTSP-optimized H.264 MP4 using ffmpeg...")
        cmd = [
            "ffmpeg", "-y", "-i", src_path,
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-profile:v", "baseline", "-bf", "0", "-g", "50", "-r", "25",
            "-an", dest_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Automatically add to config/mediamtx.yml as permanent publisher if not present
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            content = f.read()
        
        path_key = f"\n  {safe_name}:"
        if path_key not in content:
            print(f"    Registering '{safe_name}' as a permanent looping publisher in config/mediamtx.yml...")
            entry = (
                f"\n  {safe_name}:\n"
                f"    runOnInit: >-\n"
                f"      ffmpeg -nostats -loglevel warning\n"
                f"      -re -stream_loop -1\n"
                f"      -i ./videos/{target_mp4}\n"
                f"      -c:v copy\n"
                f"      -an -rtsp_transport tcp\n"
                f"      -f rtsp rtsp://127.0.0.1:8554/{safe_name}\n"
                f"    runOnInitRestart: yes\n"
            )
            insert_marker = "  '~^[a-f0-9]{32}/[a-f0-9]{32}$':"
            if insert_marker in content:
                idx = content.find(insert_marker)
                new_content = content[:idx] + entry + "\n" + content[idx:]
            elif "  all_others:" in content:
                idx = content.find("  all_others:")
                new_content = content[:idx] + entry + "\n" + content[idx:]
            else:
                new_content = content + entry
            with open(CONFIG_PATH, "w") as f:
                f.write(new_content)
            
            # Restart server if currently running so new stream is immediately active
            pid = is_server_running()
            if pid:
                print("    Restarting MediaMTX to activate permanent stream...")
                stop_server()
                time.sleep(1)
                start_server()

    lan_ip = get_lan_ip()
    print(f"\n[✓] Video successfully added & running as permanent looping RTSP stream!")
    print(f"    Stream is immediately live at:")
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

    opt_parser = subparsers.add_parser("optimize", help="Optimize videos using RTX GPU (NVENC downscale & Baseline H.264 for zero-CPU streaming)")
    opt_parser.add_argument("--file", help="Specific video file to optimize")
    opt_parser.add_argument("--cpu", action="store_true", help="Force software CPU encoding instead of NVIDIA NVENC")

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
    elif args.command == "optimize":
        optimize_script = os.path.join(BASE_DIR, "scripts", "optimize_videos.py")
        cmd = [sys.executable, optimize_script]
        if args.file:
            cmd.extend(["--file", args.file])
        if args.cpu:
            cmd.append("--cpu")
        subprocess.run(cmd)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
