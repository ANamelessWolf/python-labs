"""Salida en JSON (opción --json y -o): playlist para yt-music-playlist y lista de conciertos del año."""
from .api import Setlist
from .songs import Match, SongSearch


def playlist_name(setlist: Setlist) -> str:
    """'Gorillaz Corona Stage 2026'"""
    return f"{setlist.artist} {setlist.venue} {setlist.date.year}"


def playlist_json(setlist: Setlist, albums: list[str | None], privacy: str) -> dict:
    """Formato de yt-music-playlist (Assets/playlist.schema.json): album se omite si no se encontro."""
    tour = f" {setlist.tour}" if setlist.tour else ""
    songs = []
    for song, album in zip(setlist.songs, albums):
        item = {"title": song.title, "artist": setlist.artist}
        if album:
            item["album"] = album
        songs.append(item)
    return {
        "name": playlist_name(setlist),
        "description": f"{setlist.artist}{tour} at {setlist.place}",
        "privacy": privacy,
        "songs": songs,
    }


def concert_json(setlist: Setlist) -> dict:
    return {
        "title": setlist.title,
        "venue": setlist.place,
        "url": setlist.url,
        "date": setlist.date.isoformat(),
        "tour": setlist.tour,
        "songCount": len(setlist.songs),
    }


def year_json(band: str, years: str, setlists: list[Setlist]) -> dict:
    """years: '2026' o '2020-2026'."""
    return {"band": band, "year": years, "Tour": [concert_json(s) for s in setlists]}


def match_json(match: Match | None) -> dict | None:
    return {**concert_json(match.setlist), "songs": match.titles} if match else None


def song_json(band: str, years: str, search: SongSearch) -> dict:
    """Conciertos (del mas reciente al mas antiguo) donde se toco alguna cancion que contiene el texto."""
    return {
        "band": band,
        "song": search.query,
        "year": years,
        "checked": search.checked,
        "emptySetlists": search.empty,
        "concerts": len(search.matches),
        "plays": search.plays,
        "songs": [{"title": title, "plays": count} for title, count in search.titles.most_common()],
        "last": match_json(search.last),
        "first": match_json(search.first),
        "Tour": [match_json(m) for m in search.matches],
    }
