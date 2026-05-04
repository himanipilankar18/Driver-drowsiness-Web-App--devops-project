FROM python:3.10-slim

WORKDIR /app

# ✅ Install system dependencies for OpenCV and network streaming
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

# Create upload directory for cloud mode
RUN mkdir -p /app/uploads

# Environment variables for camera mode
ENV CAMERA_MODE=local
ENV CAMERA_INDEX=0
ENV FRAME_WIDTH=1280
ENV FRAME_HEIGHT=720
ENV VIDEO_FILE_PATH=""
ENV STREAM_URL=""

EXPOSE 8000

# Run with full output (no buffering)
CMD ["python", "-u", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
