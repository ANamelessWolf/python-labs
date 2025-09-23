from typing import List, Dict
from core.helpers.logger_helper import log_api_call, log_error
from core.helpers.cache_helper import (
    load_artist_genres_cache,
    save_artist_genres_cache,
)

# Module-level in-memory cache (lazy-loaded once)
_artist_genres_mem: Dict[str, List[str]] | None = None

def _get_artist_genres_mem() -> Dict[str, List[str]]:
    """
    Lazy-load the artist genres file cache into memory once.
    """
    global _artist_genres_mem
    if _artist_genres_mem is None:
        _artist_genres_mem = load_artist_genres_cache()
    return _artist_genres_mem

def _persist_artist_genres_mem() -> None:
    """
    Persist the current in-memory genres cache to disk.
    """
    if _artist_genres_mem is not None:
        save_artist_genres_cache(_artist_genres_mem)

def resolve_artist_genres(sp, artist_id: str, genre_cache: Dict[str, List[str]]) -> List[str]:
    """
    Resolves genres for an artist with a 3-layer cache strategy:
      1) function arg in-memory cache (genre_cache)       [fastest, per-call graph]
      2) module-level in-memory cache (_artist_genres_mem) [fast, per-process]
      3) file cache at cache/artist_genres.json            [persistent]
      4) Spotify API fallback                              [slow]

    On cache miss, it fetches from Spotify, updates all caches, and persists to disk.

    Returns a list of genres (possibly empty).
    """
    try:
        if not artist_id:
            return []

        # 1) Check short-lived call-level cache
        if artist_id in genre_cache:
            return genre_cache[artist_id]

        # 2) Check module-level in-memory cache (lazy loaded from file)
        mem = _get_artist_genres_mem()
        if artist_id in mem:
            genres = mem[artist_id]
            genre_cache[artist_id] = genres
            return genres

        # 3) Miss -> call Spotify API
        log_api_call("Getting artist genre", f"artistId={artist_id}")
        artist = sp.artist(artist_id)
        genres = artist.get("genres", [])

        # Update all caches
        genre_cache[artist_id] = genres
        mem[artist_id] = genres
        _persist_artist_genres_mem()

        return genres

    except Exception as e:
        log_error(e)
        return []
