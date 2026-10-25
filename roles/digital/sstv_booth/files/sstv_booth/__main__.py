"""Entry point: python -m sstv_booth --config /etc/hamstack/sstv_booth.json [--dev]."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import uvicorn

from .app import create_app
from .camera import MockCamera, PiCamera
from .config import load_config
from .machine import Booth, log
from .tx import Transmitter


class BoothServer(uvicorn.Server):
    """Release PTT and stop streams before uvicorn waits on open connections."""

    def __init__(self, config, app, booth):
        super().__init__(config)
        self._app = app
        self._booth = booth

    def handle_exit(self, sig, frame):
        self._app.state.closing = True
        self._booth.transmitter.abort()
        super().handle_exit(sig, frame)


def main() -> int:
    parser = argparse.ArgumentParser(description="HamStack SSTV booth")
    parser.add_argument("--config", help="JSON configuration file")
    parser.add_argument(
        "--dev",
        action="store_true",
        help="mock camera, no pedal device, Space key in the page acts as the pedal",
    )
    args = parser.parse_args()

    config = load_config(args.config, dev=args.dev)
    if config.dev and not args.config:
        # Self-contained scratch directories for laptop development.
        base = Path(tempfile.gettempdir()) / "sstv_booth_dev"
        config.data_dir = str(base / "data")
        config.rx_dir = str(base / "rx")
    if config.dev:
        Path(config.rx_dir).mkdir(parents=True, exist_ok=True)

    camera = MockCamera(config, log) if config.dev else PiCamera(config, log)
    transmitter = Transmitter(config, log)
    booth = Booth(config, camera, transmitter)

    pedal = None
    if not config.dev:
        from .pedal import Pedal

        pedal = Pedal(config.pedal_device, config.pedal_key, booth.pedal_threadsafe, log)

    def on_startup() -> None:
        camera.start()
        if pedal is not None:
            pedal.start()
        log(
            f"READY - {config.listen_address}:{config.http_port} mode={config.sstv_mode} "
            f"tx_enabled={config.tx_enabled} dev={config.dev}"
        )

    app = create_app(booth, on_startup=on_startup)
    server_config = uvicorn.Config(
        app,
        host=config.listen_address,
        port=config.http_port,
        log_level="warning",
    )
    try:
        BoothServer(server_config, app, booth).run()
    finally:
        booth.shutdown()
        if pedal is not None:
            pedal.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
