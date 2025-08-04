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