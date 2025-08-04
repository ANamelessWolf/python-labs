from core.helpers.track_helper import group_top_tracks_by_artist, group_artists_and_genres
from core.models.listening_report import ListeningReport
from core.enums import TimeRange

class ListeningHistoryService:
    """
    Service for retrieving and analyzing user's long-term listening history.
    """

    def __init__(self, spotify_client):
        self.sp = spotify_client
        
    def generate_full_history_report(self, limit=50, time_range=TimeRange.MEDIUM_TERM) -> ListeningReport:
        """
        Fetches the top artists (long term) and builds a report with artist and genre counts.

        Args:
            limit (int): Max number of top artists to retrieve. The maximum number of items to return. Default: 20. Minimum: 1. Maximum: 50.
            time_range(TimeRange): Over what time frame the affinities are computed. Valid values: long_term (calculated from ~1 year of data and including all new data as it becomes available), medium_term (approximately last 6 months), short_term (approximately last 4 weeks). Default: medium_term
            Default: time_range=medium_termExample: time_range=medium_term
        Returns:
            ListeningReport: Structured data with artist and genre play counts
        """
        top_artists_data = self.sp.current_user_top_artists(limit=limit, time_range=time_range.value)
        top_tracks_data = self.sp.current_user_top_tracks(limit=limit, time_range=time_range.value)

        track_map = group_top_tracks_by_artist(top_tracks_data)
        artists, genres = group_artists_and_genres(top_artists_data, track_map)
        
        return ListeningReport(top_artists=artists, genre_distribution=genres)