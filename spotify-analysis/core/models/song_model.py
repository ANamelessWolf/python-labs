from dataclasses import dataclass
from typing import List

@dataclass
class Song:
    spotify_id: str
    title: str
    artist: str
    artist_id: str
    genres: List[str]
