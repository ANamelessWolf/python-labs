from dataclasses import dataclass
from typing import List
from core.models.song_model import Song
from core.models.artist_summary_model import ArtistSummary
from core.models.genre_summary_model import GenreSummary

@dataclass
class UserLibraryReport:
    songs: List[Song]
    top_songs: List[Song]
    artist_distribution: List[ArtistSummary]
    top_artists: List[ArtistSummary]
    genre_summaries: List[GenreSummary]
    followed_artists: List[dict]  # Spotify raw artist data
