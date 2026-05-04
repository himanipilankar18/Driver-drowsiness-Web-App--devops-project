"""
Browser-based camera frame receiver for cloud deployment.

This module handles receiving video frames from a browser-based camera source,
enabling the system to work on cloud servers without physical cameras.
"""

import base64
import io
import logging
import queue
import threading
import time
from typing import Optional, Tuple

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class BrowserCameraReceiver:
    """
    Receives frames from browser via WebSocket or HTTP endpoints.
    Manages frame buffering and provides interface for MonitoringService.
    """

    def __init__(self, max_queue_size: int = 30, frame_timeout: float = 2.0):
        """
        Initialize the browser camera receiver.

        Args:
            max_queue_size: Maximum frames to buffer (FIFO)
            frame_timeout: Seconds to wait for frame before timeout
        """
        self._queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self._frame_timeout = frame_timeout
        self._last_frame_time = 0.0
        self._frame_count = 0
        self._error_count = 0
        self._lock = threading.Lock()
        self._is_open = False

    def open(self) -> bool:
        """Open the receiver for frame input."""
        with self._lock:
            self._is_open = True
            self._frame_count = 0
            self._error_count = 0
            logger.info("Browser camera receiver opened")
        return True

    def close(self) -> bool:
        """Close the receiver and clear queue."""
        with self._lock:
            self._is_open = False
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break
            logger.info(
                f"Browser camera receiver closed. "
                f"Frames: {self._frame_count}, Errors: {self._error_count}"
            )
        return True

    def is_open(self) -> bool:
        """Check if receiver is open."""
        with self._lock:
            return self._is_open

    def submit_frame_base64(self, frame_base64: str) -> bool:
        """
        Submit a frame as Base64-encoded JPEG string.

        Args:
            frame_base64: Base64-encoded JPEG data

        Returns:
            True if frame accepted, False if rejected
        """
        try:
            with self._lock:
                if not self._is_open:
                    return False

            # Decode Base64
            frame_bytes = base64.b64decode(frame_base64.encode())

            # Decode JPEG to numpy array
            frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)

            if frame is None:
                with self._lock:
                    self._error_count += 1
                logger.warning("Failed to decode frame from Base64")
                return False

            # Add to queue (drop oldest if full)
            try:
                self._queue.put_nowait(frame)
                with self._lock:
                    self._frame_count += 1
                    self._last_frame_time = time.time()
                return True
            except queue.Full:
                # Drop oldest frame and try again
                try:
                    self._queue.get_nowait()
                    self._queue.put_nowait(frame)
                    with self._lock:
                        self._frame_count += 1
                        self._last_frame_time = time.time()
                    logger.debug("Dropped oldest frame to make room")
                    return True
                except queue.Empty:
                    return False

        except Exception as e:
            with self._lock:
                self._error_count += 1
            logger.error(f"Error processing Base64 frame: {e}")
            return False

    def submit_frame_bytes(self, frame_bytes: bytes) -> bool:
        """
        Submit a frame as raw JPEG bytes.

        Args:
            frame_bytes: Raw JPEG bytes

        Returns:
            True if frame accepted, False if rejected
        """
        try:
            with self._lock:
                if not self._is_open:
                    return False

            # Decode JPEG to numpy array
            frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)

            if frame is None:
                with self._lock:
                    self._error_count += 1
                logger.warning("Failed to decode frame from bytes")
                return False

            # Add to queue
            try:
                self._queue.put_nowait(frame)
                with self._lock:
                    self._frame_count += 1
                    self._last_frame_time = time.time()
                return True
            except queue.Full:
                # Drop oldest frame
                try:
                    self._queue.get_nowait()
                    self._queue.put_nowait(frame)
                    with self._lock:
                        self._frame_count += 1
                        self._last_frame_time = time.time()
                    logger.debug("Dropped oldest frame to make room")
                    return True
                except queue.Empty:
                    return False

        except Exception as e:
            with self._lock:
                self._error_count += 1
            logger.error(f"Error processing frame bytes: {e}")
            return False

    def get_frame(self, timeout: Optional[float] = None) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Get next frame from queue.

        Args:
            timeout: Seconds to wait. Uses default if None.

        Returns:
            Tuple of (success, frame_array) where frame_array is None if no frame
        """
        with self._lock:
            if not self._is_open:
                return False, None

        timeout_val = timeout if timeout is not None else self._frame_timeout

        try:
            frame = self._queue.get(timeout=timeout_val)
            return True, frame
        except queue.Empty:
            logger.debug("No frames in queue (timeout)")
            return False, None

    def get_stats(self) -> dict:
        """Get receiver statistics."""
        with self._lock:
            return {
                "is_open": self._is_open,
                "frames_received": self._frame_count,
                "errors": self._error_count,
                "queue_size": self._queue.qsize(),
                "last_frame_age": (
                    time.time() - self._last_frame_time if self._last_frame_time > 0 else None
                ),
            }


class BrowserCameraAdapter:
    """
    Adapter to make BrowserCameraReceiver compatible with VideoSource interface.
    """

    def __init__(self, receiver: BrowserCameraReceiver):
        self._receiver = receiver

    def open(self) -> bool:
        """Open the camera source."""
        return self._receiver.open()

    def close(self) -> bool:
        """Close the camera source."""
        return self._receiver.close()

    def is_open(self) -> bool:
        """Check if source is open."""
        return self._receiver.is_open()

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read next frame from browser receiver.

        Returns:
            Tuple of (success, frame)
        """
        return self._receiver.get_frame()


# Global receiver instance (singleton)
_global_receiver: Optional[BrowserCameraReceiver] = None
_global_receiver_lock = threading.Lock()


def get_global_receiver() -> BrowserCameraReceiver:
    """Get or create the global browser camera receiver."""
    global _global_receiver

    if _global_receiver is None:
        with _global_receiver_lock:
            if _global_receiver is None:
                _global_receiver = BrowserCameraReceiver()

    return _global_receiver


def reset_global_receiver() -> None:
    """Reset the global receiver (for testing)."""
    global _global_receiver

    with _global_receiver_lock:
        if _global_receiver is not None:
            _global_receiver.close()
        _global_receiver = None
