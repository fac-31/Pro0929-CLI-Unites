from __future__ import annotations

import os
import webbrowser
import logging
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
from typing import Any, Dict, Optional, Tuple
import threading
from ..database.create_client import supabase
from .config import ConfigManager
from .output import console, render_status_panel, print_success, print_error

# Get the absolute path to the templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), '..', 'templates')

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from gotrue.errors import AuthApiError  # type: ignore
except Exception:  # pragma: no cover - fallback when gotrue missing
    AuthApiError = Exception  # type: ignore

def serialize_datetime(obj):
    """Convert datetime to ISO string for JSON serialization."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return obj


def user_to_dict(user):
    return {
        "id": user.id,
        "aud": user.aud,
        "role": user.role,
        "email": user.email,
        "email_confirmed_at": serialize_datetime(
            getattr(user, "email_confirmed_at", None)
        ),
        "phone": getattr(user, "phone", None),
        "confirmation_sent_at": serialize_datetime(
            getattr(user, "confirmation_sent_at", None)
        ),
        "confirmed_at": serialize_datetime(getattr(user, "confirmed_at", None)),
        "last_sign_in_at": serialize_datetime(getattr(user, "last_sign_in_at", None)),
        "app_metadata": getattr(user, "app_metadata", {}),
        "user_metadata": getattr(user, "user_metadata", {}),
        "identities": [
            {
                k: serialize_datetime(v) if hasattr(v, "isoformat") else v
                for k, v in dict(i).items()
            }
            for i in getattr(user, "identities", [])
        ],
        "created_at": serialize_datetime(getattr(user, "created_at", None)),
        "updated_at": serialize_datetime(getattr(user, "updated_at", None)),
        "is_anonymous": getattr(user, "is_anonymous", False),
    }


def session_to_dict(session):
    return {
        "access_token": session.access_token,
        "token_type": getattr(session, "token_type", None),
        "expires_in": session.expires_in,
        "expires_at": serialize_datetime(getattr(session, "expires_at", None)),
        "refresh_token": session.refresh_token,
        "user": user_to_dict(session.user),
        "provider_token": getattr(session, "provider_token", None),
        "provider_refresh_token": getattr(session, "provider_refresh_token", None),
    }


def _get_attr(obj: Any, attr: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def _normalize_expires_at(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(raw, tz=timezone.utc).isoformat()
    if hasattr(raw, "isoformat"):
        return raw.isoformat()
    return str(raw)


class AuthManager:
    """High-level helpers around Supabase auth and local session storage."""

    def __init__(self, supabase_client: Any = None, config: Optional[ConfigManager] = None) -> None:
        self.client = supabase_client or supabase
        self.config = config or ConfigManager()
        self._session: Any = None

    # --- Helpers -----------------------------------------------------------
    @staticmethod
    def _env_tokens() -> Tuple[Optional[str], Optional[str]]:
        access = os.getenv("SUPABASE_ACCESS_TOKEN")
        refresh = os.getenv("SUPABASE_REFRESH_TOKEN")
        return access, refresh

    # --- Session helpers -------------------------------------------------
    def store_session(self, session: Any) -> None:
        """Persist auth session tokens locally."""
        if session is None:
            return

        self._session = session
        access_token = _get_attr(session, "access_token")
        refresh_token = _get_attr(session, "refresh_token")
        expires_at_iso = _normalize_expires_at(_get_attr(session, "expires_at"))

        updates: Dict[str, Any] = {
            "auth_token": access_token,
            "refresh_token": refresh_token,
            "session_expires_at": expires_at_iso,
        }

        user = _get_attr(session, "user")
        if user:
            user_id = _get_attr(user, "id")
            if user_id:
                updates["current_user_id"] = user_id

        # Drop None values to avoid overwriting defaults with nulls
        filtered_updates = {key: value for key, value in updates.items() if value is not None}
        if filtered_updates:
            self.config.update(filtered_updates)

    def get_current_user_id(self) -> Optional[str]:
        """Return the authenticated user's UUID if available."""
        cached = self.config.get("current_user_id")
        if cached:
            return cached

        session = self._get_or_load_session()
        if not session:
            return None

        user = _get_attr(session, "user")
        user_id = _get_attr(user, "id") if user else None
        if user_id:
            # Ensure we have a matching row in the Supabase users table.
            self.ensure_user_exists(user_to_dict(user) if not isinstance(user, dict) else user)
            self.config.update({"current_user_id": user_id})
        return user_id

    def refresh_user_session(self) -> bool:
        """Attempt to refresh the Supabase session using the stored refresh token."""
        env_access, _ = self._env_tokens()
        if env_access:
            # Environment-driven sessions are static tokens; nothing to refresh.
            return False

        auth_client = getattr(self.client, "auth", None)
        if auth_client is None:
            logger.debug("Supabase client has no auth attribute; cannot refresh session.")
            return False

        refresh_token = self.config.get("refresh_token")
        if not refresh_token:
            return False

        try:
            try:
                response = auth_client.refresh_session()
            except TypeError:
                # Some Supabase client versions require the refresh token explicitly.
                response = auth_client.refresh_session(refresh_token)

            session = getattr(response, "session", response)
            if not session:
                raise RuntimeError("Supabase returned no session during refresh.")

            self.store_session(session)
            user = _get_attr(session, "user")
            if user:
                self.ensure_user_exists(user_to_dict(user) if not isinstance(user, dict) else user)
            return True

        except AuthApiError as exc:  # type: ignore[var-annotated]
            logger.warning("Supabase rejected refresh token: %s", exc)
            self._clear_cached_session()
            return False
        except Exception as exc:
            logger.debug("Failed to refresh Supabase session: %s", exc)
            return False

    # --- User syncing ----------------------------------------------------
    def ensure_user_exists(self, user_data: Dict[str, Any]) -> Optional[str]:
        """Ensure a Supabase Auth user has a corresponding entry in the users table."""
        if not user_data:
            return None

        user_id = user_data.get("id")
        if not user_id:
            return None

        metadata = user_data.get("user_metadata") or {}
        profile_payload = {
            "email": user_data.get("email"),
            "full_name": metadata.get("full_name") or user_data.get("full_name"),
            "avatar_url": metadata.get("avatar_url"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        profile_payload = {k: v for k, v in profile_payload.items() if v is not None}

        table_op = None
        try:
            table_op = self.client.table("users")  # type: ignore[attr-defined]
        except Exception as exc:
            logger.debug("Supabase client unavailable; skipping user sync: %s", exc)
            self.config.update({"current_user_id": user_id})
            return user_id

        try:
            existing = table_op.select("id").eq("id", user_id).execute()
            if existing.data:
                if profile_payload:
                    table_op.update(profile_payload).eq("id", user_id).execute()
            else:
                insert_payload = {"id": user_id, **profile_payload}
                table_op.insert(insert_payload).execute()
        except Exception as exc:
            logger.warning("Failed to sync user profile with Supabase: %s", exc)

        self.config.update({"current_user_id": user_id})
        return user_id

    # --- Internals -------------------------------------------------------
    def _get_or_load_session(self) -> Any:
        if self._session is not None:
            return self._session

        auth_client = getattr(self.client, "auth", None)
        if auth_client is None:
            return None

        try:
            session = auth_client.get_session()
            if session:
                self._session = session
                return session
        except Exception:
            pass

        env_access, env_refresh = self._env_tokens()
        access_token = env_access or self.config.get("auth_token")
        refresh_token = env_refresh if env_access else self.config.get("refresh_token")
        if access_token and refresh_token:
            try:
                result = auth_client.set_session(access_token, refresh_token)
                session = getattr(result, "session", result)
                if session:
                    self._session = session
                    return session
            except Exception as exc:
                logger.debug("Unable to set Supabase session from stored tokens: %s", exc)

        return self._session

    def _clear_cached_session(self) -> None:
        self._session = None
        self.config.update(
            {
                "auth_token": None,
                "refresh_token": None,
                "session_expires_at": None,
                "current_user_id": None,
            }
        )


_default_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    global _default_auth_manager
    if _default_auth_manager is None:
        _default_auth_manager = AuthManager()
    return _default_auth_manager


def ensure_user_exists(user_data: Dict[str, Any]) -> Optional[str]:
    return get_auth_manager().ensure_user_exists(user_data)


def get_current_user_id() -> Optional[str]:
    return get_auth_manager().get_current_user_id()


def refresh_user_session() -> bool:
    return get_auth_manager().refresh_user_session()


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)
        code = query_params.get("code", [None])[0]

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        if code:
            try:
                # Exchange the authorization code for a session
                auth_response = supabase.auth.exchange_code_for_session(
                    {"auth_code": code}
                )

                config = ConfigManager()
                auth_manager = AuthManager(config=config)
                session = auth_response.session

                # Persist tokens locally and sync user profile metadata
                auth_manager.store_session(session)
                auth_manager.ensure_user_exists(user_to_dict(session.user))

                print_success("Successfully authenticated!")

                with open(os.path.join(TEMPLATES_DIR, 'success.html'), 'rb') as f:
                    self.wfile.write(f.read())

            except Exception as e:
                print_error(f"Error exchanging code for session: {e}")
                with open(os.path.join(TEMPLATES_DIR, 'error.html'), 'rb') as f:
                    self.wfile.write(f.read())

            # Shutdown server after handling the request
            threading.Thread(target=self.server.shutdown).start()
        else:
            with open(os.path.join(TEMPLATES_DIR, 'error.html'), 'rb') as f:
                self.wfile.write(f.read())


def handle_login_flow() -> None:
    console.print(
        render_status_panel(
            ["[bold]Logging in with github...[/bold]"],
            ["This will open a browser window for authentication..."],
        )
    )
    console.print()

    response = supabase.auth.sign_in_with_oauth(
        {"provider": "github", "options": {"redirect_to": "http://localhost:3000"}}
    )

    console.print(
        f"If your browser has not opened this automatically, follow this link: [link={response.url}]{response.url}[/link]"
    )
    webbrowser.open(response.url)

    with console.status(
        "[bold green]Waiting for authentication...", spinner="dots"
    ) as status:
        with HTTPServer(("localhost", 3000), OAuthCallbackHandler) as httpd:
            status.update("Starting local server to capture authentication code.")
            httpd.serve_forever()
