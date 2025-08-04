from dataclasses import dataclass, field
from typing import List

@dataclass
class ArtistPlayCount:
    name: str
    play_count: int
    top_tracks: List[str] = field(default_factory=list)
