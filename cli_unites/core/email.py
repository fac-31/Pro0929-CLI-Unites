"""Email service abstractions for CLI-Unites."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from .config import ConfigManager

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    import resend  # type: ignore
except Exception:  # pragma: no cover
    resend = None  # type: ignore


class EmailService(ABC):
    """Abstract base for email providers."""

    @abstractmethod
    def send_invitation_email(
        self,
        email: str,
        team_name: str,
        inviter_name: str,
        invite_code: str,
        expires_at: Optional[str] = None,
    ) -> bool:
        """Send an invitation email."""

    @abstractmethod
    def send_welcome_email(self, email: str, team_name: str) -> bool:
        """Send a welcome email."""


class ResendEmailService(EmailService):
    """Concrete email service powered by Resend."""

    def __init__(self, api_key: str, from_address: str, from_name: str = "CLI-Unites") -> None:
        if resend is None:
            raise RuntimeError("Resend is not installed. Install the resend package to enable email sending.")
        resend.api_key = api_key
        self.from_address = from_address
        self.from_name = from_name

    def send_invitation_email(
        self,
        email: str,
        team_name: str,
        inviter_name: str,
        invite_code: str,
        expires_at: Optional[str] = None,
    ) -> bool:
        subject = f"You've been invited to join {team_name}"
        html = _render_invitation_html(team_name, inviter_name, invite_code, expires_at)
        text = _render_invitation_text(team_name, inviter_name, invite_code, expires_at)
        return self._send_email(email, subject, html, text)

    def send_welcome_email(self, email: str, team_name: str) -> bool:
        subject = f"Welcome to {team_name}!"
        html = _render_welcome_html(team_name)
        text = _render_welcome_text(team_name)
        return self._send_email(email, subject, html, text)

    def _send_email(self, to: str, subject: str, html: str, text: str) -> bool:
        try:
            resend.Emails.send(  # type: ignore[attr-defined]
                {
                    "from": f"{self.from_name} <{self.from_address}>",
                    "to": [to],
                    "subject": subject,
                    "html": html,
                    "text": text,
                }
            )
            return True
        except Exception as exc:  # pragma: no cover - network call
            logger.warning("Failed to send email via Resend: %s", exc)
            return False


def get_email_service(config: Optional[ConfigManager] = None) -> Optional[EmailService]:
    """Return the configured email service, if available."""
    manager = config or ConfigManager()

    if not manager.get("email_notifications_enabled", False):
        return None

    service_type = (manager.get("email_service") or "none").lower()
    if service_type != "resend":
        logger.debug("Email service '%s' not supported yet.", service_type)
        return None

    api_key = manager.get("resend_api_key")
    from_address = manager.get("email_from_address")
    from_name = manager.get("email_from_name") or "CLI-Unites"

    if not api_key or not from_address:
        logger.debug("Email service incomplete configuration; skipping email service creation.")
        return None

    try:
        return ResendEmailService(api_key, from_address, from_name)
    except Exception as exc:  # pragma: no cover - dependency issue
        logger.warning("Unable to initialize Resend email service: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Template helpers


def _render_invitation_html(team_name: str, inviter_name: str, invite_code: str, expires_at: Optional[str]) -> str:
    expiry_line = f"<p style=\"color: #6c757d; font-size: 14px;\">This invitation expires on {expires_at}.</p>" if expires_at else ""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Team Invitation - CLI-Unites</title>
    </head>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2>You've been invited to join {team_name}!</h2>
        <p>Hi there,</p>
        <p>{inviter_name} has invited you to join the <strong>"{team_name}"</strong> team on CLI-Unites.</p>

        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
            <h3>Your Invite Code:</h3>
            <code style="background-color: #e9ecef; padding: 15px; border-radius: 4px; font-size: 24px; font-weight: bold; display: block; margin: 10px 0; letter-spacing: 2px;">
                {invite_code}
            </code>
            <p>Run this command to join:</p>
            <code style="background-color: #e9ecef; padding: 10px; border-radius: 4px; display: block; margin: 10px 0;">
                notes team join {invite_code}
            </code>
        </div>

        <p><strong>First time using CLI-Unites?</strong></p>
        <ol>
            <li>Install: <code>pip install cli-unites</code></li>
            <li>Join team: <code>notes team join {invite_code}</code></li>
        </ol>

        {expiry_line}

        <hr style="margin: 30px 0;">
        <p style="color: #6c757d; font-size: 14px;">
            Best regards,<br>
            The CLI-Unites Team
        </p>
    </body>
    </html>
    """


def _render_invitation_text(team_name: str, inviter_name: str, invite_code: str, expires_at: Optional[str]) -> str:
    expiry_line = f"\nThis invitation expires on {expires_at}." if expires_at else ""
    return f"""You've been invited to join {team_name}!

{inviter_name} has invited you to join the "{team_name}" team on CLI-Unites.

Your Invite Code: {invite_code}

To join the team, run:
notes team join {invite_code}

First time using CLI-Unites?
1. Install: pip install cli-unites
2. Join team: notes team join {invite_code}{expiry_line}

Best regards,
The CLI-Unites Team
"""


def _render_welcome_html(team_name: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Welcome to {team_name} - CLI-Unites</title>
    </head>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2>Welcome to {team_name}!</h2>
        <p>Hi there,</p>
        <p>Welcome to the <strong>"{team_name}"</strong> team! You can now:</p>

        <ul>
            <li>Add notes: <code>notes add "My Note"</code></li>
            <li>List team notes: <code>notes list</code></li>
            <li>Search notes: <code>notes semantic-search "keyword"</code></li>
            <li>See team activity: <code>notes team members</code></li>
        </ul>

        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3>Get started:</h3>
            <code style="background-color: #e9ecef; padding: 10px; border-radius: 4px; display: block;">
                notes help
            </code>
        </div>

        <p>Happy collaborating!</p>

        <hr style="margin: 30px 0;">
        <p style="color: #6c757d; font-size: 14px;">
            Best regards,<br>
            The CLI-Unites Team
        </p>
    </body>
    </html>
    """


def _render_welcome_text(team_name: str) -> str:
    return f"""Welcome to {team_name}!

Hi there,

Welcome to the "{team_name}" team! You can now:

- Add notes: notes add "My Note"
- List team notes: notes list
- Search notes: notes semantic-search "keyword"
- See team members: notes team members

Get started: notes help

Happy collaborating!

Best regards,
The CLI-Unites Team
"""
