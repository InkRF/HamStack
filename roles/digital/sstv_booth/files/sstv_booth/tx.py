"""SSTV image/audio generation and AIOC transmit path for the SSTV booth.

The imaging, CW-ID, AIOC PTT and playback helpers are copied from the
HamStack selfie_station role (roles/digital/selfie_station/templates/
selfie_station.py.j2) and parameterised so they read booth configuration
instead of Jinja-rendered constants. Keep behavioural fixes in both places.
"""

from __future__ import annotations

import argparse
import math
import re
import struct
import subprocess
import threading
import time
import wave
from pathlib import Path
from typing import Callable, Final

from PIL import Image, ImageDraw, ImageFont, ImageOps
from pysstv.color import MartinM1, Robot36, ScottieS1

BITS_PER_SAMPLE = 16
CW_AMPLITUDE = 0.30
CW_TO_SSTV_GAP_SECONDS = 0.60

FONT_PATH = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
OVERLAY_MAX_FONT_SIZE = 22
OVERLAY_MIN_FONT_SIZE = 9
OVERLAY_HORIZONTAL_PADDING = 8
OVERLAY_VERTICAL_PADDING = 6
OVERLAY_OPACITY = 175

MODE_CLASSES: Final = {
    "Robot36": Robot36,
    "MartinM1": MartinM1,
    "ScottieS1": ScottieS1,
}

MORSE: Final = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".",
    "F": "..-.", "G": "--.", "H": "....", "I": "..", "J": ".---",
    "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---",
    "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-",
    "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--",
    "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--",
    "4": "....-", "5": ".....", "6": "-....", "7": "--...",
    "8": "---..", "9": "----.", "/": "-..-.",
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def get_mode_class(mode: str):
    try:
        return MODE_CLASSES[mode]
    except KeyError as exc:
        supported = ", ".join(MODE_CLASSES)
        raise ValueError(
            f"Unsupported SSTV mode {mode!r}; choose: {supported}"
        ) from exc


def _font(size: int):
    if FONT_PATH.exists():
        return ImageFont.truetype(str(FONT_PATH), size)
    # Development hosts without DejaVu still get a readable overlay.
    return ImageFont.load_default()


def choose_font(draw: ImageDraw.ImageDraw, text: str, max_width: int):
    for size in range(
        OVERLAY_MAX_FONT_SIZE,
        OVERLAY_MIN_FONT_SIZE - 1,
        -1,
    ):
        font = _font(size)
        box = draw.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= max_width:
            return font

    return _font(OVERLAY_MIN_FONT_SIZE)


def _draw_bar(draw: ImageDraw.ImageDraw, canvas_size, text: str, top: bool) -> None:
    max_text_width = canvas_size[0] - (2 * OVERLAY_HORIZONTAL_PADDING)
    font = choose_font(draw, text, max_text_width)
    text_box = draw.textbbox((0, 0), text, font=font)
    text_width = text_box[2] - text_box[0]
    text_height = text_box[3] - text_box[1]
    bar_height = text_height + (2 * OVERLAY_VERTICAL_PADDING)
    bar_top = 0 if top else canvas_size[1] - bar_height

    draw.rectangle(
        (0, bar_top, canvas_size[0], bar_top + bar_height),
        fill=(0, 0, 0, OVERLAY_OPACITY),
    )

    x = (canvas_size[0] - text_width) // 2
    y = bar_top + OVERLAY_VERTICAL_PADDING - text_box[1]

    # A tiny shadow helps the text survive noisy SSTV reception.
    draw.text((x + 1, y + 1), text, font=font, fill=(0, 0, 0, 255))
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))


def make_sstv_image(
    source: Image.Image,
    destination: Path,
    mode: str,
    callsign: str,
    blurb: str = "",
) -> None:
    """Fit a photo to the SSTV canvas; callsign bar at the bottom, blurb on top."""
    mode_class = get_mode_class(mode)
    canvas_size = (mode_class.WIDTH, mode_class.HEIGHT)

    image = ImageOps.fit(
        source.convert("RGB"),
        canvas_size,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.45),
    ).convert("RGBA")

    overlay = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    _draw_bar(draw, canvas_size, callsign, top=False)
    if blurb:
        _draw_bar(draw, canvas_size, blurb, top=True)

    branded = Image.alpha_composite(image, overlay).convert("RGB")
    branded.save(destination, "JPEG", quality=95, subsampling=0)


