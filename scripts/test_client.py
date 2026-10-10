#!/usr/bin/env python3
"""
RTSP Stream Verification Client
Tests connection to the RTSP camera simulator and verifies video frames.
Can be executed on this machine or copied to another PC to test remote access.
"""

import sys
import time
import argparse
import subprocess

def test_with_ffprobe(rtsp_url: str):
    print(f"\n[+] Testing with ffprobe: {rtsp_url}")
    cmd = [
        "ffprobe", "-v", "warning",
        "-rtsp_transport", "tcp",
        "-show_streams",
        "-show_entries", "stream=index,codec_name,codec_type,width,height,avg_frame_rate",
        "-of", "json",
        rtsp_url
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=12)
        if res.returncode == 0:
            print("[✓] Successfully connected to RTSP stream! Stream details:")
            print(res.stdout)
            return True
        else:
            print("[!] ffprobe returned non-zero exit code:")
            print(res.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("[!] Connection timed out. Make sure MediaMTX is running and firewall allows port 8554.")
        return False
    except FileNotFoundError:
        print("[!] ffprobe not found on this system.")
        return False

def test_with_opencv(rtsp_url: str, num_frames: int = 30):
    print(f"\n[+] Testing with OpenCV VideoCapture: {rtsp_url}")
    try:
        import cv2
        if not hasattr(cv2, "VideoCapture"):
            try:
                from cv2 import cv2 as cv2
            except ImportError:
                pass
        if not hasattr(cv2, "VideoCapture"):
            print("[!] OpenCV is installed but does not have VideoCapture. Using ffprobe.")
            return False
    except ImportError:
        print("[!] opencv-python is not installed. You can install it with: pip install opencv-python")
        return False

    print("    Opening VideoCapture stream (RTSP TCP)...")
    # Setting RTSP transport to TCP for maximum stability
    import os
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print(f"[!] Failed to open stream at {rtsp_url}")
        return False

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"    Stream opened: {width}x{height} @ {fps:.1f} FPS")

    frame_count = 0
    start_time = time.time()
    while frame_count < num_frames:
        ret, frame = cap.read()
        if not ret:
            print("[!] Frame read failed or stream ended.")
            break
        frame_count += 1
        if frame_count % 10 == 0:
            elapsed = time.time() - start_time
            print(f"    Read {frame_count}/{num_frames} frames ({frame_count/max(elapsed, 0.001):.1f} FPS)...")

    cap.release()
    total_time = time.time() - start_time
    avg_fps = frame_count / max(total_time, 0.001)
    print(f"[✓] Successfully received and decoded {frame_count} frames! Average decode rate: {avg_fps:.1f} FPS")
    return frame_count > 0

def main():
    parser = argparse.ArgumentParser(description="Test and verify RTSP camera stream playback")
    parser.add_argument("url", nargs="?", default="rtsp://127.0.0.1:8554/ppe",
                        help="RTSP URL to test (default: rtsp://127.0.0.1:8554/ppe)")
    parser.add_argument("--frames", type=int, default=30, help="Number of frames to test with OpenCV (default: 30)")
    args = parser.parse_args()

    print("=========================================================")
    print("           RTSP Stream Verification Client               ")
    print("=========================================================")
    print(f"Target RTSP URL: {args.url}")

    # Test with ffprobe first
    ffprobe_ok = test_with_ffprobe(args.url)

    # Test with OpenCV if installed
    cv_ok = test_with_opencv(args.url, args.frames)

    if ffprobe_ok or cv_ok:
        print("\n[✓] VERIFICATION SUCCESSFUL: Stream is live and readable!")
    else:
        print("\n[x] VERIFICATION FAILED. Please verify that the server is running.")

if __name__ == "__main__":
    main()
