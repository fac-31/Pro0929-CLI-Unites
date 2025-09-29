from __future__ import annotations

import click

from ..core import print_success, print_warning
from ..core.config import ConfigManager


@click.command(name="team")
@click.option("--set", "team_id", help="Set the default team identifier")
@click.option("--recent", is_flag=True, help="Show recently used team ids")
def team(team_id: str | None, recent: bool) -> None:
    """Display or update the default team id."""
    manager = ConfigManager()
    if team_id:
        manager.set("team_id", team_id)
        print_success(f"Team id set to {team_id}")
        return
    if recent:
        history = manager.get("team_history") or []
        if history:
            for idx, value in enumerate(history, start=1):
                print_success(f"{idx}. {value}")
        else:
            print_warning("No previously used teams yet.")
        return
    value = manager.get("team_id")
    if value:
        print_success(f"Current team id: {value}")
    else:
        print_warning("No team configured.")
