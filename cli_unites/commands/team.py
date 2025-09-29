from __future__ import annotations

import click

from ..core.config import ConfigManager


@click.command(name="team")
@click.option("--set", "team_id", help="Set the default team identifier")
def team(team_id: str | None) -> None:
    """Display or update the default team id."""
    manager = ConfigManager()
    if team_id:
        manager.set("team_id", team_id)
        click.echo(f"Team id set to {team_id}")
        return
    value = manager.get("team_id")
    if value:
        click.echo(f"Current team id: {value}")
    else:
        click.echo("No team configured.")
