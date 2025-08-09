from dataclasses import dataclass
from typing import List

@dataclass
class Song:
    title: str
    artist: str
    play_count: int
    genres: List[str]
