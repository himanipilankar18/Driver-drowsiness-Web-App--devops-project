from pathlib import Path

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from backend.routes.websocket import handle_browser_camera_websocket
from backend.sources import get_global_receiver


router = APIRouter()
TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    service = request.app.state.monitoring_service
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "status": service.status(),
        },
    )


@router.get("/video", response_class=HTMLResponse)
def video_page(request: Request):
    service = request.app.state.monitoring_service
    return templates.TemplateResponse(
        "video.html",
        {
            "request": request,
            "status": service.status(),
        },
    )


@router.websocket("/ws/camera")
async def websocket_browser_camera(websocket: WebSocket):
    """
    WebSocket endpoint for real-time browser camera frame streaming.
    
    Client sends JSON messages:
    {
        "type": "frame",
        "data": "base64_encoded_jpeg"
    }
    
    Server responds with:
    {
        "type": "status",
        "frame_received": true/false,
        "frame_count": 123
    }
    """
    receiver = get_global_receiver()
    await handle_browser_camera_websocket(websocket, receiver)
