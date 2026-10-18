# MediaMTX RTSP Camera Simulator

A lightweight, zero-dependency **MediaMTX** RTSP streaming server that converts downloaded industrial AI & IoT video files into continuous, live RTSP camera streams.

Designed specifically for testing Computer Vision and Industrial IoT models (PPE detection, Fire & Smoke detection, worker safety, warehouse monitoring) from any remote PC, NVR, or edge device across your local network.

---

## Features

- **Industrial AI Demo Cameras**: Pre-loaded with high-quality sample videos for:
  - **PPE Detection**: `rtsp://<HOST_IP>:8554/ppe`
  - **Fire & Smoke Detection**: `rtsp://<HOST_IP>:8554/fire-smoke`
  - **Industrial IoT / Facility Monitoring**: `rtsp://<HOST_IP>:8554/industrial-iot`
- **Convert ANY Downloaded Video**: Add any video file (`.mp4`, `.mkv`, `.avi`, `.mov`) with a single command or by dropping it into `videos/`.
- **Remote PC Access**: Streams over `0.0.0.0:8554` (RTSP TCP/UDP) so any device on your Wi-Fi/LAN can view or process the stream.
- **NVIDIA RTX GPU Hardware Acceleration**: Hardware-accelerated batch optimization and on-demand live transcoding using `h264_nvenc` (tested on RTX 3060).
- **Zero-CPU Stream Pass-through**: Uses `-stream_loop -1 -c:v copy` for permanent multi-camera feeds, allowing 12+ concurrent streams with less than 7% total CPU load.
- **Instant Web Browser Viewing**: Includes built-in WebRTC (`http://<HOST_IP>:8889/<stream>`) to watch streams in Google Chrome, Edge, or Firefox without installing VLC or any media player.
- **Interactive CLI Manager**: `python3 scripts/stream_manager.py` automatically detects host LAN IP, lists all stream URLs, optimizes videos, and manages server lifecycle.

---

## Directory Structure

```
camera-simulator/
├── bin/
│   └── mediamtx                  # MediaMTX standalone binary (v1.21.2)
├── config/
│   └── mediamtx.yml              # Server & stream paths configuration
├── videos/                       # Place downloaded video files here
│   ├── raw/                      # Automatically preserved raw 4K originals
│   ├── ppe_detection.mp4         # Sample PPE detection video
│   ├── fire_smoke_detection.mp4  # Sample Fire & Smoke detection video
│   └── industrial_iot.mp4        # Sample Industrial IoT video
├── scripts/
│   ├── setup.sh                  # Checks dependencies & downloads assets
│   ├── download_samples.py       # Downloads industrial sample videos
│   ├── optimize_videos.py        # GPU-accelerated video batch optimizer
│   ├── stream_manager.py         # CLI manager (start, stop, list, add, optimize, test)
│   └── test_client.py            # Local/remote RTSP stream test utility
├── run.sh                        # One-click start script
├── stop.sh                       # One-click stop script
├── docker-compose.yml            # Docker deployment option
├── requirements.txt              # Optional Python test dependencies
├── PERFORMANCE_AND_GPU_GUIDE.md  # Detailed performance root cause & GPU guide
└── README.md                     # Documentation
```

---

## Quick Start

### 1. Start the Camera Simulator
Run the startup script:
```bash
./run.sh
```
This automatically verifies the environment, starts MediaMTX in the background, and displays your active RTSP links with your host's LAN IP address.

### 2. View Active Streams
To display the list of all active RTSP streams and their network URLs:
```bash
python3 scripts/stream_manager.py list
```

### 3. Stop the Simulator
```bash
./stop.sh
```

### Python Virtual Environment
A Python virtual environment is configured at `.venv` with all necessary packages (`opencv-python-headless`, `requests`, `numpy`).
To activate it manually:
```bash
source .venv/bin/activate
```
*(All scripts and `./run.sh` will also automatically detect and use `.venv` if available).*

---

## Pre-configured Industrial RTSP Streams

Every stream is a **permanent, continuously looping publisher** running with `-re -stream_loop -1` and `runOnInitRestart: yes`. This ensures edge gateways (such as VisionSphere Edge Orchestrator or NVRs) can disconnect and reconnect at any time without terminating the stream.

