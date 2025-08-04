from dataclasses import asdict
from core.enums import AuthType, TimeRange
from core.services.listening_history_service import ListeningHistoryService
from core.helpers.report_helper import dump_listening_report
from core.auth_helper import SpotifyAuthHelper

# Script configuration
limit = 50
auth_type = AuthType.USER
timeRange = TimeRange.LONG_TERM

# Initialize authentication helper
auth_helper = SpotifyAuthHelper(auth_type)
sp = auth_helper.get_client()

service = ListeningHistoryService(sp)
report = service.generate_full_history_report(limit, timeRange)

# Convert dataclass to dict
output_data = asdict(report)

report = service.generate_full_history_report(limit=50)
report_path = dump_listening_report(report, filename="listening_report.json")
print(f"✅ Report saved to {report_path}")

user = sp.current_user()
print(f"Conectado como: {user['display_name']}")
