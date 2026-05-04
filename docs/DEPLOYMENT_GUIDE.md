# Driver Safety Monitoring System - Multi-Mode Deployment Guide

## Overview

This system supports **seamless deployment** in both local and cloud environments:

- **Local Machine**: Uses local webcam via `cv2.VideoCapture(0)`
- **AWS EC2 / Cloud**: Uses alternative input sources (uploaded videos, RTSP streams, or mock mode)

## Architecture

### Video Source Abstraction Layer

The system uses a flexible abstraction layer with multiple input sources:

```
VideoSource (Base Class)
├── LocalCameraSource       → Local webcam (cv2.VideoCapture)
├── VideoFileSource         → Video file upload/playback
├── RTSPStreamSource        → RTSP/IP camera streams
└── MockSource              → Demo/simulated frames
```

### Backend Flow

```
FastAPI App
    ↓
MonitoringService
    ↓
VideoSource (selected based on CAMERA_MODE)
    ↓
FaceLandmarkDetector → EyeAnalyzer → FatigueMonitor → FusionEngine → AlertManager
    ↓
Video Stream Output (MJPEG via /video/stream endpoint)
```

## Deployment Modes

### 1. **Local Mode (Default)**

**Best for**: Development, local testing with webcam

**Setup**:
```bash
# Local machine with webcam
export CAMERA_MODE=local
export CAMERA_INDEX=0
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Behavior**:
- Automatically detects local camera
- Falls back to placeholder if camera unavailable
- Real-time processing at 15-30 FPS

---

### 2. **File Upload Mode (Cloud)**

**Best for**: Processing pre-recorded videos, demos, testing without hardware

**Setup**:
```bash
export CAMERA_MODE=file
export VIDEO_FILE_PATH=/path/to/video.mp4
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Frontend Flow**:
1. Select "Upload Video" button
2. Choose video file from local machine
3. Click "Upload & Process"
4. System starts analyzing uploaded video

**API Endpoint**:
```bash
POST /configure/file
Content-Type: multipart/form-data

file: <video_file>
```

---

### 3. **RTSP Stream Mode (Cloud)**

**Best for**: IP cameras, network streams, remote surveillance systems

**Setup**:
```bash
export CAMERA_MODE=rtsp
export STREAM_URL=rtsp://camera-ip:554/stream
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Frontend Flow**:
1. Select "Live Stream" button
2. Enter stream URL (RTSP or MJPEG)
3. Click "Connect"
4. System starts analyzing stream

**Common Stream URLs**:
```
RTSP:   rtsp://192.168.1.100:554/stream
MJPEG:  http://192.168.1.100:8080/stream
HLS:    http://192.168.1.100:8080/stream.m3u8
```

**API Endpoint**:
```bash
POST /configure/stream
Content-Type: application/x-www-form-urlencoded

stream_url=rtsp://camera-ip:554/stream
```

---

### 4. **Mock Mode (Demo)**

**Best for**: Demonstrations, testing without hardware/network

**Setup**:
```bash
export CAMERA_MODE=mock
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Behavior**:
- Generates simulated gradient frames
- Useful for UI/API testing
- No external dependencies needed

---

## Docker Deployment

### Build Image

```bash
docker build -t driver-safety-system:latest .
```

### Run in Local Mode

```bash
docker run -p 8000:8000 \
  -e CAMERA_MODE=local \
  --device /dev/video0:/dev/video0 \
  driver-safety-system:latest
```

### Run in Cloud Mode (File Upload)

```bash
docker run -p 8000:8000 \
  -e CAMERA_MODE=file \
  -v /local/uploads:/app/uploads \
  driver-safety-system:latest
```

### Run in Cloud Mode (RTSP Stream)

```bash
docker run -p 8000:8000 \
  -e CAMERA_MODE=rtsp \
  -e STREAM_URL=rtsp://camera-ip:554/stream \
  driver-safety-system:latest
```

### Run in Mock Mode

