from typing import List, Dict
from core.helpers.logger_helper import (
    log_api_call, log_error
)

def resolve_artist_genres(sp, artist_id: str, genre_cache: Dict[str, List[str]]) -> List[str]:
    """
    Resolves the genres for a given artist using Spotify API and in-memory cache.

    Args:
        sp: Spotipy client
        artist_id (str): Spotify artist ID
        genre_cache (dict): In-memory cache to avoid duplicate API calls

    Returns:
        List[str]: List of genres (empty if not found or failed)
    """
    try:
        if not artist_id:
            return []

        if artist_id in genre_cache:
            return genre_cache[artist_id]
        log_api_call("Getting artist music genres", f"artistId={artist_id}")
        artist = sp.artist(artist_id)
        genres = artist.get("genres", [])
        genre_cache[artist_id] = genres
        return genres
    except Exception as e:
        log_error(e)
        return []