### Primary Surveillance Feeds
| Stream Name | Description | Local RTSP URL | Remote PC (LAN) URL | Web Browser (WebRTC) |
|---|---|---|---|---|
| **ppe** | PPE Detection (Hard Hats, Safety Vests) | `rtsp://127.0.0.1:8554/ppe` | `rtsp://<HOST_IP>:8554/ppe` | `http://<HOST_IP>:8889/ppe` |
| **fire-smoke** | Fire & Smoke Hazard Detection | `rtsp://127.0.0.1:8554/fire-smoke` | `rtsp://<HOST_IP>:8554/fire-smoke` | `http://<HOST_IP>:8889/fire-smoke` |
| **industrial-iot** | Facility / Industrial Surveillance | `rtsp://127.0.0.1:8554/industrial-iot` | `rtsp://<HOST_IP>:8554/industrial-iot` | `http://<HOST_IP>:8889/industrial-iot` |
| **transformer-monitoring** | Transformer & Substation Monitoring | `rtsp://127.0.0.1:8554/transformer-monitoring` | `rtsp://<HOST_IP>:8554/transformer-monitoring` | `http://<HOST_IP>:8889/transformer-monitoring` |
| **house-fire** | House Fire Incident Camera | `rtsp://127.0.0.1:8554/house-fire` | `rtsp://<HOST_IP>:8554/house-fire` | `http://<HOST_IP>:8889/house-fire` |
| **house-fire-worker** | House Fire & Worker Hazard Camera | `rtsp://127.0.0.1:8554/house-fire-worker` | `rtsp://<HOST_IP>:8554/house-fire-worker` | `http://<HOST_IP>:8889/house-fire-worker` |

### Multi-Camera PPE Feeds (Detection & Violations)
| Stream Name | Video Source | RTSP URL |
|---|---|---|
| `ppe-detect-1` / `ppe-video-4` | `videos/ppe-video-4.mp4` | `rtsp://<HOST_IP>:8554/ppe-detect-1` |
| `ppe-detect-2` / `ppe-video-6` | `videos/ppe-video-6.mp4` | `rtsp://<HOST_IP>:8554/ppe-detect-2` |
| `ppe-detect-3` / `ppe-video-7` | `videos/ppe-video-7.mp4` | `rtsp://<HOST_IP>:8554/ppe-detect-3` |
| `ppe-detect-4` / `ppe-video-9` | `videos/ppe-video-9.mp4` | `rtsp://<HOST_IP>:8554/ppe-detect-4` |
| `ppe-violate-1` / `ppe-video-8` | `videos/ppe-video-8.mp4` | `rtsp://<HOST_IP>:8554/ppe-violate-1` |
| `ppe-violate-2` / `ppe-violation-2` | `videos/ppe-violation-2.mp4` | `rtsp://<HOST_IP>:8554/ppe-violate-2` |
| `ppe-violate-3` / `ppe-video-5` | `videos/ppe-video-5.mp4` | `rtsp://<HOST_IP>:8554/ppe-violate-3` |
| `ppe-violation-1` | `videos/ppe-violation-1.mp4` | `rtsp://<HOST_IP>:8554/ppe-violation-1` |
| `ppe-violation-3` | `videos/ppe-violation-3.mp4` | `rtsp://<HOST_IP>:8554/ppe-violation-3` |

*(Replace `<HOST_IP>` with the LAN IP printed by `python3 scripts/stream_manager.py list`, e.g. `192.168.1.26`)*


---

## How to Convert Any Downloaded Video to an RTSP Stream

### Method A: Stream Manager CLI (Recommended)
You can convert any video file using `stream_manager.py add`:
```bash
python3 scripts/stream_manager.py add /path/to/my_downloaded_video.mp4 --name warehouse-forklift
```
- It automatically verifies the video encoding, converts to H.264 if needed, and saves it in `videos/`.
- It will print your new RTSP link immediately:
  - `rtsp://<HOST_IP>:8554/warehouse-forklift`

### Method B: Drop Video Into `videos/` (Dynamic On-Demand)
Simply drop any `.mp4` file into the `videos/` folder:
```bash
cp /downloads/conveyor_belt.mp4 videos/conveyor_belt.mp4
```
MediaMTX is configured with **dynamic on-demand streaming**. As soon as any client connects to:
```
rtsp://<HOST_IP>:8554/conveyor_belt
```
ffmpeg automatically starts streaming that file in an infinite loop!