```bash
docker run -p 8000:8000 \
  -e CAMERA_MODE=mock \
  driver-safety-system:latest
```

### Docker Compose Example

```yaml
version: '3.8'

services:
  driver-safety:
    build: .
    ports:
      - "8000:8000"
    environment:
      CAMERA_MODE: "${CAMERA_MODE:-local}"
      CAMERA_INDEX: "0"
      FRAME_WIDTH: "1280"
      FRAME_HEIGHT: "720"
      VIDEO_FILE_PATH: "${VIDEO_FILE_PATH:-}"
      STREAM_URL: "${STREAM_URL:-}"
    volumes:
      - /dev/video0:/dev/video0  # For local camera
      - ./uploads:/app/uploads    # For file uploads
    devices:
      - /dev/video0              # For local camera access
```

**Run with docker-compose**:
```bash
# Local mode
docker-compose up

# Cloud mode (file)
CAMERA_MODE=file docker-compose up

# Cloud mode (RTSP)
CAMERA_MODE=rtsp STREAM_URL=rtsp://camera-ip:554/stream docker-compose up
```

---

## AWS EC2 Deployment

### EC2 Setup Steps

1. **Launch Instance**:
   - AMI: Ubuntu 20.04 LTS (or latest)
   - Instance Type: t3.medium (minimum)
   - Security Group: Open port 8000 (TCP)

2. **Install Docker**:
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo usermod -aG docker $USER
```

3. **Clone Repository**:
```bash
git clone <your-repo> driver-safety-system
cd driver-safety-system
```

4. **Run in Cloud Mode**:

**Option A: File Upload Mode**
```bash
docker run -d -p 8000:8000 \
  -e CAMERA_MODE=file \
  -v $(pwd)/uploads:/app/uploads \
  driver-safety-system:latest
```

**Option B: RTSP Stream Mode**
```bash
docker run -d -p 8000:8000 \
  -e CAMERA_MODE=rtsp \
  -e STREAM_URL=rtsp://your-camera:554/stream \
  driver-safety-system:latest
```

5. **Access Dashboard**:
```
http://<ec2-public-ip>:8000
```

---

## API Endpoints

### Core Endpoints

```
GET    /status              → System status
POST   /start               → Start monitoring
POST   /stop                → Stop monitoring
GET    /video/stream        → MJPEG video stream
GET    /modes               → Available camera modes
```

### Configuration Endpoints

```
POST   /configure/local     → Switch to local camera mode
POST   /configure/file      → Upload and configure video file
POST   /configure/rtsp      → Configure RTSP stream
POST   /configure/mock      → Switch to mock mode
```

### Example Requests

**Get Status**:
```bash
curl http://localhost:8000/status
```

**Start Monitoring**:
```bash
curl -X POST http://localhost:8000/start
```

**Upload Video File**:
```bash
curl -X POST http://localhost:8000/configure/file \
  -F "file=@/path/to/video.mp4"
