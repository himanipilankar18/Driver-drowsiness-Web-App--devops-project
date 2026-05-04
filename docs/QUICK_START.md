# Quick Start Guide - Driver Safety Monitoring System

## 🚀 Quick Setup

### Local Machine (with Webcam)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run system
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 3. Open browser
# http://localhost:8000

# 4. Click "Start Monitoring"
```

**Result**: Real-time driver monitoring with your webcam ✅

---

### Cloud Server (EC2 without Camera)

#### Option A: Upload Video for Analysis

```bash
# 1. On your server, set environment
export CAMERA_MODE=file

# 2. Run system
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 3. Open browser
# http://ec2-public-ip:8000

# 4. Click "Upload Video" tab
# 5. Select a video file
# 6. Click "Upload & Process"
```

**Result**: System analyzes your uploaded video ✅

---

#### Option B: Connect to IP Camera

```bash
# 1. On your server, set environment
export CAMERA_MODE=rtsp
export STREAM_URL=rtsp://camera-ip:554/stream

# 2. Run system
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 3. Open browser
# http://ec2-public-ip:8000

# 4. Click "Start Monitoring"
```

**Result**: System connects to IP camera stream ✅

---

#### Option C: Demo/Test Mode (No Hardware Needed)

```bash
# 1. Set environment
export CAMERA_MODE=mock

# 2. Run system
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 3. Open browser
# http://ec2-public-ip:8000

# 4. Click "Start Monitoring"
```

**Result**: System runs in demo mode with simulated frames ✅

---

## 🐳 Docker Quick Start

### Build

```bash
docker build -t driver-safety:latest .
```

### Run Local Mode

```bash
docker run -p 8000:8000 \
  -e CAMERA_MODE=local \
  --device /dev/video0:/dev/video0 \
  driver-safety:latest
```

### Run Cloud Mode (File)

```bash
docker run -p 8000:8000 \
  -e CAMERA_MODE=file \
  -v ./uploads:/app/uploads \
  driver-safety:latest
```

### Run Cloud Mode (Stream)

```bash
docker run -p 8000:8000 \
  -e CAMERA_MODE=rtsp \
  -e STREAM_URL=rtsp://camera-ip:554/stream \
  driver-safety:latest
```

---

## 📊 Dashboard Features

| Feature | Local | File | Stream | Mock |
|---------|-------|------|--------|------|
| Real-time monitoring | ✅ | ✅ | ✅ | ✅ |
| Fatigue detection | ✅ | ✅ | ✅ | ✅ |
| Distraction detection | ✅ | ✅ | ✅ | ✅ |
| Face detection | ✅ | ✅ | ✅ | ✅ |
| Alerts | ✅ | ✅ | ✅ | ✅ |

---

## 🔧 Configuration

### Environment Variables

```bash
# Which mode to use
export CAMERA_MODE=local|file|rtsp|mock

# For file mode
export VIDEO_FILE_PATH=/path/to/video.mp4

# For RTSP mode
export STREAM_URL=rtsp://camera-ip:554/stream

# Frame settings
export FRAME_WIDTH=1280
export FRAME_HEIGHT=720
```

---

## 📡 API Examples

### Get Status
```bash
curl http://localhost:8000/status
```

### Start Monitoring
```bash
curl -X POST http://localhost:8000/start
```

### Upload Video
```bash
curl -X POST http://localhost:8000/configure/file \
  -F "file=@video.mp4"
```

### Configure Stream
```bash
curl -X POST http://localhost:8000/configure/stream \
  -d "stream_url=rtsp://192.168.1.100:554/stream"
```

### Watch Video Stream
```
Open in browser:
http://localhost:8000/video
```

---

## 🎯 Common Use Cases

### Scenario 1: Local Development
```bash
export CAMERA_MODE=local
python -m uvicorn backend.main:app --reload
# → Use webcam for testing
```

### Scenario 2: Test with Sample Video
```bash
export CAMERA_MODE=file
export VIDEO_FILE_PATH=./sample.mp4
python -m uvicorn backend.main:app
# → Upload and analyze video
```

### Scenario 3: Monitor IP Camera
```bash
export CAMERA_MODE=rtsp
export STREAM_URL=rtsp://192.168.1.50:554/stream
python -m uvicorn backend.main:app
# → Connect to camera
```

### Scenario 4: Demo/Presentation
```bash
export CAMERA_MODE=mock
python -m uvicorn backend.main:app
# → Run without any hardware
```

---

## 🚨 Troubleshooting

| Issue | Solution |
|-------|----------|
| Camera not found | Switch to mock mode: `CAMERA_MODE=mock` |
| Upload fails | Check disk space, verify video format |
| Stream won't connect | Test URL with `ffplay` or `vlc` |
| High CPU usage | Reduce frame resolution or use mock mode |

---

## 📚 Next Steps

1. **Read Full Guide**: See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
2. **Check API Docs**: Visit `http://localhost:8000/docs`
3. **View Video Feed**: Open `http://localhost:8000/video`
4. **Explore Source Code**: Check `backend/sources/video_source.py`

---

## 🎓 Architecture

```
┌─────────────────────────────────────────┐
│         Frontend Dashboard              │
│  (Mode Selection + Video Feed)          │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│        FastAPI Backend                  │
│  (/configure, /start, /stop, /status)  │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│      MonitoringService                  │
│  (Thread-based processing)              │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│      VideoSource (Abstract)             │
│  ┌──────────────────────────────────┐   │
│  ├─ LocalCameraSource              │   │
│  ├─ VideoFileSource                │   │
│  ├─ RTSPStreamSource               │   │
│  └─ MockSource                     │   │
└────────────┬────────────────────────────┘
             │
┌────────────▼────────────────────────────┐
│  Processing Pipeline                    │
│  Frame → Detect → Analyze → Alert      │
└─────────────────────────────────────────┘
```

---

## 💡 Tips & Tricks

- **Switch modes on the fly**: Use the dashboard mode selector
- **Monitor logs**: `docker logs -f <container-id>`
- **Test streams**: Use `ffprobe` to check stream URL validity
- **Performance**: Use 720p for better real-time performance
- **Security**: Put nginx reverse proxy in front for production

---

**Happy Monitoring! 🎥✨**
