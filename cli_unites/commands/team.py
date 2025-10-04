from __future__ import annotations

import click

from ..core import print_success, print_warning
from ..core.config import ConfigManager


@click.command(name="team")
@click.option("--set", "team_id", help="Set the default team identifier")
def team(team_id: str | None) -> None:
    """Display or update the default team id."""
    manager = ConfigManager()
    if team_id:
        manager.set("team_id", team_id)
        print_success(f"Team id set to {team_id}")
        return
    value = manager.get("team_id")
    if value:
        print_success(f"Current team id: {value}")
    else:
        print_warning("No team configured.")