```

**Configure Stream**:
```bash
curl -X POST http://localhost:8000/configure/stream \
  -d "stream_url=rtsp://camera-ip:554/stream"
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CAMERA_MODE` | `local` | Mode: `local`, `file`, `rtsp`, `mock` |
| `CAMERA_INDEX` | `0` | Webcam index for local mode |
| `FRAME_WIDTH` | `1280` | Frame width in pixels |
| `FRAME_HEIGHT` | `720` | Frame height in pixels |
| `VIDEO_FILE_PATH` | `` | Path to video file (file mode) |
| `STREAM_URL` | `` | RTSP/stream URL (rtsp mode) |

---

## Performance & Optimization

### Frame Processing Rates

| Mode | Typical FPS | Latency |
|------|------------|---------|
| Local Camera | 20-30 | Low (<100ms) |
| File Upload | Variable | Depends on file |
| RTSP Stream | 15-25 | Medium (200-500ms) |
| Mock | 30 | None |

### Optimization Tips

1. **Local Mode**:
   - Use USB 2.0 or better cameras
   - Keep frame resolution at 1280x720 or lower

2. **File Mode**:
   - Pre-compress videos (H.264, 720p)
   - Use local SSD storage

3. **RTSP Mode**:
   - Ensure camera supports H.264 codec
   - Test network bandwidth (recommend 5+ Mbps)
   - Use IP cameras on same network as server

4. **General**:
   - Disable low light equalization if CPU bottleneck
   - Use hardware acceleration if available

---

## Troubleshooting

### Local Camera Not Found

**Error**: "Camera not available (using local mode)"

**Solution**:
1. Verify camera device exists:
   ```bash
   ls /dev/video*
   ```
2. Check camera permissions:
   ```bash
   sudo chmod 666 /dev/video0
   ```
3. Switch to mock mode for testing:
   ```bash
   export CAMERA_MODE=mock
   ```

### File Upload Fails

**Error**: "Upload failed" or file not saved

**Solution**:
1. Check upload directory permissions:
   ```bash
   ls -la uploads/
   ```
2. Verify file format (MP4, AVI, MOV supported)
3. Check disk space:
   ```bash
   df -h
   ```

### RTSP Stream Connection Failed

**Error**: "Failed to connect to stream"

**Solution**:
1. Test stream URL with ffplay:
   ```bash
   ffplay rtsp://camera-ip:554/stream
   ```
2. Check network connectivity:
   ```bash
   ping camera-ip
   ```
3. Verify camera credentials in URL if needed:
   ```bash
   rtsp://username:password@camera-ip:554/stream
   ```
4. Check firewall rules

### High CPU Usage

**Error**: System becomes sluggish

**Solution**:
1. Reduce frame resolution (use 720p or lower)
2. Switch to mock mode to isolate issue
3. Check camera resolution (request lower from camera)
4. Disable low-light equalization

---

## Security Best Practices

✅ **DO:**
- Use HTTPS in production (nginx reverse proxy)
- Validate file uploads (check magic bytes)
- Limit upload file size
- Authenticate access to configuration endpoints
- Use VPC/security groups to restrict network access

❌ **DON'T:**
- Expose raw camera ports
- Store passwords in environment variables
- Run as root in containers
- Allow unrestricted file uploads

---

## Migration from Old System

### From Single-Mode to Multi-Mode

Old code:
```python
capture = cv2.VideoCapture(0)
```

New code:
```python
from backend.sources import get_video_source

video_source = get_video_source("local", camera_index=0)
if video_source.open():
    ret, frame = video_source.read()
```

This abstraction makes switching modes transparent to processing logic.

---

## Development & Testing

### Unit Tests

```bash
pytest tests/
```

### Local Testing with Mock

```bash
export CAMERA_MODE=mock
uvicorn backend.main:app --reload
```

### Integration Testing

```bash
# Test with local file
export CAMERA_MODE=file
export VIDEO_FILE_PATH=./test_video.mp4
uvicorn backend.main:app --reload
```

---

## Maintenance

### Log Files

```bash
# Docker logs
docker logs <container-id>

# Application logs (inside container)
tail -f /app/logs/app.log
```

### Cleanup Upload Directory

```bash
# Remove old uploads (older than 7 days)
find ./uploads -type f -mtime +7 -delete
```

### Monitor Resource Usage

```bash
# CPU and Memory
docker stats <container-id>

# Disk usage
du -sh uploads/
```

---

## Support & Resources

- **Issues**: Check logs with `docker logs`
- **API Docs**: Visit `http://localhost:8000/docs`
- **Video Feed**: Open `http://localhost:8000/video`
- **Status Dashboard**: Visit `http://localhost:8000/`

---

## Version Info

- **Python**: 3.10+
- **OpenCV**: 4.10.0+
- **MediaPipe**: 0.10.33+
- **FastAPI**: 0.115.0+
- **Docker**: 20.10+
