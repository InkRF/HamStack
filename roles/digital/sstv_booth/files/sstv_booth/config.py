"""Booth configuration loaded from the JSON file rendered by Ansible."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from pathlib import Path


@dataclass
class Config:
    callsign: str = "N0CALL"
    listen_address: str = "127.0.0.1"
    http_port: int = 8454
    data_dir: str = "/var/lib/hamstack/sstv_booth"
    rx_dir: str = "/var/lib/hamstack/slowrxd"

    sstv_mode: str = "Robot36"
    sample_rate: int = 48000
    blurb_mode: str = "fixed"  # fixed | random | none
    blurb_text: str = ""
    blurb_list: list[str] = field(default_factory=list)

    tx_enabled: bool = False
    tx_cooldown_s: float = 60.0
    max_tx_per_hour: int = 20
    rx_ignore_tail_s: float = 3.0
    rx_stale_s: float = 20.0
    countdown_s: float = 5.0
    review_s: float = 3.0

    cw_enabled: bool = True
    cw_wpm: int = 15
    cw_tone_hz: float = 700.0
    ptt_lead_s: float = 0.30
    ptt_tail_s: float = 0.20
    aioc_serial_device: str = ""
    aioc_audio_device: str = ""
    audio_device_match: str = "AllInOneCable"

    pedal_device: str = "/dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd"
    pedal_key: str = "KEY_B"
    camera_width: int = 1280
    camera_height: int = 720
    preview_width: int = 640
    preview_height: int = 360

    gallery_strip: int = 8
    gallery_keep: int = 200

    dev: bool = False

    @property
    def data_path(self) -> Path:
        return Path(self.data_dir)

    @property
    def rx_path(self) -> Path:
        return Path(self.rx_dir)

    @property
    def gallery_path(self) -> Path:
        return self.data_path / "gallery"

    @property
    def work_path(self) -> Path:
        return self.data_path / "work"


def load_config(path: str | None, dev: bool = False) -> Config:
    values: dict = {}
    if path:
        values = json.loads(Path(path).read_text(encoding="utf-8"))
    known = {f.name for f in fields(Config)}
    unknown = sorted(set(values) - known)
    if unknown:
        raise ValueError(f"Unknown sstv_booth config keys: {', '.join(unknown)}")
    config = Config(**values)
    if dev:
        config.dev = True
    if config.blurb_mode not in ("fixed", "random", "none"):
        raise ValueError(f"blurb_mode must be fixed, random or none, not {config.blurb_mode!r}")
    return config
