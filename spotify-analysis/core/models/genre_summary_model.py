from dataclasses import dataclass
from typing import List
from core.models.artist_summary_model import ArtistSummary
from core.models.song_model import Song

@dataclass
class GenreSummary:
    name: str
    song_count: int
    total_play_count: int
    top_artists: List[ArtistSummary]
    top_songs: List[Song]
