from dataclasses import dataclass
from typing import List

@dataclass
class Song:
    spotify_id: str
    title: str
    artist: str
    play_count: int
    genres: List[str]
