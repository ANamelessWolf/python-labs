from core.models.song_model import Song
from core.models.artist_summary_model import ArtistSummary
from core.models.genre_summary_model import GenreSummary
from core.models.followed_artist import FollowedArtist
from core.helpers.cache_helper import (
    load_cached_saved_tracks,
    update_cache_if_needed,
    load_cached_playlist_tracks,
    save_cached_tracks
)
from core.helpers.resolve_helpers import (
    resolve_artist_genres
)
from core.helpers.logger_helper import (
    log_api_call, log_error
)
from typing import List, Dict, Tuple
import time
from collections import defaultdict, Counter

def fetch_user_saved_tracks(sp) -> List[Song]:
    """
    Fetches the user's saved (liked) tracks using Spotify API paging and cache.

    - Uses cache file {user_id}_user_saved_tracks.json
    - If the cache has enough tracks for the current offset + limit, uses it
    - Otherwise, fetches from the API and updates the cache

    Returns:
        List[Song]: List of liked songs with genre and artist info
    """
    try:
        log_api_call("Getting current user id")
        user_id = sp.current_user()["id"]
        offset = 0
        limit = 50
        all_songs = []
        seen_ids = set()
        genre_cache = {}

        cached_data = load_cached_saved_tracks(user_id)

        while True:
            # If cache has enough items, use slice from cache
            if len(cached_data) >= offset + limit:
                track_batch = cached_data[offset:offset+limit]
            else:
                # Fetch batch from API
                log_api_call("Getting user's saved tracks", f"limit={limit}, offset={offset}")
                api_response = sp.current_user_saved_tracks(limit=limit, offset=offset)
                api_batch = [item["track"] for item in api_response["items"] if item.get("track")]
                if not api_batch:
                    break
                # Update and save cache
                cached_data = update_cache_if_needed(user_id, cached_data, offset, limit, api_batch)
                track_batch = api_batch

            # Process batch into Song objects
            for track in track_batch:
                track_id = track.get("id")
                if not track_id or track_id in seen_ids:
                    continue
                seen_ids.add(track_id)

                name = track["name"]
                artist_data = track["artists"][0]
                artist_id = artist_data["id"]
                artist_name = artist_data["name"]
                genres = resolve_artist_genres(sp, artist_id, genre_cache)

                all_songs.append(Song(
                    spotify_id=track_id,
                    title=name,
                    artist=artist_name,
                    play_count=1,
                    genres=genres
                ))

            if len(track_batch) < limit:
                break

            offset += limit
            time.sleep(0.1)

        return all_songs

    except Exception as e:
        log_error(e)
        raise RuntimeError(f"Failed to fetch user saved tracks: {str(e)}") from e
    
def fetch_user_playlists_with_tracks(sp) -> List[Song]:
    """
    Fetches all tracks from all user playlists using Spotify API with per-playlist caching.
    
    - Loads full playlists (100 tracks at a time) using pagination
    - Caches track lists per playlist
    - Avoids duplicates using track ID
    - Resolves artist genres (cached in memory)

    Returns:
        List[Song]: List of unique Song objects from all playlists
    """
    try:
        limit = 50
        offset = 0
        all_playlists = []

        # Fetch all user playlists with pagination
        while True:
            log_api_call("Getting user's current playlists", f"limit={limit}, offset={offset}")
            response = sp.current_user_playlists(limit=limit, offset=offset)
            page = response.get("items", [])
            all_playlists.extend(page)
            if not response.get("next"):
                break
            offset += limit
            time.sleep(0.1)

        all_songs = []
        seen_ids = set()
        genre_cache = {}

        for playlist in all_playlists:
            pl_id = playlist["id"]
            pl_name = playlist.get("name", "Unnamed Playlist")
            pl_total = playlist["tracks"]["total"]

            # Try to load from cache
            cached = load_cached_playlist_tracks(pl_id)
            if cached and isinstance(cached, list) and len(cached) >= pl_total:
                track_items = cached
            else:
                # Fetch all tracks for this playlist with pagination
                track_items = []
                track_offset = 0
                track_limit = 100

                while True:
                    log_api_call("Getting playlists tracks", f"playlistId={pl_id}, limit={limit}, offset={offset}")
                    track_page = sp.playlist_tracks(pl_id, limit=track_limit, offset=track_offset)
                    track_items.extend(track_page.get("items", []))
                    if not track_page.get("next"):
                        break
                    track_offset += track_limit
                    time.sleep(0.1)

                # Save flat list of track items to cache
                save_cached_tracks(pl_id, track_items)

            # Extract Song objects
            for item in track_items:
                track = item.get("track")
                if not track:
                    continue

                track_id = track.get("id")
                if not track_id or track_id in seen_ids:
                    continue
                seen_ids.add(track_id)

                artist_data = track["artists"][0]
                artist_id = artist_data["id"]
                artist_name = artist_data["name"]
                genres = resolve_artist_genres(sp, artist_id, genre_cache)

                all_songs.append(Song(
                    spotify_id=track_id,
                    title=track["name"],
                    artist=artist_name,
                    play_count=1,
                    genres=genres
                ))

        return all_songs

    except Exception as e:
        log_error(e)
        raise RuntimeError(f"Error fetching playlist songs: {str(e)}") from e
    
