# Videos Directory

This directory holds the video files that are converted into continuous RTSP camera streams.

## Pre-installed Industrial AI Sample Videos
- `ppe_detection.mp4`: Construction/factory site footage for testing PPE detection models (hard hats, safety vests, boots, etc.).
- `fire_smoke_detection.mp4`: Outdoor/industrial fire footage for testing fire and smoke detection models.
- `industrial_iot.mp4`: Industrial facility monitoring for anomaly detection, worker tracking, or intrusion detection.

## Adding Any New Downloaded Video
You can convert any video to an RTSP stream in two simple ways:

### Method 1: Using the Stream Manager CLI (Recommended)
Run the following command from the project root:
```bash
python3 scripts/stream_manager.py add /path/to/your/downloaded_video.mp4 --name warehouse-camera
```
This automatically ensures the video is encoded in RTSP-compatible H.264 format and prints your new RTSP URL immediately:
- Local: `rtsp://127.0.0.1:8554/warehouse-camera`
- Remote PC: `rtsp://<HOST_IP>:8554/warehouse-camera`

### Method 2: Direct File Drop
Simply copy any `.mp4` file directly into this `videos/` folder:
```bash
cp my_cctv_footage.mp4 videos/forklift_zone.mp4
```
MediaMTX is configured with **dynamic on-demand streaming**. As soon as any client requests:
`rtsp://<HOST_IP>:8554/forklift_zone`
it will automatically stream `videos/forklift_zone.mp4` on demand!
