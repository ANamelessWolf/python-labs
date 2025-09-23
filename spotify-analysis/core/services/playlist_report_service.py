from core.models.user_library_report import UserLibraryReport
from core.helpers.library_helper import (
    fetch_user_playlist_tracks,
    group_songs_by_artist,
    group_songs_by_genre,
    fetch_followed_artists,
    get_top_artists_from_distribution,
)
from core.helpers.logger_helper import log_error

class PlaylistReportService:
    def __init__(self, sp, playlistId):
        self.sp = sp
        self.playlistId = playlistId

    def generate_library_report(self) -> PlaylistReport:
        """
        Generates a full report based on user's liked songs, playlists, and followed artists.

        Returns:
            UserLibraryReport: Structured data containing detailed music library analysis.
        """
        try:
            # 1. Fetch all user songs (liked + playlists)
            playlist = self.sp.playlist(self.playlistId)
            all_songs = fetch_user_playlist_tracks(self.sp, playlist)

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
