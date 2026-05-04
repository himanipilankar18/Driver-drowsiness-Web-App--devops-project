"""
Video source abstraction layer for supporting multiple input modes.
Supports: Local camera, video files, RTSP streams, and mock data.
"""

import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class VideoSource(ABC):
    """Base class for video sources."""

    def __init__(self, frame_width: int = 1280, frame_height: int = 720):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self._is_open = False

    @abstractmethod
    def open(self) -> bool:
        """Open the video source. Returns True if successful."""
        pass

    @abstractmethod
    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read next frame. Returns (success, frame) tuple."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the video source."""
        pass

    def is_open(self) -> bool:
        """Check if source is open."""
        return self._is_open

    def release(self) -> None:
        """Release resources (alias for close)."""
        self.close()


class LocalCameraSource(VideoSource):
    """Local webcam via cv2.VideoCapture."""

    def __init__(
        self,
        camera_index: int = 0,
        frame_width: int = 1280,
        frame_height: int = 720,
    ):
        super().__init__(frame_width, frame_height)
        self.camera_index = camera_index
        self._capture: Optional[cv2.VideoCapture] = None

    def open(self) -> bool:
        """Open local camera."""
        try:
            self._capture = cv2.VideoCapture(self.camera_index)
            if not self._capture.isOpened():
                logger.warning(f"Failed to open camera at index {self.camera_index}")
                return False

            # Set resolution
            self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)

            # Test by reading one frame
            ret, frame = self._capture.read()
            if not ret or frame is None:
                logger.warning("Camera opened but cannot read frames")
                self._capture.release()
                self._capture = None
                return False

            self._is_open = True
            logger.info(f"Local camera opened successfully (index: {self.camera_index})")
            return True
        except Exception as e:
            logger.error(f"Error opening local camera: {e}")
            return False

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read frame from camera."""
        if not self._is_open or self._capture is None:
            return False, None
        try:
            ret, frame = self._capture.read()
            return ret, frame
        except Exception as e:
            logger.error(f"Error reading from camera: {e}")
            return False, None

    def close(self) -> None:
        """Close camera."""
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        self._is_open = False
        logger.info("Local camera closed")


class VideoFileSource(VideoSource):
    """Video file playback (useful for testing and cloud mode)."""

    def __init__(
        self,
        file_path: str,
        frame_width: int = 1280,
        frame_height: int = 720,
        loop: bool = True,
    ):
        super().__init__(frame_width, frame_height)
        self.file_path = Path(file_path)
        self.loop = loop
        self._capture: Optional[cv2.VideoCapture] = None
        self._total_frames = 0
        self._frame_count = 0

    def open(self) -> bool:
        """Open video file."""
        try:
            if not self.file_path.exists():
                logger.error(f"Video file not found: {self.file_path}")
                return False

            self._capture = cv2.VideoCapture(str(self.file_path))
            if not self._capture.isOpened():
                logger.error(f"Failed to open video file: {self.file_path}")
                return False

            self._total_frames = int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT))
            self._frame_count = 0

            # Set resolution
            self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)

            self._is_open = True
            logger.info(f"Video file opened: {self.file_path} ({self._total_frames} frames)")
            return True
        except Exception as e:
            logger.error(f"Error opening video file: {e}")
            return False

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read frame from video file."""
        if not self._is_open or self._capture is None:
            return False, None

        try:
            ret, frame = self._capture.read()

            if not ret:
                if self.loop:
                    # Restart video
                    self._capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self._frame_count = 0
                    ret, frame = self._capture.read()
                else:
                    logger.info("End of video file reached")
                    return False, None

            self._frame_count += 1

            # Resize if needed
            if frame is not None:
                h, w = frame.shape[:2]
                if w != self.frame_width or h != self.frame_height:
                    frame = cv2.resize(frame, (self.frame_width, self.frame_height))

            return ret, frame
        except Exception as e:
            logger.error(f"Error reading from video file: {e}")
            return False, None

    def close(self) -> None:
        """Close video file."""
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        self._is_open = False
        logger.info("Video file closed")


