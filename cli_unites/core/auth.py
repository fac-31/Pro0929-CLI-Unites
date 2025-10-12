from __future__ import annotations

import os
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
import threading
from ..database.create_client import supabase
from .config import ConfigManager
from .output import console, render_status_panel, print_success, print_error

# Get the absolute path to the templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), '..', 'templates')


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

                # Convert session and user to dicts
                session_data = session_to_dict(auth_response.session)
                config = ConfigManager()
                config.update(
                    {
                        "auth_token": session_data["access_token"],
                        "refresh_token": session_data["refresh_token"],
                    }
                )

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
