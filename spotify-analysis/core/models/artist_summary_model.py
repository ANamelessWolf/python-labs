from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ArtistSummary:
    id: Optional[str]
    name: str
    song_count: int
    genres: List[str]
