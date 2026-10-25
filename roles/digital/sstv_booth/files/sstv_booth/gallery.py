"""On-disk gallery of received and transmitted booth images."""

from __future__ import annotations

import re
import shutil
import threading
from datetime import datetime
from pathlib import Path

NAME_RE = re.compile(r"^(rx|tx)-[A-Za-z0-9._-]+\.(png|jpg)$")


class Gallery:
    def __init__(self, directory: Path, keep: int):
        self.directory = directory
        self.keep = keep
        self._lock = threading.Lock()
        directory.mkdir(parents=True, exist_ok=True)

    def _stamp(self) -> str:
        return datetime.now().strftime("%Y%m%d-%H%M%S-%f")

    def add(self, kind: str, source: Path, suffix: str) -> dict:
        name = f"{kind}-{self._stamp()}{suffix}"
        with self._lock:
            shutil.copyfile(source, self.directory / name)
            self._prune()
        return self._item(self.directory / name)

    def _files(self) -> list[Path]:
        files = [p for p in self.directory.iterdir() if NAME_RE.match(p.name)]
        return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)

    def _prune(self) -> None:
        for stale in self._files()[self.keep:]:
            stale.unlink(missing_ok=True)

    def _item(self, path: Path) -> dict:
        return {
            "name": path.name,
            "kind": path.name[:2],
            "url": f"/gallery/{path.name}",
            "time": path.stat().st_mtime,
        }

    def items(self, limit: int) -> list[dict]:
        with self._lock:
            return [self._item(p) for p in self._files()[:limit]]

    def latest(self, kind: str) -> dict | None:
        with self._lock:
            for path in self._files():
                if path.name.startswith(kind + "-"):
                    return self._item(path)
        return None

    def path_for(self, name: str) -> Path | None:
        if not NAME_RE.match(name):
            return None
        path = self.directory / name
        return path if path.is_file() else None
