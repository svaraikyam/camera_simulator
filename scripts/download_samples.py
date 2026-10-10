#!/usr/bin/env python3
"""
Sample Video Downloader for MediaMTX RTSP Camera Simulator.
Downloads sample videos for:
  1. PPE Detection (Personal Protective Equipment)
  2. Fire & Smoke Detection
  3. Industrial IoT / Surveillance
Also includes an offline synthetic video generator using ffmpeg as fallback.
"""

import os
import sys
import subprocess
import urllib.request
import time

VIDEOS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "videos"))

SAMPLE_URLS = [
    {
        "filename": "ppe_detection.mp4",
        "description": "PPE Detection (Construction/Industrial site with helmets & vests)",
        "url": "https://raw.githubusercontent.com/chanupadeshan/PPE-DETECTION/main/video/ppe-3-1.mp4",
    },
    {
        "filename": "fire_smoke_detection.mp4",
        "description": "Fire & Smoke Detection (Industrial/Outdoor fire scenario)",
        "url": "https://raw.githubusercontent.com/Prakhar-998/Fire_Detection/master/fire2.mp4",
    },
    {
        "filename": "industrial_iot.mp4",
        "description": "Industrial IoT & Area Monitoring",
        "url": "https://raw.githubusercontent.com/opencv/opencv/master/samples/data/vtest.avi",
        "transcode_needed": True,
    },
]

def download_file(url: str, dest_path: str, description: str) -> bool:
    print(f"\n[+] Downloading {description}...")
    print(f"    Source: {url}")
    print(f"    Target: {dest_path}")
    
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
    req = urllib.request.Request(url, headers=headers)
    
    tmp_path = dest_path + ".tmp"
    try:
        with urllib.request.urlopen(req, timeout=30) as resp, open(tmp_path, "wb") as f:
            total_size = int(resp.headers.get("content-length", 0))
            downloaded = 0
            start_time = time.time()
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    pct = (downloaded / total_size) * 100
                    elapsed = time.time() - start_time
                    speed = (downloaded / 1024) / max(elapsed, 0.001)
                    sys.stdout.write(f"\r    Progress: {downloaded/1024/1024:.2f} MB / {total_size/1024/1024:.2f} MB ({pct:.1f}%) @ {speed:.1f} KB/s")
                    sys.stdout.flush()
        print()
        os.replace(tmp_path, dest_path)
        print(f"    [OK] Saved successfully ({os.path.getsize(dest_path) / 1024 / 1024:.2f} MB)")
        return True
    except Exception as e:
        print(f"\n    [!] Download failed: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return False

def generate_synthetic_industrial_video(dest_path: str, title: str):
    """Fallback generator using ffmpeg test sources to produce realistic CCTV style video."""
    print(f"\n[+] Generating synthetic industrial CCTV video: {os.path.basename(dest_path)}...")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "testsrc=size=1280x720:rate=25",
        "-t", "15",
        "-vf", (
            f"drawbox=x=100:y=100:w=400:h=300:color=red@0.8:t=4,"
            f"drawtext=text='{title} [SIMULATED CAM]':fontcolor=white:fontsize=32:box=1:boxcolor=black@0.6:boxborderw=5:x=40:y=40,"
            f"drawtext=text='%{{localtime\\:%Y-%m-%d %H\\\\\\:%M\\\\\\:%S}}':fontcolor=yellow:fontsize=28:box=1:boxcolor=black@0.6:boxborderw=5:x=40:y=85,"
            f"drawtext=text='ZONE A: HAZARD MONITOR':fontcolor=green:fontsize=26:x=110:y=110"
        ),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        dest_path
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"    [OK] Generated {dest_path} ({os.path.getsize(dest_path) / 1024 / 1024:.2f} MB)")
        return True
    except Exception as err:
        print(f"    [!] ffmpeg generation failed: {err}")
        return False

def transcode_avi_to_mp4(src_path: str, dest_path: str):
    print(f"\n[+] Transcoding {os.path.basename(src_path)} to H.264 MP4...")
    cmd = [
        "ffmpeg", "-y", "-i", src_path,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast",
        "-an", dest_path
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"    [OK] Transcoded {dest_path} ({os.path.getsize(dest_path) / 1024 / 1024:.2f} MB)")
        if os.path.exists(src_path):
            os.remove(src_path)
        return True
    except Exception as err:
        print(f"    [!] Transcoding failed: {err}")
        return False

def main():
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    print("=========================================================")
    print("      MediaMTX Industrial AI Sample Video Downloader     ")
    print("=========================================================")

    for item in SAMPLE_URLS:
        filename = item["filename"]
        dest_path = os.path.join(VIDEOS_DIR, filename)

        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 100000:
            print(f"\n[~] File already exists: {filename} ({os.path.getsize(dest_path)/1024/1024:.2f} MB), skipping.")
            continue

        transcode_needed = item.get("transcode_needed", False)
        target_download_path = dest_path if not transcode_needed else os.path.join(VIDEOS_DIR, "temp_download.avi")

        success = download_file(item["url"], target_download_path, item["description"])
        if success and transcode_needed:
            transcode_avi_to_mp4(target_download_path, dest_path)
        elif not success:
            print("    [!] Attempting synthetic generator fallback...")
            generate_synthetic_industrial_video(dest_path, item["description"])

    print("\n[+] Video downloads complete. Current videos in videos/ folder:")
    for f in sorted(os.listdir(VIDEOS_DIR)):
        fp = os.path.join(VIDEOS_DIR, f)
        if os.path.isfile(fp):
            print(f"    - {f} ({os.path.getsize(fp)/1024/1024:.2f} MB)")

if __name__ == "__main__":
    main()
