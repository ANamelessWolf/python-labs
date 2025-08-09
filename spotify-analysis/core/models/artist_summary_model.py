from dataclasses import dataclass

@dataclass
class ArtistSummary:
    name: str
    song_count: int
    total_play_count: int
