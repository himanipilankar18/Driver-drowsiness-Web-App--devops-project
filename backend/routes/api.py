from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse


router = APIRouter()


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
