"""Cliente de la API oficial de setlist.fm (https://api.setlist.fm/docs/1.0/index.html).

La API pide la fecha como dd-MM-yyyy y regresa 20 setlists por pagina. Limite por defecto: 2 peticiones por
segundo y 1440 al dia por API key.
"""
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime

import requests

USER_AGENT = "setlist-fm-scrapper (python-labs)"
PAGE_DELAY = 0.6   # segundos minimos entre peticiones (limite de 2 peticiones por segundo)


class SetlistFMError(Exception):
    """Error que se muestra tal cual al usuario (API key invalida, limite diario...)."""


@dataclass
class Song:
    title: str
    cover: str | None = None   # artista original si es un cover
    info: str | None = None


@dataclass
class Setlist:
    id: str
    date: date
    artist: str
    venue: str
    city: str
    country: str
    tour: str | None
    url: str
    songs: list[Song] = field(default_factory=list)

    @property
    def place(self) -> str:
        """'Autódromo Hermanos Rodríguez, Mexico City, Mexico'"""
        return ", ".join(p for p in (self.venue, self.city, self.country) if p)

    @property
    def title(self) -> str:
        return f"{self.artist} at {self.place}"


def normalize(text: str) -> str:
    """Minusculas, sin acentos ni espacios repetidos: para comparar nombres."""
    text = unicodedata.normalize("NFKD", text or "")
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).casefold().split())


def parse_setlist(raw: dict) -> Setlist:
    venue = raw.get("venue") or {}
    city = venue.get("city") or {}
    songs = []
    for block in (raw.get("sets") or {}).get("set", []):
        for song in block.get("song", []):
            # tape = sonido de fondo (intro, outro); name vacio = cancion sin identificar
            if song.get("tape") or not (song.get("name") or "").strip():
                continue
            songs.append(Song(song["name"].strip(), (song.get("cover") or {}).get("name"), song.get("info")))
    return Setlist(
        id=raw.get("id", ""),
        date=datetime.strptime(raw["eventDate"], "%d-%m-%Y").date(),
        artist=(raw.get("artist") or {}).get("name", ""),
        venue=venue.get("name", ""),
        city=city.get("name", ""),
        country=(city.get("country") or {}).get("name", ""),
        tour=(raw.get("tour") or {}).get("name"),
        url=raw.get("url", ""),
        songs=songs,
    )


class Client:
    def __init__(self, api_key: str, base_url: str, language: str = "en"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"x-api-key": api_key, "Accept": "application/json",
                                     "Accept-Language": language, "User-Agent": USER_AGENT})
        self.last_request = 0.0
        self.requests = 0   # peticiones hechas en esta ejecucion (limite diario de la API: 1440)

    def _get(self, path: str, params: dict, retries: int = 3) -> dict | None:
        """GET a la API. None si no hay resultados (la API responde 404)."""
        for attempt in range(1, retries + 1):
            wait = PAGE_DELAY - (time.monotonic() - self.last_request)
            if wait > 0:
                time.sleep(wait)
            self.last_request = time.monotonic()
            self.requests += 1
            response = self.session.get(f"{self.base_url}{path}", params=params, timeout=30)
            if response.status_code == 429 or response.status_code >= 500:
                time.sleep(2 * attempt)
                continue
            break
        if response.status_code == 404:
            return None
        if response.status_code in (401, 403):
            raise SetlistFMError("La API rechazó la API key (401/403). Revisa API_KEY en config\\settings.json.")
        if response.status_code == 429:
            raise SetlistFMError("Límite de peticiones de la API alcanzado (429). Intenta más tarde.")
        response.raise_for_status()
        return response.json()

    def search_page(self, band: str, *, on: date | None = None, year: int | None = None,
                    page: int = 1) -> tuple[list[dict], int]:
        """Una pagina de /search/setlists sin procesar. Regresa (setlists, total de resultados)."""
        params = {"artistName": band, "p": page}
        if on:
            params["date"] = on.strftime("%d-%m-%Y")
        if year:
            params["year"] = year
        data = self._get("/search/setlists", params)
        if not data:
            return [], 0
        return data.get("setlist", []), int(data.get("total", 0))

    def fetch_all(self, band: str, *, on: date | None = None, year: int | None = None) -> list[dict]:
        """Todas las paginas sin procesar (asi se guardan en la cache)."""
        raw, total = self.search_page(band, on=on, year=year)
        page = 1
        while total and len(raw) < total:
            page += 1
            more, _ = self.search_page(band, on=on, year=year, page=page)
            if not more:
                break
            raw.extend(more)
        return raw

    def search_all(self, band: str, *, on: date | None = None, year: int | None = None) -> list[Setlist]:
        return only_band(parse_all(self.fetch_all(band, on=on, year=year)), band)


def parse_all(raw: list[dict]) -> list[Setlist]:
    return [parse_setlist(s) for s in raw]


def only_band(setlists: list[Setlist], band: str) -> list[Setlist]:
    """Si alguno coincide exactamente con la banda, descarta los demas artistas
    (artistName busca por aproximacion: 'Gorillaz' tambien trae bandas tributo)."""
    exact = [s for s in setlists if normalize(s.artist) == normalize(band)]
    return exact or setlists
