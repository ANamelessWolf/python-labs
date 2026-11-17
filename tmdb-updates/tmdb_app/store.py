import json
import os
from datetime import datetime
from pathlib import Path

from .config import LIBRARY_FILE
from .scanner import normalize


class Library:
    """Resultado del scan guardado en data/library.json. Las llaves son la ruta de la serie."""

    def __init__(self, path: Path = LIBRARY_FILE):
        self.path = path
        self.last_scan: str | None = None
        self.series: dict[str, dict] = {}
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            self.last_scan = data.get("lastScan")
            self.series = data.get("series", {})

    def save(self, touch_scan: bool = True) -> None:
        if touch_scan:
            self.last_scan = datetime.now().isoformat(timespec="seconds")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "lastScan": self.last_scan,
            "series": dict(sorted(self.series.items(), key=lambda kv: kv[0].lower())),
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)

    def sorted_series(self) -> list[dict]:
        return sorted(self.series.values(), key=lambda s: (s["library"].lower(), s["folder"].lower()))

    def find(self, name: str) -> list[dict]:
        return find_by_name(self.sorted_series(), name, lambda s: (s["folder"], s.get("tmdbName") or ""))


def find_by_name(items, name: str, names_of) -> list:
    """Coincidencia exacta normalizada; si no hay, coincidencia parcial."""
    target = normalize(name)
    if not target:
        return []
    exact = [i for i in items if target in {normalize(n) for n in names_of(i)}]
    if exact:
        return exact
    return [i for i in items if any(target in normalize(n) for n in names_of(i))]
