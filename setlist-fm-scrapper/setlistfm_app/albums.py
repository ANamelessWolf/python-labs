"""Album de cada cancion con la iTunes Search API (gratis, sin key).

setlist.fm no guarda el album. Primero se baja el catalogo del artista (hasta 200 canciones, 1 peticion) y solo
las canciones que no aparecen ahi se buscan una por una. iTunes permite ~20 peticiones por minuto, por eso las
busquedas sueltas esperan SONG_DELAY y todo se guarda en cache/albums.json (tambien los no encontrados).
"""
import json
import re
import time
from pathlib import Path

import requests

from .api import normalize

SEARCH_URL = "https://itunes.apple.com/search"
SONG_DELAY = 3.0
# En vivo, karaoke, tributos: nunca son el album original. Se buscan en lo agregado al nombre ("(Live)",
# "- Live") para no descartar canciones como "Live Forever"; en el album tambien "Live at ...", "Unplugged".
LIVE = re.compile(r"\b(live|en vivo|karaoke|tribute)\b", re.I)
LIVE_ALBUM = re.compile(r"\b(live (at|in|from|on)|unplugged|karaoke|tribute)\b", re.I)
# Otras versiones: se aceptan, pero solo si no hay una sin agregados
VERSION = re.compile(r"\b(remix|mix|version|instrumental|acoustic|demo|edit|rework|dub)\b", re.I)
# Agregados que no cambian la cancion
NEUTRAL = re.compile(r"^\W*(feat\.?|ft\.?|featuring|with|from|album version|remaster(ed)?|\d{4} remaster(ed)?)\b",
                     re.I)
COMPILATION = re.compile(r"\b(greatest hits|best of|collection|anthology|essentials|the singles|hits)\b", re.I)
EXTENDED = re.compile(r"\b(deluxe|edition|expanded|remaster(ed)?|anniversary|bonus|version)\b", re.I)


def decorations(name: str) -> list[str]:
    """Lo que va entre parentesis/corchetes o despues de ' - ': 'Song (Live) - Remastered' -> ['Live', 'Remastered']"""
    parts = re.findall(r"[(\[]([^)\]]*)[)\]]", name)
    if " - " in name:
        parts.append(name.split(" - ", 1)[1])
    return parts


def is_live(track: dict) -> bool:
    album = track.get("collectionName", "")
    words = " ".join(decorations(track.get("trackName", "")) + decorations(album))
    return bool(LIVE.search(words) or LIVE_ALBUM.search(album))


def version_penalty(track_name: str) -> int:
    """0 = cancion tal cual (o solo feat./remaster), 1 = otro agregado, 2 = remix/version/edit..."""
    extra = [d for d in decorations(track_name) if not NEUTRAL.search(d)]
    if any(VERSION.search(d) for d in extra):
        return 2
    return 1 if extra else 0


def clean_title(title: str) -> str:
    """'Feel Good Inc. (feat. De La Soul) - Remastered' -> 'feel good inc'"""
    title = re.sub(r"\s*[(\[][^)\]]*[)\]]", "", title)   # (feat. ...), [Live], ...
    title = re.sub(r"\s+-\s+.*$", "", title)               # - Remastered 2015, - Single Version
    return re.sub(r"[^\w]+", " ", normalize(title)).strip()


def clean_album(name: str) -> str:
    """'Plastic Beach (Deluxe Version)' -> 'Plastic Beach'; 'Song - Single' -> 'Song'"""
    name = re.sub(r"\s+-\s+(Single|EP)$", "", name)
    name = re.sub(r"\s*[(\[][^)\]]*[)\]]", lambda m: "" if EXTENDED.search(m.group()) else m.group(), name)
    return name.strip()


def artist_key(artist: str) -> str:
    return re.sub(r"[^\w]+", "", normalize(artist))


def rank(track: dict) -> tuple:
    """Menor = mejor: cancion sin agregados; album de estudio > edicion deluxe > single/EP/recopilacion;
    luego el mas antiguo."""
    album = track.get("collectionName", "")
    if COMPILATION.search(album) or (track.get("trackCount") or 0) < 5 or re.search(r" - (Single|EP)$", album):
        tier = 2
    elif EXTENDED.search(album):
        tier = 1
    else:
        tier = 0
    return version_penalty(track.get("trackName", "")), tier, track.get("releaseDate", "")


class AlbumFinder:
    def __init__(self, country: str = "US", cache_path: Path | None = None):
        self.country = country
        self.cache_path = cache_path
        self.session = requests.Session()
        self.catalogs: dict[str, list[dict]] = {}
        self.cache: dict[str, str | None] = {}
        self.last_search = 0.0
        if cache_path and cache_path.exists():
            try:
                self.cache = json.loads(cache_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self.cache = {}

    def save(self) -> None:
        if self.cache_path:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(self.cache, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                                       encoding="utf-8")

    def _search(self, **params) -> list[dict]:
        wait = SONG_DELAY - (time.monotonic() - self.last_search)
        if self.last_search and wait > 0:
            time.sleep(wait)
        self.last_search = time.monotonic()
        params = {"entity": "song", "media": "music", "country": self.country, **params}
        for attempt in range(1, 4):
            response = self.session.get(SEARCH_URL, params=params, timeout=30)
            if response.status_code in (403, 429) or response.status_code >= 500:
                time.sleep(10 * attempt)   # iTunes responde 403 al pasar el limite por minuto
                continue
            response.raise_for_status()
            return response.json().get("results", [])
        response.raise_for_status()
        return []

    def _catalog(self, artist: str) -> list[dict]:
        key = artist_key(artist)
        if key not in self.catalogs:
            self.catalogs[key] = self._search(term=artist, attribute="artistTerm", limit=200)
        return self.catalogs[key]

    @staticmethod
    def _candidates(tracks: list[dict], title: str, artist: str) -> list[dict]:
        wanted, who = clean_title(title), artist_key(artist)
        return [t for t in tracks
                if who in artist_key(t.get("artistName", ""))
                and clean_title(t.get("trackName", "")) == wanted
                and not is_live(t)]

    def lookup(self, title: str, artist: str) -> str | None:
        """Album de la cancion o None. Lanza requests.RequestException si iTunes no responde."""
        key = f"{artist_key(artist)}|{clean_title(title)}"
        if key in self.cache:
            return self.cache[key]
        candidates = self._candidates(self._catalog(artist), title, artist)
        if not candidates or min(rank(t) for t in candidates)[0] > 0:
            # No esta en el catalogo, o solo como remix/otra version: se busca la cancion directamente
            candidates += self._candidates(self._search(term=f"{artist} {title}", limit=25), title, artist)
        album = clean_album(min(candidates, key=rank)["collectionName"]) if candidates else None
        self.cache[key] = album
        return album

    def song_album(self, title: str, artist: str, cover: str | None = None) -> str | None:
        """Busca con la banda; si es un cover y no aparece, con el artista original."""
        album = self.lookup(title, artist)
        if album is None and cover and artist_key(cover) != artist_key(artist):
            album = self.lookup(title, cover)
        return album
