# Configuration Examples

## Environment Variable Reference

Set these before running the application:

```bash
# Core camera mode selection
export CAMERA_MODE=local                    # local, file, rtsp, mock
export CAMERA_INDEX=0                       # Webcam index for local mode

# Frame dimensions
export FRAME_WIDTH=1280
export FRAME_HEIGHT=720

# Cloud mode specific
export VIDEO_FILE_PATH=/path/to/video.mp4   # For file mode
export STREAM_URL=rtsp://camera:554/stream  # For RTSP mode
```

## Example Configurations

### 1. Local Development

```bash
#!/bin/bash
export CAMERA_MODE=local
export CAMERA_INDEX=0
export FRAME_WIDTH=1280
export FRAME_HEIGHT=720

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Production - AWS EC2 (File Mode)

```bash
#!/bin/bash
export CAMERA_MODE=file
export VIDEO_FILE_PATH=/app/uploads/driver_video.mp4
export FRAME_WIDTH=1280
export FRAME_HEIGHT=720

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 3. Production - AWS EC2 (RTSP Mode)

```bash
#!/bin/bash
export CAMERA_MODE=rtsp
export STREAM_URL=rtsp://192.168.1.50:554/stream
export FRAME_WIDTH=1280
export FRAME_HEIGHT=720

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 4. Demo Mode

```bash
#!/bin/bash
export CAMERA_MODE=mock
export FRAME_WIDTH=1280
export FRAME_HEIGHT=720

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## Docker Configurations

### Docker Run - Local Mode

```bash
docker run \
  -p 8000:8000 \
  -e CAMERA_MODE=local \
  -e CAMERA_INDEX=0 \
  -e FRAME_WIDTH=1280 \
  -e FRAME_HEIGHT=720 \
  --device /dev/video0:/dev/video0 \
  driver-safety-system:latest
```

### Docker Run - File Mode

```bash
docker run \
  -p 8000:8000 \
  -e CAMERA_MODE=file \
  -e VIDEO_FILE_PATH=/app/uploads/video.mp4 \
  -e FRAME_WIDTH=1280 \
  -e FRAME_HEIGHT=720 \
  -v /local/uploads:/app/uploads \
  driver-safety-system:latest
```

### Docker Run - RTSP Mode

```bash
docker run \
  -p 8000:8000 \
  -e CAMERA_MODE=rtsp \
  -e STREAM_URL=rtsp://192.168.1.50:554/stream \
  -e FRAME_WIDTH=1280 \
  -e FRAME_HEIGHT=720 \
  driver-safety-system:latest
```

### Docker Compose - Multi-Mode

```yaml
version: '3.8'

services:
  driver-safety-local:
    build: .
    container_name: driver-safety-local
    ports:
      - "8001:8000"
    environment:
      CAMERA_MODE: "local"
      CAMERA_INDEX: "0"
      FRAME_WIDTH: "1280"
      FRAME_HEIGHT: "720"
    devices:
      - /dev/video0:/dev/video0
    restart: unless-stopped

  driver-safety-cloud:
    build: .
    container_name: driver-safety-cloud
    ports:
      - "8002:8000"
    environment:
      CAMERA_MODE: "file"
      VIDEO_FILE_PATH: "/app/uploads/video.mp4"
      FRAME_WIDTH: "1280"
      FRAME_HEIGHT: "720"
    volumes:
      - ./uploads:/app/uploads
    restart: unless-stopped
```

## Environment File (.env)

```bash
# .env
CAMERA_MODE=local
CAMERA_INDEX=0
FRAME_WIDTH=1280
FRAME_HEIGHT=720
VIDEO_FILE_PATH=
STREAM_URL=
```

Load with:
```bash
set -a
source .env
set +a
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## Performance Tuning

### For Real-Time Local Processing

```bash
export CAMERA_MODE=local
export FRAME_WIDTH=640      # Reduce for faster processing
export FRAME_HEIGHT=480
```

### For High-Accuracy Cloud Processing

```bash
export CAMERA_MODE=file
export VIDEO_FILE_PATH=/path/to/video.mp4
export FRAME_WIDTH=1280     # Higher resolution for accuracy
export FRAME_HEIGHT=720
```

### For Stream Processing (Balance)

```bash
export CAMERA_MODE=rtsp
export STREAM_URL=rtsp://camera:554/stream
export FRAME_WIDTH=960      # Balance between speed and accuracy
export FRAME_HEIGHT=540
```

## AWS EC2 Startup Script

```bash
#!/bin/bash
# startup.sh

# Update system
sudo apt-get update
sudo apt-get install -y docker.io

# Start Docker
sudo systemctl start docker

# Create uploads directory
mkdir -p /app/uploads

# Set environment
export CAMERA_MODE=file
export FRAME_WIDTH=1280
export FRAME_HEIGHT=720

# Build and run
cd /home/ubuntu/driver-safety-system
docker build -t driver-safety:latest .
docker run -d \
  -p 8000:8000 \
  -e CAMERA_MODE=$CAMERA_MODE \
  -e FRAME_WIDTH=$FRAME_WIDTH \
  -e FRAME_HEIGHT=$FRAME_HEIGHT \
  -v /app/uploads:/app/uploads \
  --restart unless-stopped \
  driver-safety:latest

# Check status
sleep 5
curl http://localhost:8000/status
```

## Load Balancing (Multiple Instances)

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - safety-1
      - safety-2

  safety-1:
    build: .
    environment:
      CAMERA_MODE: "file"
      VIDEO_FILE_PATH: "/app/uploads/video1.mp4"

  safety-2:
    build: .
    environment:
      CAMERA_MODE: "file"
      VIDEO_FILE_PATH: "/app/uploads/video2.mp4"
```

### nginx.conf

```nginx
upstream safety_backend {
    server safety-1:8000;
    server safety-2:8000;
}

server {
    listen 80;
    
    location / {
        proxy_pass http://safety_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /video/stream {
        proxy_pass http://safety_backend;
        proxy_buffering off;
        proxy_request_buffering off;
    }
}
```

## Monitoring & Logging

```bash
# Docker logs
docker logs -f <container-id>

# Follow logs with timestamps
docker logs -f --timestamps <container-id>

# Save logs to file
docker logs <container-id> > app.log 2>&1

# Real-time monitoring
watch -n 1 'docker stats --no-stream <container-id>'
```

## Health Check

```yaml
version: '3.8'

services:
  driver-safety:
    build: .
    environment:
      CAMERA_MODE: "local"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/status"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped
```

## Kubernetes Deployment

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: driver-safety-config
data:
  CAMERA_MODE: "file"
  FRAME_WIDTH: "1280"
  FRAME_HEIGHT: "720"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: driver-safety
spec:
  replicas: 2
  selector:
    matchLabels:
      app: driver-safety
  template:
    metadata:
      labels:
        app: driver-safety
    spec:
      containers:
      - name: driver-safety
        image: driver-safety:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: driver-safety-config
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        volumeMounts:
        - name: uploads
          mountPath: /app/uploads
      volumes:
      - name: uploads
        emptyDir: {}
```

## Summary

Choose the configuration that best fits your deployment:

- **Local**: Development with webcam
- **File**: Cloud with video uploads
- **RTSP**: Cloud with IP camera streams
- **Mock**: Testing without hardware
