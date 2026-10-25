"""Camera sources: Picamera2 (Camera Module 3) and a development mock."""

from __future__ import annotations

import io
import math
import threading
import time
from datetime import datetime

from PIL import Image, ImageDraw


class FrameBuffer(io.BufferedIOBase):
    """Latest MJPEG preview frame plus a sequence number for streaming clients."""

    def __init__(self) -> None:
        self.frame: bytes | None = None
        self.seq = 0
        self._lock = threading.Lock()

    def write(self, buf) -> int:
        with self._lock:
            self.frame = bytes(buf)
            self.seq += 1
        return len(buf)

    def get(self) -> tuple[int, bytes | None]:
        with self._lock:
            return self.seq, self.frame


class PiCamera:
    def __init__(self, config, log):
        self.config = config
        self.log = log
        self.frames = FrameBuffer()
        self._camera = None

    def start(self) -> None:
        from picamera2 import Picamera2
        from picamera2.encoders import MJPEGEncoder
        from picamera2.outputs import FileOutput

        camera = Picamera2()
        configuration = camera.create_video_configuration(
            main={"size": (self.config.camera_width, self.config.camera_height), "format": "RGB888"},
            lores={"size": (self.config.preview_width, self.config.preview_height)},
        )
        camera.configure(configuration)
        try:
            from libcamera import controls

            camera.set_controls({"AfMode": controls.AfModeEnum.Continuous})
        except Exception as exc:  # cameras without autofocus reject AfMode
            self.log(f"Continuous autofocus unavailable: {exc}")
        camera.start_recording(MJPEGEncoder(), FileOutput(self.frames), name="lores")
        self._camera = camera
        self.log("Camera started")

    def capture(self) -> Image.Image:
        if self._camera is None:
            raise RuntimeError("Camera is not started")
        return self._camera.capture_image("main").convert("RGB")

    def stop(self) -> None:
        if self._camera is not None:
            try:
                self._camera.stop_recording()
            except Exception:
                pass
            self._camera = None


class MockCamera:
    """Synthetic moving test pattern for --dev runs without camera hardware."""

    def __init__(self, config, log, fps: float = 10.0):
        self.config = config
        self.log = log
        self.frames = FrameBuffer()
        self._fps = fps
        self._running = False
        self._thread: threading.Thread | None = None

    def _render(self, size) -> Image.Image:
        width, height = size
        t = time.monotonic()
        image = Image.new("RGB", size)
        draw = ImageDraw.Draw(image)
        for x in range(0, width, 8):
            shade = int(127 + 127 * math.sin(x / width * 6.28 + t))
            draw.rectangle((x, 0, x + 8, height), fill=(shade // 3, shade // 2, shade))
        cx = width / 2 + width / 3 * math.sin(t)
        radius = height / 6
        draw.ellipse((cx - radius, height / 2 - radius, cx + radius, height / 2 + radius), fill=(255, 200, 0))
        draw.text((10, 10), f"MOCK CAMERA {datetime.now():%H:%M:%S}", fill=(255, 255, 255))
        return image

    def _loop(self) -> None:
        size = (self.config.preview_width, self.config.preview_height)
        while self._running:
            buffer = io.BytesIO()
            self._render(size).save(buffer, "JPEG", quality=70)
            self.frames.write(buffer.getvalue())
            time.sleep(1.0 / self._fps)

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="mock-camera", daemon=True)
        self._thread.start()
        self.log("Mock camera started")

    def capture(self) -> Image.Image:
        return self._render((self.config.camera_width, self.config.camera_height))

    def stop(self) -> None:
        self._running = False