---

## Accessing the RTSP Stream from Another PC

Ensure the client PC is connected to the same local network (Wi-Fi, Ethernet, or VPN).

### 1. In VLC Media Player
1. Open VLC on the remote PC.
2. Go to **Media** (or **File**) -> **Open Network Stream...** (Ctrl+N / Cmd+N).
3. Enter the network RTSP URL:
   ```
   rtsp://<HOST_IP>:8554/ppe
   ```
4. Click **Play**.
*(Tip: In VLC Edit Options, you can add `:rtsp-tcp` for low-latency TCP streaming).*

### 2. In Python / OpenCV (AI Inference & YOLO)
Run this snippet on the other PC to process the RTSP camera stream directly with OpenCV:
```python
import cv2
import os

# Use TCP transport for reliable RTSP streaming over LAN/Wi-Fi
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

RTSP_URL = "rtsp://<HOST_IP>:8554/ppe"  # or /fire-smoke or /industrial-iot

cap = cv2.VideoCapture(RTSP_URL)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("Failed to receive frame from RTSP stream")
        break

    # --> Run your PPE / Fire detection model here (e.g. YOLOv8 / YOLOv11) <--
    # results = model(frame)

    cv2.imshow("Industrial AI RTSP Stream", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
```

### 3. In Web Browser (Zero-Install WebRTC)
Open Google Chrome, Mozilla Firefox, or Microsoft Edge on any phone, tablet, or PC and navigate to:
```
http://<HOST_IP>:8889/ppe
```
or
```
http://<HOST_IP>:8889/fire-smoke
```
MediaMTX includes a built-in WebRTC WHEP viewer that streams ultra-low latency video directly in the browser!

### 4. Using FFplay
On any machine with FFmpeg installed:
```bash
ffplay -rtsp_transport tcp rtsp://<HOST_IP>:8554/ppe
```

---

## Network & Firewall Configuration

If another PC cannot connect to the stream:
1. Ensure both devices can ping each other:
   ```bash
   ping <HOST_IP>
   ```
2. If `ufw` firewall is active on the server machine, open the streaming ports:
   ```bash
   sudo ufw allow 8554/tcp
   sudo ufw allow 8554/udp
   sudo ufw allow 8889/tcp
   ```

---

## Running with Docker (Alternative)

If you prefer to run the simulator inside Docker:
```bash
docker compose up -d
```
To view logs:
```bash
docker compose logs -f
```
To stop:
```bash
docker compose down
```

---

## Performance & NVIDIA RTX GPU Acceleration

To avoid CPU saturation when streaming 12+ cameras simultaneously, the simulator uses a **Dual-Strategy Architecture**:

1. **Strategy A (Permanent Feeds)**: Pre-transcoded with Baseline H.264, GOP 50, and 0 B-frames, streaming via `-c:v copy` (Zero-CPU pass-through).
2. **Strategy B (On-Demand Feeds)**: Dynamic videos requested on-the-fly use NVIDIA NVENC (`h264_nvenc`) hardware acceleration with bounded 1080p scaling.

> [!NOTE]
> Read the complete architectural analysis, benchmarks, and tuning tips in [PERFORMANCE_AND_GPU_GUIDE.md](file:///media/avaish/aiwork/camera-simulator/PERFORMANCE_AND_GPU_GUIDE.md).

### Batch Video Optimizer
To optimize all videos in `videos/` for zero-CPU streaming using the RTX GPU:
```bash
python3 scripts/stream_manager.py optimize
```
*(Original full-resolution files are safely preserved in `videos/raw/`).*

---

## CLI Reference

```bash
python3 scripts/stream_manager.py list              # List all available RTSP links
python3 scripts/stream_manager.py start             # Start the server
python3 scripts/stream_manager.py stop              # Stop the server
python3 scripts/stream_manager.py restart           # Restart the server
python3 scripts/stream_manager.py status            # Check server & stream health
python3 scripts/stream_manager.py optimize          # Optimize videos using RTX GPU (NVENC)
python3 scripts/stream_manager.py add <video_path>  # Convert & optimize a video to an RTSP link
python3 scripts/stream_manager.py test ppe          # Test and probe an RTSP stream locally
```
