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
        "available_modes": ["local", "file", "rtsp", "mock"],
        "current_mode": CONFIG.camera_mode,
        "modes_description": {
            "local": "Local webcam via cv2.VideoCapture",
            "file": "Video file upload and playback",
            "rtsp": "RTSP or HTTP stream from IP camera",
            "mock": "Mock/demo mode with simulated frames",
        },
    })
