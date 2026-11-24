"""Cache de setlists por banda y año: cache/setlists/<banda>/<año>.json con la respuesta cruda de la API.

setlist.fm se sigue editando despues de cada concierto (se agregan canciones, se corrigen datos), asi que el año
actual se vuelve a pedir cada CURRENT_TTL y el anterior cada PREVIOUS_TTL; los años mas viejos no se vuelven a pedir.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

from .albums import artist_key
from .api import Client

CURRENT_TTL = timedelta(hours=6)
PREVIOUS_TTL = timedelta(days=7)


def ttl(year: int, now: datetime) -> timedelta | None:
    """None = no caduca."""
    if year >= now.year:
        return CURRENT_TTL
    if year == now.year - 1:
        return PREVIOUS_TTL
    return None


class SetlistCache:
    def __init__(self, client: Client, folder: Path):
        self.client = client
        self.folder = folder
        self.downloaded = 0   # años pedidos a la API (el resto salio de la cache)

    def path(self, band: str, year: int) -> Path:
        return self.folder / (artist_key(band) or "_") / f"{year}.json"

    def _read(self, path: Path, year: int) -> list[dict] | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            fetched = datetime.fromisoformat(data["fetched"])
        except (OSError, ValueError, KeyError):
            return None
        now = datetime.now()
        limit = ttl(year, now)
        if limit is not None and now - fetched > limit:
            return None
        return data.get("setlists", [])

    def year(self, band: str, year: int, refresh: bool = False) -> list[dict]:
        """Setlists crudos de la banda en ese año; de la cache si sigue vigente (y no se pidio refresh)."""
        path = self.path(band, year)
        if not refresh and path.exists():
            cached = self._read(path, year)
            if cached is not None:
                return cached
        raw = self.client.fetch_all(band, year=year)
        self.downloaded += 1
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"band": band, "year": year, "fetched": datetime.now().isoformat(timespec="seconds"), "setlists": raw}
        path.write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")
        return raw
