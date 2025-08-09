from dataclasses import asdict
from core.enums import AuthType, TimeRange, ReportType
from core.services.listening_history_service import ListeningHistoryService
from core.services.user_library_analysis_service import UserLibraryAnalysisService
from core.helpers.report_helper import dump_listening_report
from core.auth_helper import SpotifyAuthHelper
from core.helpers.logger_helper import log_api_call, log_error

# Script configuration
limit = 50
auth_type = AuthType.USER
timeRange = TimeRange.LONG_TERM
report_type = ReportType.USER_LIBRARY

# Initialize authentication helper
auth_helper = SpotifyAuthHelper(auth_type)
sp = auth_helper.get_client()
report = None
report_name = ""

# User identified
log_api_call("Getting current user")
user = sp.current_user()
print(f"Connected as: {user['display_name']} ({user['id']})")

match report_type:
    case ReportType.TOP_HISTORY:
        service = ListeningHistoryService(sp)
        report = service.generate_full_history_report(limit, timeRange)
        report_name = "listening_report.json"
    case ReportType.RECENTLY_PLAYED:
        print(f"Report not implemented yet.")
        pass  # To be implemented
    case ReportType.USER_LIBRARY:
        service = UserLibraryAnalysisService(sp)
        report = service.generate_library_report()
        report_name = "user_library_report.json"        
    case _:
        raise ValueError("Unsupported report type")

if report is not None:
    report_path = dump_listening_report(report, filename=report_name)
    print(f"✅ Report saved to {report_path}")


