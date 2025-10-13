from supabase import create_client
from ..core.config import ConfigManager
import os

config = ConfigManager()
auth_token = config.get("auth_token")
refresh_token = config.get("refresh_token")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

if auth_token:
    if refresh_token:
        try:
            supabase.auth.set_session(auth_token, refresh_token)
        except Exception as e:
            print(f"Warning: supabase.auth.set_session failed: {e}")
            supabase.auth.session = {
                "access_token": auth_token,
                "refresh_token": None,
            }
    else:
        # No refresh token, just set access token manually
        supabase.auth.session = {
            "access_token": auth_token,
            "refresh_token": None,
        }

user_resp = supabase.auth.get_user()

user = None
if user_resp:
    if hasattr(user_resp, "user"):
        user = user_resp.user
    elif getattr(user_resp, "data", None) and hasattr(user_resp.data, "user"):
        user = user_resp.data.user

# Debugging: 
# if user:
#     print(f"Logged in as: {user.id} ({user.email})")
# else:
#     print("No valid user session found")