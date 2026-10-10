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
- **Zero-CPU Pass-through**: Uses `-stream_loop -1 -c:v copy` whenever possible to loop streams indefinitely without consuming heavy CPU or GPU resources.
- **Instant Web Browser Viewing**: Includes built-in WebRTC (`http://<HOST_IP>:8889/<stream>`) to watch streams in Google Chrome, Edge, or Firefox without installing VLC or any media player.
- **Interactive CLI Manager**: `python3 scripts/stream_manager.py` automatically detects host LAN IP, lists all stream URLs, and manages server lifecycle.

---

## Directory Structure

```
camera-simulator/
├── bin/
│   └── mediamtx                  # MediaMTX standalone binary (v1.21.2)
├── config/
│   └── mediamtx.yml              # Server & stream paths configuration
├── videos/                       # Place downloaded video files here
│   ├── ppe_detection.mp4         # Sample PPE detection video
│   ├── fire_smoke_detection.mp4  # Sample Fire & Smoke detection video
│   └── industrial_iot.mp4        # Sample Industrial IoT video
├── scripts/
│   ├── setup.sh                  # Checks dependencies & downloads assets
│   ├── download_samples.py       # Downloads industrial sample videos
│   ├── stream_manager.py         # CLI manager (start, stop, list, add, test)
│   └── test_client.py            # Local/remote RTSP stream test utility
├── run.sh                        # One-click start script
├── stop.sh                       # One-click stop script
├── docker-compose.yml            # Docker deployment option
├── requirements.txt              # Optional Python test dependencies
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

| Stream Name | Description | Local RTSP URL | Remote PC (LAN) URL | Web Browser (WebRTC) |
|---|---|---|---|---|
| **ppe** | PPE Detection (Hard Hats, Safety Vests) | `rtsp://127.0.0.1:8554/ppe` | `rtsp://<HOST_IP>:8554/ppe` | `http://<HOST_IP>:8889/ppe` |
| **fire-smoke** | Fire & Smoke Hazard Detection | `rtsp://127.0.0.1:8554/fire-smoke` | `rtsp://<HOST_IP>:8554/fire-smoke` | `http://<HOST_IP>:8889/fire-smoke` |
| **industrial-iot** | Facility / Industrial Surveillance | `rtsp://127.0.0.1:8554/industrial-iot` | `rtsp://<HOST_IP>:8554/industrial-iot` | `http://<HOST_IP>:8889/industrial-iot` |

*(Replace `<HOST_IP>` with the IP printed by `python3 scripts/stream_manager.py list`, e.g. `192.168.1.50`)*

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

## CLI Reference

```bash
python3 scripts/stream_manager.py list              # List all available RTSP links
python3 scripts/stream_manager.py start             # Start the server
python3 scripts/stream_manager.py stop              # Stop the server
python3 scripts/stream_manager.py restart           # Restart the server
python3 scripts/stream_manager.py status            # Check server & stream health
python3 scripts/stream_manager.py add <video_path>  # Convert a downloaded video to an RTSP link
python3 scripts/stream_manager.py test ppe          # Test and probe an RTSP stream locally
```