def fetch_user_playlists_and_saved_tracks(sp) -> List[Song]:
    """
    Fetches all user songs from both liked/saved tracks and all playlists.
    Merges the results, removes duplicates by track ID, and returns a unified list.

    Args:
        sp: Authenticated Spotify client

    Returns:
        List[Song]: List of unique Song objects
    """
    try:
        liked_songs = fetch_user_saved_tracks(sp)
        playlist_songs = fetch_user_playlists_with_tracks(sp)

        by_id = {}
        fallback_seen: set[Tuple[str, str]] = set()
        merged: List[Song] = []

        for s in liked_songs:
            if s.spotify_id:
                if s.spotify_id not in by_id:
                    by_id[s.spotify_id] = s
            else:
                key = (s.title.lower(), s.artist.lower())
                if key not in fallback_seen:
                    fallback_seen.add(key)
                    merged.append(s)

        for s in playlist_songs:
            if s.spotify_id:
                if s.spotify_id not in by_id:
                    by_id[s.spotify_id] = s
            else:
                key = (s.title.lower(), s.artist.lower())
                if key not in fallback_seen:
                    fallback_seen.add(key)
                    merged.append(s)

        merged.extend(by_id.values())
        return merged

    except Exception as e:
        log_error(e)
        raise RuntimeError(f"Error merging liked and playlist tracks: {str(e)}")
    
def group_songs_by_artist(songs: List[Song]) -> List[ArtistSummary]:
    """
    Groups songs by artist and computes summary statistics.

    Args:
        songs (List[Song]): List of Song objects.

    Returns:
        List[ArtistSummary]: Aggregated summary for each artist.
    """
    artist_map = defaultdict(lambda: {"song_count": 0, "total_play_count": 0})

    for song in songs:
        key = song.artist
        artist_map[key]["song_count"] += 1
        artist_map[key]["total_play_count"] += song.play_count

    return [
        ArtistSummary(
            name=artist,
            song_count=data["song_count"],
            total_play_count=data["total_play_count"]
        )
        for artist, data in artist_map.items()
    ]    
    
def group_songs_by_genre(songs: List[Song]) -> List[GenreSummary]:
    """
    Groups songs by genre and computes summary statistics.

    Args:
        songs (List[Song]): List of Song objects.

    Returns:
        List[GenreSummary]: Aggregated summary for each genre.
    """
    genre_map: Dict[str, Dict] = defaultdict(lambda: {
        "songs": [],
        "artist_counter": Counter()
    })

    for song in songs:
        for genre in song.genres:
            genre_map[genre]["songs"].append(song)
            genre_map[genre]["artist_counter"][song.artist] += song.play_count

    summaries = []
    for genre, data in genre_map.items():
        songs_in_genre = data["songs"]
        artist_counter = data["artist_counter"]

        summaries.append(GenreSummary(
            name=genre,
            song_count=len(songs_in_genre),
            total_play_count=sum(song.play_count for song in songs_in_genre),
            top_artists=[
                {"name": artist, "total_play_count": count}
                for artist, count in artist_counter.most_common(5)
            ],
            top_songs=sorted(
                songs_in_genre, key=lambda s: s.play_count, reverse=True
            )[:5]
        ))

    return summaries    
    
def get_top_n_songs(all_songs: List[Song], n: int = 25) -> List[Song]:
    """
    Returns the top N songs sorted by play count.

    Args:
        all_songs (List[Song]): The full list of Song objects.
        n (int): Number of top songs to return (default is 25).

    Returns:
        List[Song]: Top N songs by play count.
    """
    try:
        sorted_songs = sorted(all_songs, key=lambda s: s.play_count, reverse=True)
        return sorted_songs[:n]
    except Exception as e:
        log_error(e)
        raise RuntimeError(f"Error sorting top {n} songs: {str(e)}") from e
    
def fetch_followed_artists(sp) -> List[FollowedArtist]:
    """
    Fetches the list of artists the user is following and returns structured FollowedArtist objects.

    Args:
        sp (Spotify): Authenticated Spotipy client.

    Returns:
        List[FollowedArtist]: List of followed artists with basic info.
    """
    try:
        artists: List[FollowedArtist] = []
        after = None
        limit = 50

        while True:
            log_api_call("Getting user followed artists", f"limit={limit}, after={after}")
            response = sp.current_user_followed_artists(limit=limit, after=after)
            items = response.get("artists", {}).get("items", [])

            for item in items:
                artist = FollowedArtist(
                    name=item.get("name"),
                    spotify_id=item.get("id"),
                    genres=item.get("genres", []),
                    url=item.get("external_urls", {}).get("spotify", "")
                )
                artists.append(artist)

            after = response.get("artists", {}).get("cursors", {}).get("after")
            if not after:
                break

            time.sleep(0.1)

        return sorted(artists, key=lambda a: a.name.lower())

    except Exception as e:
        log_error(e)
        raise RuntimeError(f"Unexpected error fetching followed artists: {e}") from e    
    
    
    
    
    