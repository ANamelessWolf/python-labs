from core.models.user_library_report import UserLibraryReport
from core.helpers.library_helper import (
    fetch_user_playlists_and_saved_tracks,
    group_songs_by_artist,
    group_songs_by_genre,
    get_top_n_songs,
    fetch_followed_artists,
    get_top_artists_from_distribution,
)
from core.helpers.logger_helper import log_error

class UserLibraryAnalysisService:
    def __init__(self, sp):
        self.sp = sp

    def generate_library_report(self) -> UserLibraryReport:
        """
        Generates a full report based on user's liked songs, playlists, and followed artists.

        Returns:
            UserLibraryReport: Structured data containing detailed music library analysis.
        """
        try:
            # 1. Fetch all user songs (liked + playlists)
            all_songs = fetch_user_playlists_and_saved_tracks(self.sp)

            # 2. Group and analyze
            artist_summary = group_songs_by_artist(all_songs)
            genre_summary = group_songs_by_genre(all_songs)
            top_songs = []
            followed_artists = fetch_followed_artists(self.sp)
            top_artists = get_top_artists_from_distribution(artist_summary, n=10)

            # 3. Create report model
            report = UserLibraryReport(
                songs=all_songs,
                top_songs=top_songs,
                artist_distribution=artist_summary,
                top_artists=top_artists,
                genre_distribution=genre_summary,
                followed_artists=followed_artists
            )

            return report
        except Exception as e:
            log_error(e)
            raise RuntimeError(f"Failed to generate library report: {e}") from e
