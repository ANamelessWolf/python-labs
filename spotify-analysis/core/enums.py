from enum import Enum

class AuthType(Enum):
    """
    Enum representing available Spotify authentication modes.
    
    Attributes:
        USER: Uses Spotify OAuth with user login and scopes.
        CLIENT: Uses Client Credentials flow without user interaction.
    """
    USER = "user"
    CLIENT = "client"
    NONE = "none"
    
class TimeRange(Enum):
    """
    Enum representing the time range options for top artists/tracks affinity data.

    - SHORT_TERM: Last ~4 weeks
    - MEDIUM_TERM: Last ~6 months
    - LONG_TERM: Last ~12 months (default)
    """
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"  # Spotify default
    LONG_TERM = "long_term"    