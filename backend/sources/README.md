# Video Source Abstraction Layer

## Overview

The video source abstraction layer provides a unified interface for multiple input sources, making it easy to switch between local cameras, files, streams, and mock data without changing the core processing logic.

## Architecture

```python
VideoSource (ABC)
    ├── LocalCameraSource         # cv2.VideoCapture(0)
    ├── VideoFileSource           # MP4, AVI, MOV playback
    ├── RTSPStreamSource          # RTSP, MJPEG, HTTP streams
    └── MockSource                # Simulated gradient frames
```

## Usage

### Basic Usage

```python
from backend.sources import get_video_source

# Create video source
video_source = get_video_source("local", camera_index=0)

# Open source
if video_source.open():
    # Read frames
    while True:
        ret, frame = video_source.read()
        if not ret:
            break
        # Process frame...
    
    # Close source
    video_source.close()
```

### Mode-Specific Examples

#### Local Camera
```python
source = get_video_source(
    "local",
    camera_index=0,
    frame_width=1280,
    frame_height=720
)
```

#### Video File
```python
source = get_video_source(
    "file",
    file_path="/path/to/video.mp4",
    frame_width=1280,
    frame_height=720,
    loop=True  # Restart video when finished
)
```

#### RTSP Stream
```python
source = get_video_source(
    "rtsp",
    stream_url="rtsp://camera:554/stream",
    frame_width=1280,
    frame_height=720,
    timeout=5
)
```

#### Mock Source
```python
source = get_video_source(
    "mock",
    frame_width=1280,
    frame_height=720
)
```

## Class Reference

### VideoSource (Base Class)

Abstract base class for all video sources.

**Methods:**
- `open() -> bool`: Open the video source
- `read() -> Tuple[bool, Optional[np.ndarray]]`: Read next frame
- `close() -> None`: Close the source
- `is_open() -> bool`: Check if source is open
- `release() -> None`: Alias for close()

**Properties:**
- `frame_width`: Width of frames in pixels
- `frame_height`: Height of frames in pixels

---

### LocalCameraSource

Local webcam via OpenCV.

**Constructor:**
```python
LocalCameraSource(
    camera_index: int = 0,
    frame_width: int = 1280,
    frame_height: int = 720
)
```

**Features:**
- Supports multiple cameras (index 0, 1, 2, ...)
- Auto-detects camera availability
- Configurable resolution

**Example:**
```python
camera = LocalCameraSource(camera_index=0)
if camera.open():
    while True:
        ret, frame = camera.read()
        if ret:
            cv2.imshow("Camera", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    camera.close()
```

---

### VideoFileSource

Video file playback with optional looping.

**Constructor:**
```python
VideoFileSource(
    file_path: str,
    frame_width: int = 1280,
    frame_height: int = 720,
    loop: bool = True
)
```

**Features:**
- Supports MP4, AVI, MOV, MKV formats
- Optional looping
- Auto-resizing to target resolution
- Progress tracking

**Example:**
```python
video = VideoFileSource(
    file_path="sample.mp4",
    loop=True
)
if video.open():
    for _ in range(100):
        ret, frame = video.read()
        if ret:
            # Process frame
            pass
    video.close()
```

---

### RTSPStreamSource

Network stream input (RTSP, MJPEG, HTTP).

**Constructor:**
```python
RTSPStreamSource(
    stream_url: str,
    frame_width: int = 1280,
    frame_height: int = 720,
    timeout: int = 5
)
```

**Supported Formats:**
- RTSP: `rtsp://camera:554/stream`
- MJPEG: `http://camera:8080/stream`
- HTTP: `http://camera:8080/video.mp4`
- HLS: `http://camera:8080/stream.m3u8`

**Features:**
- Minimal buffering for low latency
- Auto-reconnect capability
- Timeout handling

**Example:**
```python
stream = RTSPStreamSource(
    stream_url="rtsp://192.168.1.100:554/stream"
)
if stream.open():
    while True:
        ret, frame = stream.read()
        if ret:
            # Process frame
            pass
        else:
            print("Reconnecting...")
            break
    stream.close()
```

---

### MockSource

Simulated frames for testing/demo.

**Constructor:**
```python
MockSource(
    frame_width: int = 1280,
    frame_height: int = 720
)
```

