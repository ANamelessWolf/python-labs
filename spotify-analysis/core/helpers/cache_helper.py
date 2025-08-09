import os
import json
from typing import List
from core.helpers.logger_helper import log_error

def get_cache_dir() -> str:
    """
    Resolves and creates the cache directory path relative to the project.

    Returns:
        str: Absolute path to the cache/ directory
    """
    cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", "cache")
    cache_dir = os.path.abspath(cache_dir)
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir

def get_cache_file_path(user_id: str) -> str:
    """
    Constructs the full path to the user's saved tracks cache file.

    Args:
        user_id (str): Spotify user ID

    Returns:
        str: Absolute path to cache file
    """
    filename = f"{user_id}_user_saved_tracks.json"
    return os.path.join(get_cache_dir(), filename)

def load_cached_saved_tracks(user_id: str) -> List[dict]:
    """
    Loads cached saved tracks for a given user from a local JSON file.

    Args:
        user_id (str): The unique identifier of the user whose saved tracks are to be loaded.

    Raises:
        RuntimeError: If there is an error reading or parsing the cached file.

    Returns:
        List[dict]: A list of dictionaries representing the user's saved tracks. Returns an empty list if no cache exists.
    """
    try:
        path = get_cache_file_path(user_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    except Exception as e:
        log_error(e)
        raise RuntimeError(f"Error loading cached tracks for {user_id}: {str(e)}") from e
    
def save_cached_tracks(uId: str, track_data: List[dict]) -> None:
    """
    Saves the provided track data to a cache file for the specified identifier(user, playlist).
    Args:
        uId (str): The unique identifier for the user, or playlist whose tracks are being cached.
        track_data (List[dict]): A list of dictionaries containing track information to be cached.
    Raises:
        RuntimeError: If an error occurs while saving the cached tracks.
    """
    try:
        path = get_cache_file_path(uId)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(track_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log_error(e)
        raise RuntimeError(f"Error saving cached tracks for {uId}: {str(e)}") from e

def update_cache_if_needed(user_id: str, current_cache: List[dict], offset: int, limit: int, new_batch: List[dict]) -> List[dict]:
    """
    Updates the user's cache with a new batch of data if the cache does not already contain enough items.
    Args:
        user_id (str): The identifier for the user whose cache is being updated.
        current_cache (List[dict]): The current list of cached items.
        offset (int): The starting index for the new batch in the cache.
        limit (int): The number of items expected in the batch.
        new_batch (List[dict]): The new batch of items to add to the cache.
    Returns:
        List[dict]: The updated cache containing the new batch if needed.
    Raises:
        RuntimeError: If an error occurs during the cache update process.
    user_id: str, current_cache: List[dict], offset: int, limit: int, new_batch: List[dict]) -> List[dict]:
    """
    try:
        target_index = offset + limit
        cache_len = len(current_cache)

        if cache_len >= target_index:
            # Cache already has enough data
            return current_cache

        # Update by slicing and appending new batch
        updated_cache = current_cache[:offset] + new_batch
        save_cached_tracks(user_id, updated_cache)
        return updated_cache
    except Exception as e:
        log_error(e)
        raise RuntimeError(f"Error updating cache at offset {offset}: {str(e)}") from e    
    
def get_playlist_cache_file_path(playlist_id: str) -> str:
    """
    Constructs the path to the playlist cache file.

    Args:
        playlist_id (str): Spotify playlist ID

    Returns:
        str: Absolute path to the JSON cache file
    """
    filename = f"{playlist_id}_saved_tracks.json"
    return os.path.join(get_cache_dir(), filename)

def load_cached_playlist_tracks(playlist_id: str) -> dict:
    """
    Loads cached playlist tracks from a local file for the given playlist ID.

    Args:
        playlist_id (str): The unique identifier of the playlist.

    Returns:
        dict: The cached playlist tracks data if the cache file exists and is valid.
        None: If the cache file does not exist.

    Raises:
        RuntimeError: If there is an error loading or parsing the cache file.
    """
    try:
        path = get_playlist_cache_file_path(playlist_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    except Exception as e:
        log_error(e)
        raise RuntimeError(f"Error loading cached playlist {playlist_id}: {str(e)}") from e
    