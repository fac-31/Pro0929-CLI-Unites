from __future__ import annotations

import click

from ..core import console, print_warning, render_notes_table
from ..core.config import ConfigManager
from ..core.db import get_connection
from ..models.note import Note


@click.command(name="activity")
@click.option("--team", help="Show activity for a specific team id")
@click.option("-n", "--limit", type=int, default=5, show_default=True, help="Number of notes to show")
def activity(team: str | None, limit: int) -> None:
    """Show recent notes for the current or selected team."""
    manager = ConfigManager()
    config = manager.as_dict()
    team_id = team or config.get("team_id")

    with get_connection() as db:
        rows = db.list_notes(limit=limit, team_id=team_id)

        if not rows and team_id:
            print_warning(f"No notes found for team {team_id}.")
            return
        if not rows:
            rows = db.list_notes(limit=limit)
            if not rows:
                print_warning("No notes recorded yet. Run `notes add` to create one.")
                return
            print_warning("No team set; showing recent notes across all teams.")

        notes = [Note.from_row(row) for row in rows]
    console.print(render_notes_table(notes))
