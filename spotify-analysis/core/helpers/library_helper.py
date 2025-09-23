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
from typing import List, Dict, Tuple, Set
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
                    artist_id=artist_id,
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
    
def fetch_user_playlists_with_tracks(sp, include_non_owned: bool = False) -> List[Song]:
    """
    Fetches tracks from user playlists, with optional filtering by ownership.

    - Paginates over /me/playlists (limit=50)
    - Optionally filters only playlists owned by the current user
    - Paginates /playlists/{id}/tracks (limit=100)
    - Uses flat list cache per playlist id
    - Deduplicates by Spotify track id
    - Resolves artist genres with memo/file cache

    Args:
        sp: Authenticated Spotipy client.
        include_non_owned (bool): If False, include only playlists owned by the current user.

    Returns:
        List[Song]: Unique songs across all selected playlists.
    """
    try:
        limit = 50
        offset = 0
        all_playlists = []

        # Get current user id to filter ownership
        log_api_call("Getting current user for playlist filtering")
        me = sp.current_user()
        current_user_id = me.get("id")

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

        # 2) Optionally filter playlists by owner
        if not include_non_owned:
            before_count = len(all_playlists)
            all_playlists = [
                pl for pl in all_playlists
                if pl.get("owner", {}).get("id") == current_user_id
            ]
            log_api_call(
                "Filtering playlists by owner",
                f"owner_id={current_user_id}, kept={len(all_playlists)}/{before_count}"
            )            

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
                    artist_id=artist_id,
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
    artist_map = defaultdict(lambda: {"song_count": 0, "genres": set()})

    for song in songs:
        key = (song.artist_id, song.artist)  # Ensure both ID and name are considered unique pair
        artist_map[key]["song_count"] += 1
        artist_map[key]["genres"].update(song.genres or [])

    return [
        ArtistSummary(
            id=artist_id,
            name=artist_name,
            song_count=data["song_count"],
            genres=sorted(data["genres"])
        )
        for (artist_id, artist_name), data in artist_map.items()
    ]
    
def group_songs_by_genre(
    songs: List[Song],
    top_k_global_genres: int = 5,
    top_k_songs_per_genre: int = 5,
    top_k_artists_per_genre: int = 5,
) -> List[GenreSummary]:
    """
    Groups songs by genre and computes summary statistics WITHOUT play counts.

    Top songs per genre are chosen by overlap with the globally most frequent genres:
        score(song) = | set(song.genres) ∩ TOP_K_GLOBAL_GENRES |

    top_artists for each genre:
        - Aggregated by artist name inside the genre bucket
        - song_count = number of songs by that artist inside this genre
        - id = Song.artist_id if present (first seen), else None
        - genres = union of all genres across that artist's songs in this genre bucket

    Args:
        songs: All unique Song objects in the library.
        top_k_global_genres: How many global genres to use for scoring songs.
        top_k_songs_per_genre: How many top songs to return per genre.
        top_k_artists_per_genre: How many top artists to return per genre.

    Returns:
        List[GenreSummary]: One summary per genre, sorted by song_count desc.
    """
    # --- Build per-genre buckets and global genre frequency ---
    genre_to_songs: Dict[str, List[Song]] = defaultdict(list)
    global_genre_counter: Counter = Counter()

    for s in songs:
        # Deduplicate genre labels per song to avoid overcounting
        unique_genres = list(dict.fromkeys(s.genres or []))
        for g in unique_genres:
            genre_to_songs[g].append(s)
            global_genre_counter[g] += 1

    # Top-K global genres used to score songs
    top_global_genres: Set[str] = {
        g for g, _ in global_genre_counter.most_common(top_k_global_genres)
    }

    def song_score(song: Song) -> int:
        """Score by overlap with global top genres (higher is better)."""
        return len(set(song.genres or []) & top_global_genres)

    summaries: List[GenreSummary] = []

    for genre_name, songs_in_genre in genre_to_songs.items():
        # --- Aggregate artist stats within this genre bucket ---
        # artist_name -> {count, ids(set), genres(set)}
        artist_agg: Dict[str, Dict[str, object]] = defaultdict(
            lambda: {"count": 0, "ids": set(), "genres": set()}
        )

        for s in songs_in_genre:
            artist_agg[s.artist]["count"] += 1
            # Collect an id if your Song has artist_id; ignore otherwise
            artist_id: Optional[str] = getattr(s, "artist_id", None)
            if artist_id:
                artist_agg[s.artist]["ids"].add(artist_id)
            # Collect all observed genres for this artist (within this bucket)
            for g in (s.genres or []):
                artist_agg[s.artist]["genres"].add(g)

        # Build top_artists list sorted by song count desc
        # If multiple IDs were seen for same name, pick one arbitrarily (first)
        top_artists: List[ArtistSummary] = []
        for artist_name, data in sorted(
            artist_agg.items(),
            key=lambda kv: kv[1]["count"],  # sort by count asc then reverse below
        )[::-1][:top_k_artists_per_genre]:
            ids_set = data["ids"]  # type: ignore
            genres_set = data["genres"]  # type: ignore
            picked_id = next(iter(ids_set)) if ids_set else None
            top_artists.append(
                ArtistSummary(
                    id=picked_id,
                    name=artist_name,
                    song_count=int(data["count"]),     # type: ignore
                    genres=sorted(genres_set),
                )
            )

        # --- Rank songs inside this genre by score (then title/artist for tie-break) ---
        ranked_songs = sorted(
            songs_in_genre,
            key=lambda s: (-song_score(s), s.title.lower(), s.artist.lower()),
        )

        summaries.append(
            GenreSummary(
                name=genre_name,
                song_count=len(songs_in_genre),
                top_artists=top_artists,
                top_songs=ranked_songs[:top_k_songs_per_genre],
            )
        )

    # Sort genres by number of songs desc for nicer output
    summaries.sort(key=lambda g: g.song_count, reverse=True)
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
    
def get_top_artists_from_distribution(artist_dist: List[ArtistSummary], n: int = 10) -> List[ArtistSummary]:
    """
    Returns the top N artists from an artist distribution list.
    If play_count is synthetic (1 per song), this is effectively by song_count.
    """
    try:
        # Prefer song_count, tie-break by song_count
        return sorted(
            artist_dist,
            key=lambda a: (a.song_count, a.song_count),
            reverse=True
        )[:n]
    except Exception as e:
        # use your logger if you want
        raise RuntimeError(f"Error computing top artists: {e}") from e    
    
    
    
    