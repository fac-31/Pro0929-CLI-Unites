from __future__ import annotations
import rich_click as click
from ..core.output import print_success
from ..core.config import ConfigManager


@click.command(name="logout")
def logout() -> None:
    config = ConfigManager()
    config.update(
        {
            "auth_token": None,
            "refresh_token": None,
            "session_expires_at": None,
            "current_user_id": None,
        }
    )
    print_success("Successfully logged out and cleared authentication tokens.")
