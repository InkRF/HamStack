"""Offline tests for the SSTV booth (no camera, pedal, radio, or ALSA needed).

Run from roles/digital/sstv_booth/files:  python -m unittest discover -s tests
Requires Pillow and PySSTV; fastapi is not needed.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
import time
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image  # noqa: E402

from sstv_booth import tx  # noqa: E402
from sstv_booth.camera import MockCamera  # noqa: E402
from sstv_booth.config import Config, load_config  # noqa: E402
from sstv_booth.machine import COUNTDOWN, REVIEW, STANDBY, Booth, TxGuard  # noqa: E402


def quiet(_message: str) -> None:
    pass


class FakeTransmitter:
    def __init__(self):
        self.calls = 0
        self.aborted = False

    def transmit(self, wav_path, duration, on_progress):
        self.calls += 1
        assert wav_path.exists()
        on_progress(0.5)
        on_progress(1.0)

    def abort(self):
        self.aborted = True


class TxGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "tx_log.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_cooldown_blocks_until_elapsed(self):
        guard = TxGuard(self.path, cooldown_s=60, max_per_hour=20)
        guard.record_start(1000.0)
        guard.record_end(1040.0)
        self.assertIn("Cooling down", guard.block_reason(1050.0))
        self.assertIsNone(guard.block_reason(1101.0))

    def test_hourly_cap_is_sliding_and_persisted(self):
        guard = TxGuard(self.path, cooldown_s=0, max_per_hour=2)
        guard.record_start(0.0)
        guard.record_start(100.0)
        self.assertIn("Hourly limit", guard.block_reason(200.0))
        reloaded = TxGuard(self.path, cooldown_s=0, max_per_hour=2)
        self.assertIn("Hourly limit", reloaded.block_reason(200.0))
        self.assertIsNone(reloaded.block_reason(3601.0))


class TxAudioTests(unittest.TestCase):
    def test_image_and_wav_with_cw_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            image = tmp / "out.jpg"
            tx.make_sstv_image(Image.new("RGB", (1280, 720), "blue"), image, "Robot36", "N0CALL", "HELLO")
            with Image.open(image) as result:
                self.assertEqual(result.size, (320, 240))

            config = Config(cw_wpm=20)
            duration = tx.build_tx_wav(config, image, tmp / "tx.wav")
            self.assertGreater(duration, 36.0)  # Robot36 body plus the CW ID
            with wave.open(str(tmp / "tx.wav"), "rb") as wav:
                self.assertEqual(wav.getframerate(), 48000)
                self.assertEqual(wav.getnchannels(), 1)
            self.assertFalse((tmp / "tx.raw.wav").exists())

    def test_rejects_non_morse_callsign(self):
        with self.assertRaises(ValueError):
            tx.generate_cw_pcm("N0CALL!", 8000, 20, 700.0)

    def test_dry_run_never_opens_ptt(self):
        config = Config(tx_enabled=False)
        progress = []
        tx.Transmitter(config, quiet).transmit(Path("missing.wav"), 0.3, progress.append)
        self.assertEqual(progress[-1], 1.0)


class BoothFlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.config = Config(
            data_dir=str(base / "data"),
            rx_dir=str(base / "rx"),
            countdown_s=1,
            review_s=0.3,
            tx_cooldown_s=60,
            dev=True,
        )
        self.config.rx_path.mkdir(parents=True)
        self.transmitter = FakeTransmitter()
        self.booth = Booth(self.config, MockCamera(self.config, quiet), self.transmitter)
        self.booth.loop = asyncio.get_running_loop()

    async def asyncTearDown(self):
        self.tmp.cleanup()

    async def wait_for_mode(self, mode, timeout=60.0):
        deadline = time.monotonic() + timeout
        while self.booth.mode != mode:
            if time.monotonic() > deadline:
                self.fail(f"timed out waiting for {mode}, still {self.booth.mode}")
            await asyncio.sleep(0.05)

    async def test_selfie_transmits_then_cools_down(self):
        self.booth.pedal()
        await self.wait_for_mode(COUNTDOWN)
        self.booth.pedal()  # ignored during countdown
        await self.wait_for_mode(REVIEW)
        await self.booth._selfie_task
        self.assertEqual(self.booth.mode, STANDBY)
        self.assertEqual(self.transmitter.calls, 1)
        self.assertEqual(self.booth.gallery.items(8)[0]["kind"], "tx")
        self.assertEqual(list(self.config.work_path.glob("*.wav")), [])

        self.booth.pedal()
        self.assertEqual(self.booth.mode, STANDBY)
        self.assertIn("Cooling down", self.booth.toast)

    async def test_pedal_cancels_review(self):
        self.booth.pedal()
        await self.wait_for_mode(REVIEW)
        self.booth.pedal()
        await self.booth._selfie_task
        self.assertEqual(self.transmitter.calls, 0)
        self.assertIn("Cancelled", self.booth.toast)

    async def test_rx_events_update_gallery_and_block_tx(self):
        rx = self.config.rx_path
        Image.new("RGB", (320, 240), "red").save(rx / "inprogress.png")
        (rx / "inprogress.ndjson").write_text('{"type":"VIS_DETECT","desc":"Robot 36"}\n')
        await self.booth.rx_event("VIS_DETECT", "inprogress.png")
        self.assertTrue(self.booth.receiving)
        self.assertEqual(self.booth.rx_mode, "Robot 36")
        self.assertIsNotNone(self.booth.inprogress_png)

        self.booth.pedal()
        self.assertEqual(self.booth.mode, STANDBY)
        self.assertIn("Receiving", self.booth.toast)

        final = rx / "2026-10-27T15-00Z-R36.png"
        Image.new("RGB", (320, 240), "green").save(final)
        (rx / "latest.png").write_bytes(final.read_bytes())
        await self.booth.rx_event("RECEIVE_END", final.name)
        self.assertFalse(self.booth.receiving)
        self.assertEqual(self.booth.gallery.latest("rx")["kind"], "rx")

    async def test_rx_ignored_during_own_tx_tail(self):
        self.booth.tx_ended_at = time.time()
        result = await self.booth.rx_event("VIS_DETECT", "inprogress.png")
        self.assertFalse(result["accepted"])
        self.assertFalse(self.booth.receiving)


class ConfigTests(unittest.TestCase):
    def test_unknown_keys_rejected(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            handle.write('{"callsign": "N0CALL", "bogus": 1}')
        try:
            with self.assertRaises(ValueError):
                load_config(handle.name)
        finally:
            Path(handle.name).unlink()

    def test_camera_rotation_limited_to_0_or_180(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            handle.write('{"camera_rotation": 90}')
        try:
            with self.assertRaises(ValueError):
                load_config(handle.name)
        finally:
            Path(handle.name).unlink()


if __name__ == "__main__":
    unittest.main()
