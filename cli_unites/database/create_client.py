from supabase import create_client
from ..core.config import ConfigManager
import os

# Load tokens from config
config = ConfigManager()
auth_token = config.get("auth_token")
refresh_token = config.get("refresh_token")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Try to set session if tokens exist
if auth_token:
    # If you have a refresh token use it; else fallback to manual session
    if refresh_token:
        try:
            supabase.auth.set_session(auth_token, refresh_token)
        except Exception as e:
            # Log or warn that refresh session failed; fallback
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

# Safe call to get user
user_resp = supabase.auth.get_user()

# user_resp may hold `.user` or `.data.user` depending on version
user = None
if user_resp:
    # Some versions: user_resp.user
    if hasattr(user_resp, "user"):
        user = user_resp.user
    # Or alternate version: user_resp.data.user
    elif getattr(user_resp, "data", None) and hasattr(user_resp.data, "user"):
        user = user_resp.data.user

if user:
    print(f"Logged in as: {user.id} ({user.email})")
else:
    print("No valid user session found")
