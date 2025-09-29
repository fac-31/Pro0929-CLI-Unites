from __future__ import annotations

import click

from ..core.config import ConfigManager


@click.command(name="auth")
@click.option("--token", help="CLI auth token")
@click.option("--team-id", help="Default team identifier")
@click.option("--supabase-url", help="Supabase project URL")
@click.option("--supabase-key", help="Supabase service role key")
@click.option("--show", is_flag=True, help="Show the currently stored auth configuration")
def auth(
    token: str | None,
    team_id: str | None,
    supabase_url: str | None,
    supabase_key: str | None,
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

    if updates:
        manager.update(updates)
        click.echo("Updated authentication configuration.")

    if show or not updates:
        config = manager.as_dict()
        sanitized = {**config, "supabase_key": "***" if config.get("supabase_key") else None}
        click.echo(sanitized)
