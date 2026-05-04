import os
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse

import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Temporary upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.get("/status")
def status(request: Request):
    service = request.app.state.monitoring_service
    return JSONResponse(service.status())


@router.post("/start")
def start(request: Request):
    service = request.app.state.monitoring_service
    started = service.start()
    status_code = 200 if started else 503
    return JSONResponse(service.status(), status_code=status_code)


@router.post("/stop")
def stop(request: Request):
    service = request.app.state.monitoring_service
    service.stop()
    return JSONResponse(service.status())


@router.get("/video/stream")
def video_stream(request: Request):
    service = request.app.state.monitoring_service
    return StreamingResponse(
        service.video_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.post("/configure/file")
async def configure_file_mode(request: Request, file: UploadFile = File(...)):
    """
    Upload video file for processing in cloud mode.
    Stops current monitoring, saves file, and prepares for processing.
    """
    try:
        service = request.app.state.monitoring_service
        
        # Stop current monitoring
        if service.is_running():
            service.stop()
        
        # Save uploaded file
        file_path = UPLOAD_DIR / file.filename
        contents = await file.read()
        
        with open(file_path, "wb") as f:
            f.write(contents)
        
        logger.info(f"Video file uploaded: {file_path}")
        
        # Update config for file mode
        os.environ["CAMERA_MODE"] = "file"
        os.environ["VIDEO_FILE_PATH"] = str(file_path)
        
        # Reload config
        from config import SystemConfig
        import importlib
        import config as config_module
        importlib.reload(config_module)
        from config import CONFIG
        
        return JSONResponse({
            "status": "success",
            "message": f"File uploaded: {file.filename}",
            "file_path": str(file_path),
            "camera_mode": "file",
        })
    except Exception as e:
        logger.error(f"File upload error: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=400,
        )


@router.post("/configure/stream")
def configure_stream_mode(request: Request, stream_url: str = Form(...)):
    """
    Configure RTSP/stream source for processing.
    Stops current monitoring and configures stream mode.
    """
    try:
        service = request.app.state.monitoring_service
        
        # Stop current monitoring
        if service.is_running():
            service.stop()
        
        # Validate stream URL format
        if not (stream_url.startswith("rtsp://") or stream_url.startswith("http")):
            return JSONResponse(
                {"status": "error", "message": "Invalid stream URL (must be RTSP or HTTP)"},
                status_code=400,
            )
        
        logger.info(f"Stream configured: {stream_url}")
        
        # Update config for stream mode
        os.environ["CAMERA_MODE"] = "rtsp"
        os.environ["STREAM_URL"] = stream_url
        
        # Reload config
        import importlib
        import config as config_module
        importlib.reload(config_module)
        
        return JSONResponse({
            "status": "success",
            "message": f"Stream configured",
            "stream_url": stream_url,
            "camera_mode": "rtsp",
        })
    except Exception as e:
        logger.error(f"Stream configuration error: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=400,
        )


@router.post("/configure/local")
def configure_local_mode(request: Request):
    """
    Configure local camera mode.
    Stops current monitoring and switches to local camera.
    """
    try:
        service = request.app.state.monitoring_service
        
        # Stop current monitoring
        if service.is_running():
            service.stop()
        
        logger.info("Switched to local camera mode")
        
        # Update config for local mode
        os.environ["CAMERA_MODE"] = "local"
        
        # Reload config
        import importlib
        import config as config_module
        importlib.reload(config_module)
        
        return JSONResponse({
            "status": "success",
            "message": "Switched to local camera mode",
            "camera_mode": "local",
        })
    except Exception as e:
        logger.error(f"Mode configuration error: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=400,
        )


@router.post("/configure/mock")
def configure_mock_mode(request: Request):
    """
    Configure mock/demo mode.
    Stops current monitoring and switches to mock mode.
    """
    try:
        service = request.app.state.monitoring_service
        
        # Stop current monitoring
        if service.is_running():
            service.stop()
        
        logger.info("Switched to mock mode")
        
        # Update config for mock mode
        os.environ["CAMERA_MODE"] = "mock"
        
        # Reload config
        import importlib
        import config as config_module
        importlib.reload(config_module)
        
        return JSONResponse({
            "status": "success",
            "message": "Switched to mock mode",
            "camera_mode": "mock",
        })
    except Exception as e:
        logger.error(f"Mode configuration error: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=400,
        )


@router.get("/modes")
def get_available_modes(request: Request):
    """Get list of available camera modes."""
    from config import CONFIG
    
    return JSONResponse({
        "available_modes": ["local", "file", "rtsp", "browser", "mock"],
        "current_mode": CONFIG.camera_mode,
        "modes_description": {
            "local": "Local webcam via cv2.VideoCapture",
            "file": "Video file upload and playback",
            "rtsp": "RTSP or HTTP stream from IP camera",
            "browser": "Browser-based webcam via getUserMedia",
            "mock": "Mock/demo mode with simulated frames",
        },
    })


@router.post("/configure/browser")
def configure_browser_mode(request: Request):
    """
    Configure browser-based camera mode.
    Stops current monitoring and switches to browser camera.
    
    Usage:
    - Start monitoring in browser mode
    - Send frames via /frame/upload endpoint
    """
    try:
        service = request.app.state.monitoring_service
        
        # Stop current monitoring
        if service.is_running():
            service.stop()
        
        logger.info("Switched to browser camera mode")
        
        # Update config for browser mode
        os.environ["CAMERA_MODE"] = "browser"
        
        # Reload config
        import importlib
        import config as config_module
        importlib.reload(config_module)
        
        # Reset and open the global receiver
        from backend.sources import get_global_receiver
        receiver = get_global_receiver()
        receiver.open()
        
        return JSONResponse({
            "status": "success",
            "message": "Switched to browser camera mode. Start sending frames via /frame/upload",
            "camera_mode": "browser",
        })
    except Exception as e:
        logger.error(f"Browser mode configuration error: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=400,
        )


@router.post("/frame/upload")
async def upload_frame(request: Request, image: UploadFile = File(...)):
    """
    Upload a video frame from browser camera.
    
    Accepts JPEG image file.
    Returns analysis results: fatigue_score, distraction_score, face_detected, state
    
    Usage:
    - POST image file as multipart form
    - Response contains current monitoring status
    """
    try:
        from backend.sources import get_global_receiver
        
        receiver = get_global_receiver()
        
        if not receiver.is_open():
            return JSONResponse(
                {"status": "error", "message": "Browser receiver not active"},
                status_code=400,
            )
        
        # Read image file
        frame_bytes = await image.read()
        
        if len(frame_bytes) == 0:
            return JSONResponse(
                {"status": "error", "message": "Empty frame"},
                status_code=400,
            )
        
        # Limit frame size (10MB max)
        if len(frame_bytes) > 10 * 1024 * 1024:
            return JSONResponse(
                {"status": "error", "message": "Frame too large (max 10MB)"},
                status_code=413,
            )
        
        # Submit frame to receiver
        success = receiver.submit_frame_bytes(frame_bytes)
        
        if not success:
            return JSONResponse(
                {"status": "error", "message": "Failed to process frame"},
                status_code=400,
            )
        
        # Get current monitoring status
        service = request.app.state.monitoring_service
        status_data = service.status()
        
        return JSONResponse({
            "status": "success",
            "message": "Frame received",
            "frame_count": receiver.get_stats()["frames_received"],
            "analysis": {
                "state": status_data.get("state"),
                "fatigue_score": status_data.get("fatigue_score"),
                "distraction_score": status_data.get("distraction_score"),
                "face_detected": status_data.get("face_detected"),
                "monitoring": status_data.get("monitoring"),
            },
        })
    except Exception as e:
        logger.error(f"Frame upload error: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=400,
        )


@router.post("/frame/base64")
async def upload_frame_base64(request: Request):
    """
    Upload a video frame from browser camera as Base64.
    
    POST JSON body:
    {
        "frame": "base64_encoded_jpeg_data"
    }
    
    Returns analysis results: fatigue_score, distraction_score, face_detected, state
    """
    try:
        from backend.sources import get_global_receiver
        import json
        
        receiver = get_global_receiver()
        
        if not receiver.is_open():
            return JSONResponse(
                {"status": "error", "message": "Browser receiver not active"},
                status_code=400,
            )
        
        # Parse request body
        body = await request.json()
        frame_base64 = body.get("frame")
        
        if not frame_base64:
            return JSONResponse(
                {"status": "error", "message": "No frame data provided"},
                status_code=400,
            )
        
        # Check size limit (Base64 string max 15MB)
        if len(frame_base64) > 15 * 1024 * 1024:
            return JSONResponse(
                {"status": "error", "message": "Frame too large"},
                status_code=413,
            )
        
        # Submit frame to receiver
        success = receiver.submit_frame_base64(frame_base64)
        
        if not success:
            return JSONResponse(
                {"status": "error", "message": "Failed to process frame"},
                status_code=400,
            )
        
        # Get current monitoring status
        service = request.app.state.monitoring_service
        status_data = service.status()
        
        return JSONResponse({
            "status": "success",
            "message": "Frame received",
            "frame_count": receiver.get_stats()["frames_received"],
            "analysis": {
                "state": status_data.get("state"),
                "fatigue_score": status_data.get("fatigue_score"),
                "distraction_score": status_data.get("distraction_score"),
                "face_detected": status_data.get("face_detected"),
                "monitoring": status_data.get("monitoring"),
            },
        })
    except Exception as e:
        logger.error(f"Frame upload error: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=400,
        )


@router.get("/frame/stats")
def get_frame_stats(request: Request):
    """Get statistics about browser camera frame reception."""
    try:
        from backend.sources import get_global_receiver
        
        receiver = get_global_receiver()
        stats = receiver.get_stats()
        
        return JSONResponse({
            "status": "success",
            "frame_stats": stats,
        })
    except Exception as e:
        logger.error(f"Error getting frame stats: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=400,
        )
