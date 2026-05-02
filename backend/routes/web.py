from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


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
