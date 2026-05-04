"""
WebSocket handlers for real-time browser camera frame streaming.

Provides WebSocket endpoint for continuous frame capture from browser,
enabling low-latency processing on cloud servers.
"""

import asyncio
import base64
import io
import json
import logging
from typing import Optional

import cv2
import numpy as np
from fastapi import WebSocket, WebSocketDisconnect
from PIL import Image

logger = logging.getLogger(__name__)


class BrowserCameraWebSocketHandler:
    """
    Handles WebSocket connections for browser camera frame streaming.
    """

    def __init__(self, websocket: WebSocket):
        """
        Initialize WebSocket handler.

        Args:
            websocket: FastAPI WebSocket connection
        """
        self.websocket = websocket
        self.connected = False
        self.frame_count = 0
        self.error_count = 0

    async def connect(self) -> bool:
        """Accept WebSocket connection."""
        try:
            await self.websocket.accept()
            self.connected = True
            logger.info("Browser camera WebSocket connected")
            return True
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            return False

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        self.connected = False
        try:
            await self.websocket.close()
        except Exception:
            pass
        logger.info(
            f"Browser camera WebSocket disconnected. "
            f"Frames: {self.frame_count}, Errors: {self.error_count}"
        )

    async def send_message(self, data: dict) -> bool:
        """
        Send JSON message to client.

        Args:
            data: Dictionary to send as JSON

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.connected:
                await self.websocket.send_json(data)
            return True
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            return False

    async def receive_frame(self) -> Optional[np.ndarray]:
        """
        Receive and decode frame from WebSocket.

        Expects JSON message with structure:
        {
            "type": "frame",
            "data": "base64_encoded_jpeg"
        }

        Returns:
            Decoded OpenCV frame or None if error
        """
        try:
            data = await self.websocket.receive_json()

            if data.get("type") != "frame":
                logger.warning(f"Invalid message type: {data.get('type')}")
                return None

            frame_data = data.get("data")
            if not frame_data:
                logger.warning("No frame data in message")
                return None

            # Decode Base64 JPEG
            frame_bytes = base64.b64decode(frame_data.encode())
            frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)

            if frame is None:
                self.error_count += 1
                logger.warning("Failed to decode frame from WebSocket")
                return None

            self.frame_count += 1
            return frame

        except json.JSONDecodeError:
            self.error_count += 1
            logger.error("Invalid JSON in WebSocket message")
            return None
        except Exception as e:
            self.error_count += 1
            logger.error(f"Error receiving WebSocket frame: {e}")
            return None

    async def handle_stream(self, on_frame_callback) -> None:
        """
        Main WebSocket event loop.

        Continuously receives frames and calls callback.

        Args:
            on_frame_callback: Async function to call with each frame
        """
        try:
            while self.connected:
                frame = await self.receive_frame()

                if frame is None:
                    continue

                # Call callback with frame
                try:
                    await on_frame_callback(frame)
                except Exception as e:
                    logger.error(f"Error in frame callback: {e}")
                    self.error_count += 1

        except WebSocketDisconnect:
            logger.info("Client disconnected from browser camera WebSocket")
            self.connected = False
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            self.connected = False
        finally:
            await self.disconnect()


async def handle_browser_camera_websocket(
    websocket: WebSocket,
    receiver,  # BrowserCameraReceiver instance
) -> None:
    """
    Handle browser camera WebSocket connection.

    Args:
        websocket: FastAPI WebSocket connection
        receiver: BrowserCameraReceiver instance to submit frames to
    """
    handler = BrowserCameraWebSocketHandler(websocket)

    # Accept connection
    if not await handler.connect():
        return

    async def on_frame(frame: np.ndarray) -> None:
        """Process received frame."""
        # Submit frame to receiver (blocking call in thread-safe manner)
        success = receiver.submit_frame_bytes(
            cv2.imencode(".jpg", frame)[1].tobytes()
        )

        # Send status response
        response = {
            "type": "status",
            "frame_received": success,
            "frame_count": receiver.get_stats()["frames_received"],
        }
        await handler.send_message(response)

    # Start handling frames
    await handler.handle_stream(on_frame)
