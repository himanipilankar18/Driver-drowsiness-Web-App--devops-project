"""Video source abstraction layer."""

from backend.sources.video_source import (
    LocalCameraSource,
    MockSource,
    RTSPStreamSource,
    VideoFileSource,
    VideoSource,
    get_video_source,
)
from backend.sources.browser_camera import (
    BrowserCameraReceiver,
    BrowserCameraAdapter,
    get_global_receiver,
    reset_global_receiver,
)

__all__ = [
    "VideoSource",
    "LocalCameraSource",
    "VideoFileSource",
    "RTSPStreamSource",
    "MockSource",
    "get_video_source",
    "BrowserCameraReceiver",
    "BrowserCameraAdapter",
    "get_global_receiver",
    "reset_global_receiver",
]
