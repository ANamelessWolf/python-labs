import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from .enums import AuthType

class SpotifyAuthHelper:
    """
    Helper class to handle Spotify API authentication.

    Supports both user-based and client-based authentication modes.

    Args:
        auth_type (AuthType): Enum specifying the authentication type.
    """

    def __init__(self, auth_type: AuthType):
        load_dotenv()  # Load environment variables from .env file
        self.auth_type = auth_type

    def get_client(self) -> spotipy.Spotify:
        """
        Returns an authenticated Spotify client based on the selected auth type.

        Returns:
            spotipy.Spotify: Authenticated Spotify client instance.
        
        Raises:
            ValueError: If an unsupported AuthType is provided.
        """
        if self.auth_type == AuthType.USER:
            return spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=os.getenv("SPOTIPY_CLIENT_ID"),
                client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
                redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
                scope='playlist-read-private',
                cache_path='spotify_token_cache.json'
            ))
        elif self.auth_type == AuthType.CLIENT:
            return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
                client_id=os.getenv("SPOTIPY_CLIENT_ID"),
                client_secret=os.getenv("SPOTIPY_CLIENT_SECRET")
            ))
        else:
            raise ValueError("Unsupported authentication type")
