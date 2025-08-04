from dataclasses import dataclass
from typing import List
from .artist_model import ArtistPlayCount
from .genre_model import GenrePlayCount

@dataclass
class ListeningReport:
    top_artists: List[ArtistPlayCount]
    genre_distribution: List[GenrePlayCount]
