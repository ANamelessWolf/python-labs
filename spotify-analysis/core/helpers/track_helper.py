from collections import Counter
from typing import List, Dict, Tuple
from core.models.artist_model import ArtistPlayCount
from core.models.genre_model import GenrePlayCount
from core.helpers.logger_helper import log_error


def group_top_tracks_by_artist(top_tracks_data: dict) -> Dict[str, List[str]]:
    """
    Groups up to 5 top tracks per artist from provided top track data.

    Args:
        top_tracks_data (dict): Spotify API response from current_user_top_tracks()

    Returns:
        Dict[str, List[str]]: Map of artist name to list of top track names
    """
    try:
        artist_track_map = {}

        for item in top_tracks_data.get('items', []):
            track_name = item['name']
            for artist in item['artists']:
                name = artist['name']
                if name not in artist_track_map:
                    artist_track_map[name] = []
                if len(artist_track_map[name]) < 5:
                    artist_track_map[name].append(track_name)

        return artist_track_map
    except Exception as e:
        log_error(e)
        raise RuntimeError(f"Error while grouping top tracks by artist: {str(e)}") from e


def group_artists_and_genres(top_artists_data: dict, track_map: Dict[str, List[str]]) -> Tuple[List[ArtistPlayCount], List[GenrePlayCount]]:
    """
    Builds artist play counts and genre counters using provided top artist data.

    Args:
        top_artists_data (dict): Spotify API response from current_user_top_artists()
        track_map (dict): Mapping of artist to top tracks

    Returns:
        Tuple[List[ArtistPlayCount], List[GenrePlayCount]]
    """
    try:
        artist_play_counts = []
        genre_counter = Counter()

        for artist in top_artists_data.get('items', []):
            name = artist['name']
            popularity = artist.get('popularity', 50)
            genres = artist.get('genres', [])
            top_tracks = track_map.get(name, [])

            artist_play_counts.append(ArtistPlayCount(
                name=name,
                play_count=popularity,
                top_tracks=top_tracks
            ))

            for genre in genres:
                genre_counter[genre] += popularity

        genre_distribution = [
            GenrePlayCount(genre=g, play_count=c)
            for g, c in genre_counter.items()
        ]

        return artist_play_counts, genre_distribution
    except Exception as e:
        log_error(e)
        raise RuntimeError(f"Error while grouping artists and genres: {str(e)}") from e
