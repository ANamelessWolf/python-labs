from dataclasses import dataclass
from typing import List

@dataclass
class FollowedArtist:
    name: str
    spotify_id: str
    genres: List[str]
    url: str