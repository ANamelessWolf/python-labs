from core.auth_helper import SpotifyAuthHelper
from core.enums import AuthType

# Select authentication type: AuthType.USER or AuthType.CLIENT
auth_type = AuthType.USER

# Initialize authentication helper
auth_helper = SpotifyAuthHelper(auth_type)
sp = auth_helper.get_client()

user = sp.current_user()
print(f"Conectado como: {user['display_name']}")
