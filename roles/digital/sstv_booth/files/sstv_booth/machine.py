"""Booth state machine: STANDBY / COUNTDOWN / REVIEW / TX plus RX tracking."""

from __future__ import annotations

import asyncio
import io
import json
import random
import time
from datetime import datetime
from pathlib import Path

from PIL import Image

from . import tx
from .gallery import Gallery

STANDBY = "standby"
COUNTDOWN = "countdown"
REVIEW = "review"
TX = "tx"

RX_EVENTS = ("VIS_DETECT", "IMAGE_REFRESHED", "RECEIVE_END")
RX_POLL_SECONDS = 1.0
TOAST_SECONDS = 4.0


def log(message: str) -> None:
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {message}", flush=True)


class TxGuard:
    """Cooldown and hourly-cap bookkeeping, persisted across restarts."""

    def __init__(self, path: Path, cooldown_s: float, max_per_hour: int):
        self.path = path
        self.cooldown_s = cooldown_s
        self.max_per_hour = max_per_hour
        self.history: list[float] = []
        self.last_end = 0.0
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.history = [float(t) for t in data.get("history", [])]
            self.last_end = float(data.get("last_end", 0.0))
        except (OSError, ValueError):
            pass

    def _recent(self, now: float) -> list[float]:
        return [t for t in self.history if now - t < 3600]

    def cooldown_until(self) -> float:
        return self.last_end + self.cooldown_s if self.last_end else 0.0

    def count_last_hour(self, now: float | None = None) -> int:
        return len(self._recent(time.time() if now is None else now))

    def block_reason(self, now: float | None = None) -> str | None:
        now = time.time() if now is None else now
        remaining = self.cooldown_until() - now
        if remaining > 0:
            return f"Cooling down - ready in {int(remaining + 0.999)} s"
        recent = self._recent(now)
        if len(recent) >= self.max_per_hour:
            wait = 3600 - (now - min(recent))
            return f"Hourly limit reached - ready in {int(wait / 60) + 1} min"
        return None

    def record_start(self, now: float | None = None) -> None:
        now = time.time() if now is None else now
        self.history = self._recent(now) + [now]
        self._save()

    def record_end(self, now: float | None = None) -> None:
        self.last_end = time.time() if now is None else now
        self._save()

    def _save(self) -> None:
        try:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"history": self.history, "last_end": self.last_end}), encoding="utf-8")
            tmp.replace(self.path)
        except OSError as exc:
            log(f"Could not save TX log: {exc}")


