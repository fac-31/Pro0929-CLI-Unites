from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client

from ..core.config import ConfigManager

load_dotenv()

config = ConfigManager()
auth_token = config.get("auth_token")
refresh_token = config.get("refresh_token")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


class _ConnectTableStub:
    """Stub for the 'connect' table to prevent errors when table doesn't exist."""

    def select(self, *args: Any, **kwargs: Any) -> "_ConnectTableStub":
        return self

    def execute(self) -> Any:
        class _Response:
            data = []
            error = None

            def __repr__(self) -> str:  # pragma: no cover - repr helper
                return "<SupabaseStubResponse data=0>"

        return _Response()

    def __getattr__(self, name: str):  # pragma: no cover - chained methods
        def _chain(*args: Any, **kwargs: Any) -> "_ConnectTableStub":
            return self

        return _chain


class _SupabaseStub:
    """Stub client for when Supabase is not configured."""

    def table(self, name: str) -> _ConnectTableStub:
        return _ConnectTableStub()

    def __getattr__(self, attr: str) -> Any:  # pragma: no cover - unused attrs
        raise AttributeError(attr)


class _SafeClient:
    """Wrapper around Supabase client that handles missing tables gracefully."""

    def __init__(self, inner: Client) -> None:
        self._inner = inner

    def table(self, name: str):
        if name == "connect":
            return _ConnectTableStub()
        return self._inner.table(name)

    def __getattr__(self, attr: str) -> Any:
        return getattr(self._inner, attr)


def _create_client() -> Client | _SupabaseStub | _SafeClient:
    """Create Supabase client with authentication and graceful fallback."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return _SupabaseStub()

    try:
        base = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Set up authentication session if available
        if auth_token:
            if refresh_token:
                try:
                    base.auth.set_session(auth_token, refresh_token)
                except Exception as e:
                    print(f"Warning: supabase.auth.set_session failed: {e}")
                    base.auth.session = {
                        "access_token": auth_token,
                        "refresh_token": None,
                    }
            else:
                # No refresh token, just set access token manually
                base.auth.session = {
                    "access_token": auth_token,
                    "refresh_token": None,
                }

        # Verify user session (optional debugging)
        try:
            user_resp = base.auth.get_user()
            user = None
            if user_resp:
                if hasattr(user_resp, "user"):
                    user = user_resp.user
                elif getattr(user_resp, "data", None) and hasattr(user_resp.data, "user"):
                    user = user_resp.data.user
            
            # Debugging (uncomment if needed):
            # if user:
            #     print(f"Logged in as: {user.id} ({user.email})")
            # else:
            #     print("No valid user session found")
        except Exception:
            # Ignore auth verification errors - client still works for public operations
            pass

        return _SafeClient(base)
    except Exception:
        # If client creation fails, return stub for offline functionality
        return _SupabaseStub()


supabase: Client | _SupabaseStub | _SafeClient = _create_client()