class RTSPStreamSource(VideoSource):
    """RTSP or HTTP stream source (IP cameras, MJPEG servers)."""

    def __init__(
        self,
        stream_url: str,
        frame_width: int = 1280,
        frame_height: int = 720,
        timeout: int = 5,
    ):
        super().__init__(frame_width, frame_height)
        self.stream_url = stream_url
        self.timeout = timeout
        self._capture: Optional[cv2.VideoCapture] = None

    def open(self) -> bool:
        """Open RTSP/stream source."""
        try:
            # Set timeout and buffer size for network streams
            self._capture = cv2.VideoCapture(self.stream_url)

            # Configure for network streaming
            self._capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimal buffering
            self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)

            # Test connection
            ret, frame = self._capture.read()
            if not ret or frame is None:
                logger.error(f"Failed to connect to stream: {self.stream_url}")
                if self._capture:
                    self._capture.release()
                self._capture = None
                return False

            self._is_open = True
            logger.info(f"RTSP stream connected: {self.stream_url}")
            return True
        except Exception as e:
            logger.error(f"Error connecting to stream: {e}")
            return False

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read frame from stream."""
        if not self._is_open or self._capture is None:
            return False, None

        try:
            ret, frame = self._capture.read()

            if not ret or frame is None:
                logger.warning("Failed to read from stream, attempting reconnect")
                return False, None

            # Resize if needed
            if frame is not None:
                h, w = frame.shape[:2]
                if w != self.frame_width or h != self.frame_height:
                    frame = cv2.resize(frame, (self.frame_width, self.frame_height))

            return ret, frame
        except Exception as e:
            logger.error(f"Error reading from stream: {e}")
            return False, None

    def close(self) -> None:
        """Close stream."""
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        self._is_open = False
        logger.info("RTSP stream closed")


class MockSource(VideoSource):
    """Mock/demo source with simulated frames."""

    def __init__(self, frame_width: int = 1280, frame_height: int = 720):
        super().__init__(frame_width, frame_height)
        self._frame_count = 0
        self._start_time = None

    def open(self) -> bool:
        """Open mock source."""
        self._is_open = True
        self._start_time = time.time()
        self._frame_count = 0
        logger.info("Mock source initialized")
        return True

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Generate mock frame."""
        if not self._is_open:
            return False, None

        try:
            # Create a gradient frame with timestamp
            frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)

            # Create gradient background
            for i in range(self.frame_height):
                frame[i, :] = [
                    int(255 * (i / self.frame_height)),
                    128,
                    int(255 * (1 - i / self.frame_height)),
                ]

            # Add text overlay
            elapsed = time.time() - self._start_time
            text = f"Mock Frame #{self._frame_count} | Time: {elapsed:.1f}s"
            cv2.putText(
                frame,
                text,
                (50, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (255, 255, 255),
                2,
            )

            self._frame_count += 1

            # Simulate ~30 FPS
            time.sleep(0.033)

            return True, frame
        except Exception as e:
            logger.error(f"Error generating mock frame: {e}")
            return False, None

    def close(self) -> None:
        """Close mock source."""
        self._is_open = False
        logger.info("Mock source closed")


def get_video_source(
    mode: str,
    camera_index: int = 0,
    file_path: Optional[str] = None,
    stream_url: Optional[str] = None,
    frame_width: int = 1280,
    frame_height: int = 720,
) -> Optional[VideoSource]:
    """
    Factory function to create appropriate video source.

    Args:
        mode: "local", "file", "rtsp", or "mock"
        camera_index: Index for local camera (default 0)
        file_path: Path to video file (required for "file" mode)
        stream_url: RTSP/stream URL (required for "rtsp" mode)
        frame_width: Frame width in pixels
        frame_height: Frame height in pixels

    Returns:
        VideoSource instance or None if invalid configuration
    """
    mode = mode.lower().strip()

    if mode == "local":
        return LocalCameraSource(camera_index, frame_width, frame_height)
    elif mode == "file":
        if not file_path:
            logger.error("file_path required for 'file' mode")
            return None
        return VideoFileSource(file_path, frame_width, frame_height)
    elif mode == "rtsp":
        if not stream_url:
            logger.error("stream_url required for 'rtsp' mode")
            return None
        return RTSPStreamSource(stream_url, frame_width, frame_height)
    elif mode == "mock":
        return MockSource(frame_width, frame_height)
    else:
        logger.error(f"Unknown video source mode: {mode}")
        return None
