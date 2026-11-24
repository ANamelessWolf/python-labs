"""Busqueda de una cancion dentro de los setlists descargados (la API no permite buscar por cancion)."""
import re
from collections import Counter
from dataclasses import dataclass, field

from .api import Setlist, normalize


def song_key(text: str) -> str:
    """Minusculas, sin acentos ni puntuacion: 'Feel Good Inc.' -> 'feel good inc'"""
    return " ".join(re.sub(r"[^\w]+", " ", normalize(text)).split())


@dataclass
class Match:
    setlist: Setlist
    titles: list[str]   # canciones del setlist que contienen el texto (puede repetirse si se toco dos veces)


@dataclass
class SongSearch:
    query: str
    checked: int = 0                 # setlists revisados
    empty: int = 0                   # setlists sin canciones registradas (no se puede saber si se toco)
    matches: list[Match] = field(default_factory=list)   # del mas reciente al mas antiguo

    @property
    def plays(self) -> int:
        return sum(len(m.titles) for m in self.matches)

    @property
    def titles(self) -> Counter:
        """Veces que se toco cada cancion que coincide ('eastwood' puede traer varias). Las que solo cambian en
        mayusculas o puntuacion ('CLINT EASTWOOD') cuentan como una, con el nombre de la mas reciente."""
        names: dict[str, str] = {}
        counts: Counter = Counter()
        for title in (t for m in self.matches for t in m.titles):
            name = names.setdefault(song_key(title), title)
            counts[name] += 1
        return counts

    @property
    def first(self) -> Match | None:
        return self.matches[-1] if self.matches else None

    @property
    def last(self) -> Match | None:
        return self.matches[0] if self.matches else None


def find_song(setlists: list[Setlist], query: str) -> SongSearch:
    """Conciertos cuyo setlist tiene alguna cancion que contiene el texto (sin mayusculas, acentos ni puntuacion)."""
    wanted = song_key(query)
    result = SongSearch(query)
    for setlist in sorted(setlists, key=lambda s: s.date, reverse=True):
        result.checked += 1
        if not setlist.songs:
            result.empty += 1
            continue
        titles = [song.title for song in setlist.songs if wanted in song_key(song.title)]
        if titles:
            result.matches.append(Match(setlist, titles))
    return result
