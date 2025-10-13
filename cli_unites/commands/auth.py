from __future__ import annotations

import click

from ..core import console, print_warning, render_status_panel
from ..core.config import ConfigManager


def truncate_token(token: str | None, length: int = 12) -> str | None:
    if not token:
        return None
    return token[:length] + "..." if len(token) > length else token


@click.command(name="auth")
@click.option("--token", help="CLI auth token")
@click.option("--team-id", help="Default team identifier")
@click.option("--supabase-url", help="Supabase project URL")
@click.option("--supabase-key", help="Supabase service role key")
@click.option(
    "--supabase-realtime-url",
    help="Override the Supabase Realtime websocket URL (defaults to derived wss endpoint)",
)
@click.option(
    "--supabase-realtime-channel",
    help="Default Realtime channel, e.g. realtime:public:messages (falls back to SUPABASE_REALTIME_CHANNEL)",
)
@click.option("--supabase-note-table", help="Supabase table name used for note updates (default notes)")
@click.option("--supabase-message-table", help="Supabase table name used for direct messages (default messages)")
@click.option(
    "--show", is_flag=True, help="Show the currently stored auth configuration"
)
def auth(
    token: str | None,
    team_id: str | None,
    supabase_url: str | None,
    supabase_key: str | None,
    supabase_realtime_url: str | None,
    supabase_realtime_channel: str | None,
    supabase_note_table: str | None,
    supabase_message_table: str | None,
    show: bool,
) -> None:
    """Manage authentication details."""
    manager = ConfigManager()
    updates = {}

    if token:
        updates["auth_token"] = token
    if team_id:
        updates["team_id"] = team_id
    if supabase_url:
        updates["supabase_url"] = supabase_url
    if supabase_key:
        updates["supabase_key"] = supabase_key
    if supabase_realtime_url:
        updates["supabase_realtime_url"] = supabase_realtime_url
    if supabase_realtime_channel:
        updates["supabase_realtime_channel"] = supabase_realtime_channel
    if supabase_note_table:
        updates["supabase_note_table"] = supabase_note_table
    if supabase_message_table:
        updates["supabase_message_table"] = supabase_message_table

    if updates:
        manager.update(updates)
        console.print(
            render_status_panel(
                ["[success]Updated authentication configuration[/success]"],
                [f"Updated fields: {', '.join(updates.keys())}"],
            )
        )

    if show or not updates:
        config = manager.as_dict()
        sanitized = {
            **config,
            "auth_token": truncate_token(config.get("auth_token")),
            "supabase_key": "***" if config.get("supabase_key") else None,
        }

        if not sanitized.get("auth_token"):
            print_warning("No authentication details stored.")

        lines = [f"{k}: {v}" for k, v in sanitized.items() if v is not None]
        console.print(
            render_status_panel(
                ["[bold]Current Authentication Configuration[/bold]"], lines
            )
        )