class Booth:
    def __init__(self, config, camera, transmitter: tx.Transmitter):
        self.config = config
        self.camera = camera
        self.transmitter = transmitter
        config.work_path.mkdir(parents=True, exist_ok=True)
        self.gallery = Gallery(config.gallery_path, config.gallery_keep)
        self.guard = TxGuard(config.data_path / "tx_log.json", config.tx_cooldown_s, config.max_tx_per_hour)

        self.loop: asyncio.AbstractEventLoop | None = None
        self.subscribers: set[asyncio.Queue] = set()

        self.mode = STANDBY
        self.countdown = 0
        self.review_url: str | None = None
        self.tx_progress = 0.0
        self.tx_duration = 0.0
        self.tx_active = False
        self.tx_ended_at = 0.0
        self.toast: str | None = None
        self.toast_until = 0.0

        self.receiving = False
        self.rx_mode: str | None = None
        self.rx_version = 0
        self.rx_last_activity = 0.0
        self.inprogress_png: bytes | None = None
        self._inprogress_mtime = 0.0
        self._rx_task: asyncio.Task | None = None

        self._selfie_task: asyncio.Task | None = None
        self._review_cancel = asyncio.Event()
        self._review_image: Path | None = None

    # ------------------------------------------------------------------ state

    def snapshot(self) -> dict:
        now = time.time()
        latest_rx = self.gallery.latest("rx")
        return {
            "mode": self.mode,
            "callsign": self.config.callsign,
            "sstv_mode": self.config.sstv_mode,
            "tx_enabled": self.config.tx_enabled,
            "dev": self.config.dev,
            "countdown": self.countdown,
            "review_url": self.review_url,
            "tx_progress": round(self.tx_progress, 3),
            "tx_duration": round(self.tx_duration, 1),
            "receiving": self.receiving,
            "rx_mode": self.rx_mode,
            "rx_version": self.rx_version,
            "latest_rx": latest_rx,
            "gallery": self.gallery.items(self.config.gallery_strip),
            "cooldown_until": self.guard.cooldown_until(),
            "tx_last_hour": self.guard.count_last_hour(now),
            "max_tx_per_hour": self.config.max_tx_per_hour,
            "toast": self.toast if now < self.toast_until else None,
            "server_time": now,
        }

    def publish(self) -> None:
        state = self.snapshot()
        for queue in list(self.subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(state)

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=4)
        self.subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self.subscribers.discard(queue)

    def say(self, message: str) -> None:
        log(message)
        self.toast = message
        self.toast_until = time.time() + TOAST_SECONDS
        self.publish()

    # ------------------------------------------------------------- guardrails

    def tx_block_reason(self) -> str | None:
        if self.receiving:
            return "Receiving an image - wait for it to finish"
        return self.guard.block_reason()

    def rx_ignored(self) -> bool:
        if self.tx_active:
            return True
        return time.time() < self.tx_ended_at + self.config.rx_ignore_tail_s

    # ------------------------------------------------------------------ pedal

    def pedal_threadsafe(self) -> None:
        if self.loop is not None:
            self.loop.call_soon_threadsafe(self.pedal)

    def pedal(self) -> None:
        if self.mode == STANDBY:
            reason = self.tx_block_reason()
            if reason:
                self.say(reason)
                return
            self._selfie_task = asyncio.ensure_future(self._run_selfie())
        elif self.mode == REVIEW:
            self._review_cancel.set()
        # Presses during COUNTDOWN and TX are ignored.

    def _blurb(self) -> str:
        if self.config.blurb_mode == "fixed":
            return self.config.blurb_text
        if self.config.blurb_mode == "random" and self.config.blurb_list:
            return random.choice(self.config.blurb_list)
        return ""

    async def _run_selfie(self) -> None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        image_path = self.config.work_path / f"selfie-{stamp}.jpg"
        wav_path = self.config.work_path / f"selfie-{stamp}-tx.wav"
        wav_task: asyncio.Future | None = None
        try:
            self.mode = COUNTDOWN
            for remaining in range(int(self.config.countdown_s), 0, -1):
                self.countdown = remaining
                self.publish()
                await asyncio.sleep(1)
            self.countdown = 0

            photo = await asyncio.to_thread(self.camera.capture)
            await asyncio.to_thread(
                tx.make_sstv_image, photo, image_path, self.config.sstv_mode,
                self.config.callsign, self._blurb(),
            )
            self._review_image = image_path

            # Encoding is slow on a Pi; start it while the visitor reviews.
            wav_task = asyncio.ensure_future(asyncio.to_thread(tx.build_tx_wav, self.config, image_path, wav_path))

            self._review_cancel.clear()
            self.mode = REVIEW
            self.review_url = f"/work/review.jpg?v={stamp}"
            self.publish()
            try:
                await asyncio.wait_for(self._review_cancel.wait(), timeout=self.config.review_s)
                self.say("Cancelled - press the pedal to try again")
                return
            except asyncio.TimeoutError:
                pass

            reason = self.tx_block_reason()
            if reason:
                self.say(reason)
                return

            duration = await wav_task
            self.mode = TX
            self.tx_duration = duration
            self.tx_progress = 0.0
            self.tx_active = True
            self.guard.record_start()
            self.publish()
            log(f"{'Transmitting' if self.config.tx_enabled else 'Dry-run TX'} {image_path.name} ({duration:.1f} s)")
            try:
                await asyncio.to_thread(self.transmitter.transmit, wav_path, duration, self._progress_threadsafe)
            finally:
                self.tx_active = False
                self.tx_ended_at = time.time()
                self.guard.record_end(self.tx_ended_at)
            await asyncio.to_thread(self.gallery.add, "tx", image_path, ".jpg")
            self.say("Sent over the air!" if self.config.tx_enabled else "Dry run complete (TX disabled)")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.say(f"Error: {exc}")
        finally:
            if wav_task is not None and not wav_task.done():
                try:
                    await wav_task
                except Exception:
                    pass
            wav_path.unlink(missing_ok=True)
            self.mode = STANDBY
            self.countdown = 0
            self.review_url = None
            self.tx_progress = 0.0
            self.publish()

    def review_image(self) -> Path | None:
        return self._review_image if self.mode in (REVIEW, TX) else None

    def _progress_threadsafe(self, fraction: float) -> None:
        if self.loop is not None:
            self.loop.call_soon_threadsafe(self._set_progress, fraction)

    def _set_progress(self, fraction: float) -> None:
        self.tx_progress = fraction
        self.publish()

    # --------------------------------------------------------------------- rx

    async def rx_event(self, event: str, image: str) -> dict:
        if event not in RX_EVENTS:
            return {"accepted": False, "reason": "unknown event"}
        if self.rx_ignored():
            return {"accepted": False, "reason": "ignored during own TX"}

        self.rx_last_activity = time.monotonic()
        if event in ("VIS_DETECT", "IMAGE_REFRESHED"):
            if not self.receiving:
                self.receiving = True
                self.rx_mode = None
                self.inprogress_png = None
                self._inprogress_mtime = 0.0
                log("RX started")
            if self._rx_task is None or self._rx_task.done():
                self._rx_task = asyncio.ensure_future(self._poll_inprogress())
            await self._refresh_inprogress()
            self.publish()
        else:
            await self._finish_rx(image)
        return {"accepted": True}

    async def _finish_rx(self, image: str) -> None:
        await self._refresh_inprogress()
        self.receiving = False
        source = self.config.rx_path / image if image else None
        if source is None or not source.is_file() or source.suffix != ".png":
            source = self.config.rx_path / "latest.png"
        source = source.resolve()
        if source.is_file() and source.parent == self.config.rx_path.resolve():
            await asyncio.to_thread(self.gallery.add, "rx", source, ".png")
            log(f"RX complete: {source.name}")
        else:
            log("RX ended but no final image was found")
        self.publish()

    async def _refresh_inprogress(self) -> None:
        path = self.config.rx_path / "inprogress.png"
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return
        if mtime == self._inprogress_mtime:
            return
        data = await asyncio.to_thread(_read_valid_png, path)
        if data is None:
            return  # slowrxd is mid-write; keep the last good frame
        self._inprogress_mtime = mtime
        self.inprogress_png = data
        self.rx_version += 1
        self.rx_last_activity = time.monotonic()
        if self.rx_mode is None:
            self.rx_mode = await asyncio.to_thread(_read_vis_mode, self.config.rx_path / "inprogress.ndjson")

    async def _poll_inprogress(self) -> None:
        while self.receiving:
            version = self.rx_version
            await self._refresh_inprogress()
            if self.rx_version != version:
                self.publish()
            if time.monotonic() - self.rx_last_activity > self.config.rx_stale_s:
                self.receiving = False
                log("RX went quiet without RECEIVE_END; returning to standby")
                self.publish()
                break
            await asyncio.sleep(RX_POLL_SECONDS)

    # -------------------------------------------------------------- lifecycle

    def shutdown(self) -> None:
        self.transmitter.abort()
        self.camera.stop()


def _read_valid_png(path: Path) -> bytes | None:
    try:
        data = path.read_bytes()
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        return data
    except Exception:
        return None


def _read_vis_mode(path: Path) -> str | None:
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if record.get("type") == "VIS_DETECT":
                    return record.get("desc") or record.get("mode")
    except OSError:
        pass
    return None
