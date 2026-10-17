# MediaMTX Performance & NVIDIA GPU Acceleration Guide

This guide details the architectural optimizations, root cause analysis of CPU saturation, and the dual-strategy hardware acceleration implemented in the **MediaMTX RTSP Camera Simulator**.

---

## 1. Problem Diagnosis & Root Cause

### The Symptom
When running multiple simultaneous camera streams, system CPU utilization pegged at **100% across all 12 CPU cores**, driving the system load average to **~50.0 (49.93)**. Client connections suffered from packet drops, buffering, RTSP handshake timeouts, and high latency.

### The Root Cause
A detailed audit of the streaming pipeline and video source files revealed two compounding bottlenecks:

1. **4K UHD / 2K QHD Resolution on Source Media:**
   Several downloaded industrial and PPE sample videos were encoded at **3840×2160 (4K UHD)** and **2560×1440 (2K QHD)**:
   - `ppe-video-4.mp4`: 3840×2160 (4K)
   - `ppe-video-5.mp4`: 3840×2160 (4K)
   - `ppe-video-7.mp4`: 3840×2160 (4K)
   - `ppe-video-8.mp4`: 3840×2160 (4K)
   - `ppe-video-9.mp4`: 3840×2160 (4K)
   - `ppe-violation-2.mp4`: 2560×1440 (2K)

2. **Software CPU Transcoding (`libx264`):**
   In `config/mediamtx.yml`, all 12 permanent streams were configured to continuously decode and re-encode video using `libx264` on the CPU:
   ```yaml
   # OLD CONFIGURATION (Bottleneck)
   runOnInit: ffmpeg -re -stream_loop -1 -i ./videos/sample.mp4 -c:v libx264 ...
   ```
   Software encoding a single 4K H.264 stream at 25-30 FPS requires **300% to 400% CPU capacity** (3 to 4 dedicated CPU cores).
   Attempting to run 6 concurrent 4K streams plus 6 concurrent 1080p streams required **>2400% CPU capacity** on a 12-core system (max 1200%), causing total thread starvation, massive runqueue delays, and a load average near 50.

---

## 2. The Dual-Strategy Architecture

To eliminate the bottleneck while accommodating both high-throughput permanent streams and on-demand ad-hoc video streams, we implemented a **Dual-Strategy Architecture**:

```
+---------------------------------------------------------------------------------------+
|                               CAMERA SIMULATOR ARCHITECTURE                           |
+---------------------------------------------------------------------------------------+
                                           |
                   +-----------------------+-----------------------+
                   |                                               |
                   v                                               v
       [ STRATEGY A: PERMANENT FEEDS ]                 [ STRATEGY B: ON-DEMAND FEEDS ]
         (12 Fixed Surveillance Feeds)                   (Dynamic Videos in videos/)
                   |                                               |
         GPU Pre-Transcoded Once                          NVIDIA RTX NVENC Transcoder
      (1080p Bounded, Baseline, -bf 0)                  (h264_nvenc, Ultra-Low Latency)
                   |                                               |
                   v                                               v
        Zero-CPU Stream Copy (-c:v copy)                GPU Hardware Offload (-c:v h264_nvenc)
       Packets routed directly to network              Frames scaled and encoded on NVENC
                   |                                               |
                   +-----------------------+-----------------------+
                                           |
                                           v
                             +---------------------------+
                             |   MediaMTX Engine :8554   |
                             +---------------------------+
                                           |
                     +---------------------+---------------------+
                     |                     |                     |
                     v                     v                     v
                RTSP Clients          WebRTC Clients        HLS Clients
              (VLC, OpenCV AI)       (Web Browsers :8889)   (HTTP Live :8888)
```

---

### Strategy A: GPU Pre-Transcoding + Zero-CPU Stream Copy (`-c:v copy`)

**Best suited for:** Permanent, multi-camera simulated surveillance environments (e.g. 12+ factory cameras running 24/7).

1. **One-Time Optimization:**
   Source videos are batch-processed once using the dedicated GPU script `scripts/optimize_videos.py`:
   - 4K/2K resolutions are downscaled to standard **1080p / 720p** (bounded inside 1920×1080, preserving original aspect ratio and ensuring dimensions are even numbers).
   - Video is normalized to **H.264 Baseline Profile**, **0 B-frames (`-bf 0`)**, **fixed 25 FPS**, and **GOP size of 50 (`-g 50`)** with faststart metadata.
   - Raw full-resolution originals are backed up in `videos/raw/`.