**Features:**
- Generates gradient frames with timestamp
- ~30 FPS simulation
- No external dependencies

**Example:**
```python
mock = MockSource()
if mock.open():
    for i in range(100):
        ret, frame = mock.read()
        if ret:
            print(f"Frame {i}: {frame.shape}")
    mock.close()
```

---

## Error Handling

### Graceful Degradation

```python
video_source = get_video_source("local")

if not video_source:
    print("Invalid configuration, falling back to mock")
    video_source = get_video_source("mock")

if not video_source.open():
    print("Failed to open source")
    exit(1)
```

### Connection Retry

```python
max_retries = 3
retry_count = 0

while retry_count < max_retries:
    if video_source.open():
        break
    retry_count += 1
    print(f"Retry {retry_count}/{max_retries}")
    time.sleep(2)
```

---

## Performance Considerations

### Frame Rate Targeting

```python
import time

fps_target = 30
frame_time = 1.0 / fps_target

while True:
    start = time.time()
    
    ret, frame = video_source.read()
    if ret:
        # Process frame...
        pass
    
    elapsed = time.time() - start
    sleep_time = max(0, frame_time - elapsed)
    time.sleep(sleep_time)
```

### Resolution Optimization

```python
# For real-time processing
source = get_video_source("local", frame_width=640, frame_height=480)

# For accuracy
source = get_video_source("local", frame_width=1280, frame_height=720)

# For bandwidth-limited streams
source = get_video_source("rtsp", frame_width=640, frame_height=360, 
                         stream_url="rtsp://camera:554/stream")
```

---

## Integration with MonitoringService

```python
from backend.sources import get_video_source

class MonitoringService:
    def __init__(self):
        self._video_source = None
    
    def start(self, camera_mode: str, **kwargs):
        # Create appropriate source
        self._video_source = get_video_source(camera_mode, **kwargs)
        
        # Attempt to open
        if not self._video_source.open():
            self._video_source = None
            return False
        
        return True
    
    def _run(self):
        while not self._stop_event.is_set():
            if self._video_source is None:
                time.sleep(0.2)
                continue
            
            ret, frame = self._video_source.read()
            if not ret:
                self._video_source.close()
                self._video_source = None
                continue
            
            # Process frame...
```

---

## Troubleshooting

### Camera Not Detected

```python
import cv2
from backend.sources import LocalCameraSource

# Check available cameras
for i in range(5):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print(f"Camera {i} found")
        cap.release()
    else:
        print(f"Camera {i} not found")
```

### Stream Connection Failed

```python
# Test RTSP stream with ffprobe
import subprocess

stream_url = "rtsp://camera:554/stream"
try:
    result = subprocess.run(
        ["ffprobe", "-v", "error", stream_url],
        capture_output=True
    )
    print("Stream is valid" if result.returncode == 0 else "Stream failed")
except Exception as e:
    print(f"ffprobe error: {e}")
```

### Low Frame Rate

```python
import time

start = time.time()
frame_count = 0

while frame_count < 100:
    ret, frame = video_source.read()
    if ret:
        frame_count += 1

elapsed = time.time() - start
fps = frame_count / elapsed
print(f"Actual FPS: {fps:.1f}")

# If low, try:
# 1. Reduce resolution
# 2. Switch to mock mode to test
# 3. Check network bandwidth for streams
# 4. Close other applications
```

---

## Testing

### Unit Tests

```python
import pytest
from backend.sources import get_video_source, MockSource

def test_mock_source():
    source = MockSource()
    assert source.open()
    assert source.is_open()
    
    ret, frame = source.read()
    assert ret and frame is not None
    assert frame.shape == (720, 1280, 3)
    
    source.close()
    assert not source.is_open()

def test_video_file_source():
    source = get_video_source("file", file_path="test.mp4")
    assert source is not None
    assert source.open()
    
    for _ in range(10):
        ret, frame = source.read()
        assert ret and frame is not None
    
    source.close()
```

---

## Future Extensions

Potential additions to the abstraction layer:

1. **WebRTC Source**: Browser-based camera via WebRTC
2. **HTTP POST Source**: Frames sent via HTTP POST
3. **Kafka Source**: Stream from Kafka topics
4. **Database Source**: Frames stored in database
5. **Azure Blob Source**: Stream from cloud storage

---

## License

Same as parent project.
