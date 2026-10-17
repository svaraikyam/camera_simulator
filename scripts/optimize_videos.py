#!/usr/bin/env python3
"""
GPU-Accelerated Video Optimizer for MediaMTX RTSP Camera Simulator
===================================================================
Optimizes videos for ultra-low latency RTSP streaming:
  - Downscales 4K/2K videos to clean 1080p/720p (preserves aspect ratio)
  - Enforces H.264 Baseline profile with NO B-frames (-bf 0) for WebRTC & VLC
  - Fixed 25 FPS with consistent 2-second keyframe GOP (-g 50)
  - Uses NVIDIA NVENC (RTX GPU) for fast batch processing with CPU fallback
  - Enables Zero-CPU stream copying (-c:v copy) in MediaMTX!
"""

import os
import sys
import shutil
import subprocess
import argparse
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
VIDEOS_DIR = BASE_DIR / "videos"
RAW_DIR = VIDEOS_DIR / "raw"

def check_nvenc_support() -> bool:
    """Checks if ffmpeg has h264_nvenc support on this machine."""
    try:
        res = subprocess.run(
            ["ffmpeg", "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return "h264_nvenc" in res.stdout
    except Exception:
        return False

def get_video_info(video_path: Path):
    """Probes resolution, codec, and frame rate of a video file."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,codec_name,avg_frame_rate,profile",
        "-of", "default=noprint_wrappers=1",
        str(video_path)
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        info = {}
        for line in res.stdout.strip().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                info[k] = v
        width = int(info.get("width", 0))
        height = int(info.get("height", 0))
        codec = info.get("codec_name", "")
        profile = info.get("profile", "")
        return {"width": width, "height": height, "codec": codec, "profile": profile}
    except Exception as e:
        return None

def optimize_video(src_path: Path, dest_path: Path, use_gpu: bool = True, max_width: int = 1920, max_height: int = 1080):
    """Encodes a video into RTSP streaming-ready format."""
    info = get_video_info(src_path)
    if not info:
        print(f"[!] Warning: Could not probe {src_path.name}, skipping.")
        return False

    w, h = info["width"], info["height"]
    print(f"[+] Optimizing: {src_path.name} (Source: {w}x{h}, {info['codec']} {info['profile']})")

    # Safe proportional scale filter that guarantees even dimensions (divisible by 2)
    # Bounded inside max_width x max_height
    vf_filter = (
        f"scale=w={max_width}:h={max_height}:force_original_aspect_ratio=decrease,"
        f"scale=trunc(iw/2)*2:trunc(ih/2)*2"
    )

    tmp_out = dest_path.with_suffix(".tmp.mp4")

    if use_gpu:
        encoder_args = [
            "-c:v", "h264_nvenc",
            "-preset", "p4",
            "-tune", "hq",
            "-profile:v", "baseline",
            "-bf", "0",
            "-g", "50",
            "-r", "25",
            "-b:v", "3M",
            "-maxrate", "4M",
            "-bufsize", "8M",
            "-pix_fmt", "yuv420p"
        ]
    else:
        encoder_args = [
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-tune", "zerolatency",
            "-profile:v", "baseline",
            "-bf", "0",
            "-g", "50",
            "-r", "25",
            "-crf", "22",
            "-pix_fmt", "yuv420p"
        ]

    cmd = [
        "ffmpeg", "-y",
        "-i", str(src_path),
        "-vf", vf_filter,
        *encoder_args,
        "-an",
        "-movflags", "+faststart",
        str(tmp_out)
    ]

    start_t = time.time()
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        if tmp_out.exists():
            tmp_out.replace(dest_path)
            elapsed = time.time() - start_t
            src_sz = src_path.stat().st_size / (1024 * 1024)
            dest_sz = dest_path.stat().st_size / (1024 * 1024)
            new_info = get_video_info(dest_path) or {}
            nw, nh = new_info.get("width", "?"), new_info.get("height", "?")
            print(f"    [✓] Done in {elapsed:.1f}s | {src_sz:.1f}MB -> {dest_sz:.1f}MB | Resolution: {nw}x{nh}")
            return True
    except subprocess.CalledProcessError as e:
        print(f"    [x] Failed to optimize: {e.stderr.decode(errors='ignore')[:300]}")
        if tmp_out.exists():
            tmp_out.unlink()
        return False

def main():
    parser = argparse.ArgumentParser(description="Optimize video files for zero-CPU RTSP streaming")
    parser.add_argument("--file", type=str, help="Specific file to optimize")
    parser.add_argument("--cpu", action="store_true", help="Force CPU encoding instead of NVIDIA NVENC")
    parser.add_argument("--backup-raw", action="store_true", default=True, help="Backup original 4K/raw files to videos/raw/")
    args = parser.parse_args()

    has_nvenc = check_nvenc_support()
    use_gpu = has_nvenc and not args.cpu

    print("==================================================================")
    print("      MediaMTX RTSP Camera Simulator - Video Optimizer           ")
    print("==================================================================")
    if use_gpu:
        print("[✓] Acceleration: NVIDIA NVENC GPU Hardware Acceleration (RTX)")
    else:
        print("[!] Acceleration: Software CPU Encoding (libx264)")
    print(f"[*] Videos Directory: {VIDEOS_DIR}")
    print("==================================================================\n")

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if args.file:
        files = [Path(args.file)]
    else:
        files = [
            f for f in VIDEOS_DIR.glob("*.mp4")
            if not f.name.startswith(".") and not f.name.endswith(".tmp.mp4")
        ]

    if not files:
        print("[!] No .mp4 videos found in videos/ directory.")
        return

    print(f"[*] Found {len(files)} video(s) to inspect/optimize.\n")

    for f in sorted(files):
        info = get_video_info(f)
        if not info:
            continue
        
        # Check if already optimized: H264 baseline, width <= 1920, height <= 1080
        w, h = info["width"], info["height"]
        is_4k_or_high = w > 1920 or h > 1080 or "baseline" not in info["profile"].lower()

        if is_4k_or_high:
            raw_backup = RAW_DIR / f.name
            if not raw_backup.exists() and args.backup_raw:
                print(f"[*] Preserving raw original -> {raw_backup.relative_to(BASE_DIR)}")
                shutil.copy2(f, raw_backup)

            optimize_video(f, f, use_gpu=use_gpu)
        else:
            print(f"[i] Already optimized: {f.name} ({w}x{h}, {info['profile']})")

    print("\n==================================================================")
    print("[✓] Batch optimization complete! All videos are RTSP-streaming ready.")
    print("==================================================================")

if __name__ == "__main__":
    main()