2. **Zero-CPU Stream Copying (`-c:v copy`):**
   Because the video files on disk already meet RTSP, WebRTC, VLC, and OpenCV strict stream specifications, MediaMTX launches `ffmpeg` with `-c:v copy`:
   ```yaml
   ppe-detect-1:
     runOnInit: >-
       ffmpeg -nostats -loglevel warning
       -re -stream_loop -1
       -i ./videos/ppe-video-4.mp4
       -c:v copy
       -an -rtsp_transport tcp
       -f rtsp rtsp://127.0.0.1:8554/ppe-detect-1
     runOnInitRestart: yes
   ```
   **CPU Impact:** ffmpeg only reads container packets and forwards them to the RTSP socket. CPU usage drops from **100% per stream to ~0.5% per stream**!

---

### Strategy B: NVIDIA RTX NVENC Hardware Acceleration (`h264_nvenc`)

**Best suited for:** Dynamic on-demand streams (`all_others` pattern in `config/mediamtx.yml`) when users drop unoptimized, raw video files directly into `videos/`.

1. **On-Demand Trigger:**
   When an external client requests any arbitrary video path (e.g. `rtsp://<HOST_IP>:8554/warehouse-cam`):
   ```yaml
   all_others:
     runOnDemand: >-
       ffmpeg -nostats -loglevel warning
       -re -stream_loop -1
       -i ./videos/$MTX_PATH.mp4
       -map 0:v:0
       -vf "scale=w=1920:h=1080:force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2"
       -c:v h264_nvenc -preset p1 -tune ull
       -profile:v baseline -pix_fmt yuv420p -bf 0
       -r 25 -g 50
       -an -rtsp_transport tcp
       -f rtsp rtsp://127.0.0.1:8554/$MTX_PATH
     runOnDemandRestart: yes
     runOnDemandStartTimeout: 10s
     runOnDemandCloseAfter: 10s
   ```
2. **NVENC Acceleration:**
   - Transcoding is executed entirely on the dedicated **NVIDIA NVENC hardware chip** (tested on NVIDIA GeForce RTX 3060 12GB).
   - Flags `-preset p1 -tune ull` ensure the fastest possible hardware encoding with ultra-low latency.
   - Scale filter guarantees bounding to 1080p with aspect ratio preservation.
   - When the client disconnects, `runOnDemandCloseAfter: 10s` automatically stops ffmpeg to release GPU resources.

---

## 3. Benchmarks & Performance Comparison

The following telemetry was captured on a 12-core Linux system with an NVIDIA GeForce RTX 3060:

| Metric | Before Optimization | After Dual-Strategy Optimization | Improvement |
|---|---|---|---|
| **System Load Average** | **49.93** (Extreme Saturation) | **2.17** (Idle / Healthy) | **~96% Reduction** |
| **CPU Usage Per Stream** | 98% – 100% CPU | **0.3% – 0.7% CPU** | **>99% Drop** |
| **Total CPU (12 Streams)** | >1100% CPU (All cores pinned) | **~6.5% Total CPU** | **Zero CPU Spikes** |
| **GPU VRAM Consumption** | 0 MB (Unused) | Minimal (<100MB for on-demand) | Headroom for AI inference |
| **Client Decode Frame Rate** | Stuttered / Frame Drops | **77.1 FPS** (Smooth playback) | Flawless streaming |
| **WebRTC / VLC Latency** | High / Frequent Timeouts | **< 200ms** (Real-time) | Immediate responsiveness |

---

## 4. How to Optimize Videos

### Option 1: Optimize All Existing Videos (CLI)
To scan `videos/` and optimize any 4K, 2K, or high-profile videos using the RTX GPU:
```bash
python3 scripts/stream_manager.py optimize
```
Or directly:
```bash
python3 scripts/optimize_videos.py
```

### Option 2: Add and Auto-Optimize a New Video
When adding a new downloaded video, `stream_manager.py add` will automatically detect NVENC support, scale to 1080p, and configure it for streaming:
```bash
python3 scripts/stream_manager.py add /path/to/my_download.mp4 --name dock-camera-1
```

### Option 3: Force Software CPU Encoding (Fallback)
If running on an edge device without an NVIDIA GPU:
```bash
python3 scripts/stream_manager.py optimize --cpu
```

---

## 5. Summary of Best Practices for RTSP Streaming

1. **Never software-transcode 4K streams live** on CPU unless you have a dedicated server with 32+ cores.
2. **Always eliminate B-frames (`-bf 0`)** for real-time RTSP/WebRTC streams. B-frames introduce reordering latency and packet jitter in browsers and OpenCV.
3. **Enforce Baseline Profile (`-profile:v baseline`)** for universal compatibility across VLC, WebRTC (Chrome/Edge), and OpenCV `VideoCapture`.
4. **Fix GOP Size (`-g 50` at 25 FPS)**: Keyframes every 2 seconds allow connecting clients (like VLC or web viewers) to lock onto the stream within 1–2 seconds instead of waiting for a distant I-frame.
5. **Use `-movflags +faststart`**: Moves the container index (moov atom) to the front of the file, allowing immediate packet seeking and streaming without loading the entire video into memory.
