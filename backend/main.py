import logging
from pathlib import Path

import cv2
import numpy as np
import uvicorn
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.services.monitoring_service import MonitoringService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

BASE_DIR = Path(__file__).resolve().parent


def create_app() -> FastAPI:
    app = FastAPI(title="Driver Safety Monitoring System", version="1.0.0")
    app.state.monitoring_service = MonitoringService()
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
    templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    @app.post("/start")
    def start(request: Request):
        request.app.state.monitoring_service.start()
        return JSONResponse({"status": "started"})

    @app.post("/stop")
    def stop(request: Request):
        request.app.state.monitoring_service.stop()
        return JSONResponse({"status": "stopped"})

    @app.post("/process-frame")
    async def process_frame(request: Request, image: UploadFile = File(...)):
        frame_bytes = await image.read()
        if not frame_bytes:
            return JSONResponse({"detail": "Empty image payload"}, status_code=400)

        np_buffer = np.frombuffer(frame_bytes, dtype=np.uint8)
        frame = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)
        if frame is None:
            return JSONResponse({"detail": "Invalid image payload"}, status_code=400)

        result = request.app.state.monitoring_service.process_frame(frame)
        return JSONResponse(result)

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