def generate_sstv_wav(image_path: Path, wav_path: Path, mode: str, sample_rate: int) -> None:
    mode_class = get_mode_class(mode)

    with Image.open(image_path) as image:
        encoder = mode_class(
            image.convert("RGB"),
            sample_rate,
            BITS_PER_SAMPLE,
        )
        encoder.write_wav(str(wav_path))


def silence_pcm(seconds: float, sample_rate: int) -> bytes:
    frame_count = max(0, round(seconds * sample_rate))
    return b"\x00\x00" * frame_count


def tone_pcm(
    seconds: float,
    sample_rate: int,
    frequency: float,
    amplitude: float,
) -> bytes:
    frame_count = max(0, round(seconds * sample_rate))
    fade_frames = min(round(0.005 * sample_rate), frame_count // 2)
    output = bytearray()

    for index in range(frame_count):
        envelope = 1.0

        if fade_frames:
            if index < fade_frames:
                envelope = index / fade_frames
            elif index >= frame_count - fade_frames:
                envelope = (frame_count - index - 1) / fade_frames

        value = round(
            32767
            * amplitude
            * envelope
            * math.sin(2.0 * math.pi * frequency * index / sample_rate)
        )
        output.extend(struct.pack("<h", value))

    return bytes(output)


def generate_cw_pcm(text: str, sample_rate: int, wpm: int, tone_hz: float) -> bytes:
    dot_seconds = 1.2 / wpm
    output = bytearray()
    words = text.upper().split()

    for word_index, word in enumerate(words):
        for character_index, character in enumerate(word):
            pattern = MORSE.get(character)
            if pattern is None:
                raise ValueError(
                    f"Unsupported Morse character in callsign: {character!r}"
                )

            for element_index, element in enumerate(pattern):
                duration = (
                    dot_seconds if element == "." else 3 * dot_seconds
                )
                output.extend(
                    tone_pcm(
                        duration,
                        sample_rate,
                        tone_hz,
                        CW_AMPLITUDE,
                    )
                )

                if element_index < len(pattern) - 1:
                    output.extend(silence_pcm(dot_seconds, sample_rate))

            if character_index < len(word) - 1:
                output.extend(silence_pcm(3 * dot_seconds, sample_rate))

        if word_index < len(words) - 1:
            output.extend(silence_pcm(7 * dot_seconds, sample_rate))

    return bytes(output)


def prepend_cw_id(
    source_wav: Path,
    destination_wav: Path,
    callsign: str,
    cw_enabled: bool,
    wpm: int,
    tone_hz: float,
) -> None:
    with wave.open(str(source_wav), "rb") as source:
        params = source.getparams()
        sstv_pcm = source.readframes(source.getnframes())

    if params.nchannels != 1:
        fail(f"Expected mono SSTV WAV, got {params.nchannels} channels")
    if params.sampwidth != 2:
        fail(f"Expected 16-bit SSTV WAV, got {params.sampwidth * 8}-bit")
    if params.comptype != "NONE":
        fail(f"Expected uncompressed PCM WAV, got {params.comptype}")

    prefix = bytearray()
    prefix.extend(silence_pcm(0.10, params.framerate))

    if cw_enabled:
        prefix.extend(generate_cw_pcm(callsign, params.framerate, wpm, tone_hz))
        prefix.extend(
            silence_pcm(CW_TO_SSTV_GAP_SECONDS, params.framerate)
        )

    with wave.open(str(destination_wav), "wb") as destination:
        destination.setparams(params)
        destination.writeframes(bytes(prefix) + sstv_pcm)


def build_tx_wav(config, image_path: Path, tx_wav: Path) -> float:
    """Render SSTV audio with the CW ID prefix; return the WAV duration in seconds."""
    raw_wav = tx_wav.with_suffix(".raw.wav")
    try:
        generate_sstv_wav(image_path, raw_wav, config.sstv_mode, config.sample_rate)
        prepend_cw_id(
            raw_wav,
            tx_wav,
            config.callsign,
            config.cw_enabled,
            config.cw_wpm,
            config.cw_tone_hz,
        )
    finally:
        raw_wav.unlink(missing_ok=True)
    return wav_duration(tx_wav)


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav:
        return wav.getnframes() / float(wav.getframerate())


def detect_aioc_serial_device(configured: str) -> str:
    if configured:
        return configured

    from serial.tools import list_ports

    candidates = []

    for port in list_ports.comports():
        description = " ".join(
            filter(
                None,
                (
                    port.device,
                    port.description,
                    port.manufacturer,
                    port.product,
                    port.hwid,
                ),
            )
        ).lower()

        vid_pid_match = port.vid == 0x1209 and port.pid == 0x7388
        name_match = "allinonecable" in description or "aioc" in description

        if vid_pid_match or name_match:
            candidates.append(port.device)

    if not candidates:
        fail(
            "Could not auto-detect the AIOC serial interface. "
            "Set aioc_serial_device in the booth configuration."
        )

    if len(candidates) > 1:
        fail(
            "Multiple possible AIOC serial devices found: "
            f"{', '.join(candidates)}. Set aioc_serial_device explicitly."
        )

    return candidates[0]


def detect_aioc_audio_device(configured: str, match_text: str) -> str:
    if configured:
        return configured

    result = subprocess.run(
        ["aplay", "-l"],
        check=True,
        capture_output=True,
        text=True,
    )

    pattern = re.compile(
        r"^card\s+(\d+):.*?,\s+device\s+(\d+):",
        re.IGNORECASE,
    )
    matches = []

    for line in result.stdout.splitlines():
        if match_text.lower() not in line.lower():
            continue

        match = pattern.search(line)
        if match:
            matches.append(f"plughw:{match.group(1)},{match.group(2)}")

    matches = list(dict.fromkeys(matches))

    if not matches:
        fail(
            f"Could not find an ALSA playback device matching "
            f"{match_text!r}. Run `aplay -l` and set aioc_audio_device."
        )

    if len(matches) > 1:
        fail(
            "Multiple matching AIOC playback devices found: "
            f"{', '.join(matches)}. Set aioc_audio_device explicitly."
        )

    return matches[0]


class AiocPtt:
    def __init__(self, device: str):
        self.device = device
        self.serial_port = None

    def open(self) -> None:
        import serial

        port = serial.Serial()
        port.port = self.device
        port.baudrate = 9600
        port.timeout = 1
        port.write_timeout = 1

        # Establish the inactive state before and immediately after opening.
        port.dtr = False
        port.rts = True
        port.open()
        port.dtr = False
        port.rts = True

        self.serial_port = port

    def key(self) -> None:
        if self.serial_port is None:
            fail("AIOC PTT serial port is not open")

        # The AIOC keys when DTR=1 and RTS=0.
        self.serial_port.rts = False
        self.serial_port.dtr = True

    def unkey(self) -> None:
        if self.serial_port is None:
            return

        # Drop DTR first, then return RTS to its inactive state.
        self.serial_port.dtr = False
        self.serial_port.rts = True

    def close(self) -> None:
        if self.serial_port is None:
            return

        try:
            self.unkey()
        finally:
            self.serial_port.close()
            self.serial_port = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False


class Transmitter:
    """Plays a TX WAV, keying the AIOC only when transmit is enabled.

    With transmit disabled the call waits for the WAV duration so the booth
    flow and progress bar behave exactly like a real transmission.
    """

    def __init__(self, config, log: Callable[[str], None]):
        self.config = config
        self.log = log
        self._lock = threading.Lock()
        self._player: subprocess.Popen | None = None
        self._ptt: AiocPtt | None = None
        self._abort = threading.Event()

    def transmit(
        self,
        wav_path: Path,
        duration: float,
        on_progress: Callable[[float], None],
    ) -> None:
        self._abort.clear()
        if not self.config.tx_enabled:
            self._dry_run(duration, on_progress)
            return

        serial_device = detect_aioc_serial_device(self.config.aioc_serial_device)
        audio_device = detect_aioc_audio_device(
            self.config.aioc_audio_device, self.config.audio_device_match
        )
        self.log(f"AIOC serial PTT: {serial_device}; audio output: {audio_device}")

        total = duration + self.config.ptt_lead_s + self.config.ptt_tail_s
        started = time.monotonic()
        with AiocPtt(serial_device) as ptt:
            with self._lock:
                self._ptt = ptt
            try:
                ptt.key()
                time.sleep(self.config.ptt_lead_s)
                with self._lock:
                    if self._abort.is_set():
                        return
                    player = subprocess.Popen(
                        ["aplay", "-q", "-D", audio_device, str(wav_path)]
                    )
                    self._player = player
                while player.poll() is None:
                    on_progress(min(1.0, (time.monotonic() - started) / total))
                    time.sleep(0.25)
                if player.returncode != 0 and not self._abort.is_set():
                    fail(f"aplay exited with status {player.returncode}")
                time.sleep(self.config.ptt_tail_s)
                on_progress(1.0)
            finally:
                ptt.unkey()
                with self._lock:
                    self._stop_player()
                    self._ptt = None

    def _dry_run(self, duration: float, on_progress: Callable[[float], None]) -> None:
        started = time.monotonic()
        while not self._abort.is_set():
            elapsed = time.monotonic() - started
            if elapsed >= duration:
                break
            on_progress(elapsed / duration if duration else 1.0)
            time.sleep(0.25)
        on_progress(1.0)

    def _stop_player(self) -> None:
        if self._player is not None and self._player.poll() is None:
            self._player.terminate()
            try:
                self._player.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._player.kill()
        self._player = None

    def abort(self) -> None:
        """Stop playback and release PTT; safe to call from any thread."""
        self._abort.set()
        with self._lock:
            self._stop_player()
            if self._ptt is not None:
                try:
                    self._ptt.unkey()
                except Exception:
                    pass


def _test_pattern(size=(640, 480), label: str = "LOOPBACK TEST") -> Image.Image:
    image = Image.new("RGB", size)
    draw = ImageDraw.Draw(image)
    bars = [
        (255, 255, 255), (255, 255, 0), (0, 255, 255), (0, 255, 0),
        (255, 0, 255), (255, 0, 0), (0, 0, 255), (0, 0, 0),
    ]
    width = size[0] // len(bars)
    for index, colour in enumerate(bars):
        draw.rectangle((index * width, 0, (index + 1) * width, size[1]), fill=colour)
    draw.rectangle((0, size[1] // 2 - 30, size[0], size[1] // 2 + 30), fill=(20, 20, 20))
    draw.text((20, size[1] // 2 - 10), label, font=_font(24), fill=(255, 255, 255))
    return image


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an SSTV test WAV.")
    parser.add_argument("--test-wav", required=True, type=Path, help="output WAV path")
    parser.add_argument("--callsign", default="N0CALL")
    parser.add_argument("--mode", default="Robot36")
    parser.add_argument("--sample-rate", type=int, default=48000)
    parser.add_argument("--no-cw", action="store_true")
    args = parser.parse_args()

    image_path = args.test_wav.with_suffix(".jpg")
    make_sstv_image(
        _test_pattern(label=time.strftime("TEST %H:%M:%S")),
        image_path,
        args.mode,
        args.callsign,
        "LOOPBACK TEST",
    )

    class _Cfg:
        sstv_mode = args.mode
        sample_rate = args.sample_rate
        callsign = args.callsign
        cw_enabled = not args.no_cw
        cw_wpm = 20
        cw_tone_hz = 700.0

    duration = build_tx_wav(_Cfg, image_path, args.test_wav)
    print(f"{args.test_wav} ({duration:.1f} s, {args.mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
