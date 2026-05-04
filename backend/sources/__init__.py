"""Video source abstraction layer."""

from backend.sources.video_source import (
    LocalCameraSource,
    MockSource,
    RTSPStreamSource,
    VideoFileSource,
    VideoSource,
    get_video_source,
)

__all__ = [
    "VideoSource",
    "LocalCameraSource",
    "VideoFileSource",
    "RTSPStreamSource",
    "MockSource",
    "get_video_source",
]
