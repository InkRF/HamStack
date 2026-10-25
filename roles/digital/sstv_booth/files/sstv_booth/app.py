"""FastAPI application: kiosk page, SSE state stream, MJPEG preview, RX hook."""

from __future__ import annotations

import asyncio
import json
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .machine import Booth

STATIC_DIR = Path(__file__).resolve().parent / "static"
IMAGE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{0,128}$")
SSE_HEARTBEAT_SECONDS = 15.0
MJPEG_INTERVAL_SECONDS = 1 / 15
NO_CACHE = {"Cache-Control": "no-store"}


def create_app(booth: Booth, on_startup=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        booth.loop = asyncio.get_running_loop()
        if on_startup is not None:
            on_startup()
        yield
        booth.shutdown()

    app = FastAPI(title="HamStack SSTV booth", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.closing = False
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    async def index():
        return FileResponse(STATIC_DIR / "index.html", headers=NO_CACHE)

    @app.get("/api/state")
    async def state():
        return booth.snapshot()

    @app.get("/api/gallery")
    async def gallery(limit: int = 8):
        return booth.gallery.items(max(1, min(limit, 200)))

    @app.get("/api/events")
    async def events(request: Request):
        queue = booth.subscribe()

        async def stream():
            try:
                yield f"data: {json.dumps(booth.snapshot())}\n\n"
                idle = 0.0
                while not app.state.closing:
                    if await request.is_disconnected():
                        break
                    try:
                        state = await asyncio.wait_for(queue.get(), timeout=1.0)
                    except asyncio.TimeoutError:
                        idle += 1.0
                        if idle >= SSE_HEARTBEAT_SECONDS:
                            idle = 0.0
                            yield ": ping\n\n"
                        continue
                    idle = 0.0
                    yield f"data: {json.dumps(state)}\n\n"
            finally:
                booth.unsubscribe(queue)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/pedal")
    async def pedal():
        booth.pedal()
        return {"mode": booth.mode}

    @app.post("/api/rx-event")
    async def rx_event(request: Request):
        try:
            body = await request.json()
        except ValueError:
            raise HTTPException(status_code=400, detail="expected JSON")
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="expected a JSON object")
        event = str(body.get("event", ""))
        image = str(body.get("image", ""))
        if not IMAGE_NAME_RE.match(image) or image.startswith("."):
            raise HTTPException(status_code=400, detail="invalid image name")
        return JSONResponse(await booth.rx_event(event, image))

    @app.get("/stream.mjpg")
    async def mjpeg(request: Request):
        frames = booth.camera.frames

        async def stream():
            last_seq = -1
            while not app.state.closing:
                if await request.is_disconnected():
                    break
                seq, frame = frames.get()
                if frame is not None and seq != last_seq:
                    last_seq = seq
                    yield (
                        b"--frame\r\nContent-Type: image/jpeg\r\n"
                        + f"Content-Length: {len(frame)}\r\n\r\n".encode()
                        + frame
                        + b"\r\n"
                    )
                await asyncio.sleep(MJPEG_INTERVAL_SECONDS)

        return StreamingResponse(
            stream(),
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers=NO_CACHE,
        )

    @app.get("/rx/inprogress.png")
    async def inprogress():
        if booth.inprogress_png is None:
            raise HTTPException(status_code=404)
        return Response(booth.inprogress_png, media_type="image/png", headers=NO_CACHE)

    @app.get("/gallery/{name}")
    async def gallery_image(name: str):
        path = booth.gallery.path_for(name)
        if path is None:
            raise HTTPException(status_code=404)
        return FileResponse(path)

    @app.get("/work/review.jpg")
    async def review():
        path = booth.review_image()
        if path is None or not path.is_file():
            raise HTTPException(status_code=404)
        return FileResponse(path, headers=NO_CACHE)

    return app
