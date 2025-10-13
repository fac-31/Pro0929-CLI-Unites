from __future__ import annotations

import click

from ..core import console, print_warning, render_notes_table
from ..core.config import ConfigManager
from ..core.db import get_connection
from ..models.note import Note


@click.command(name="search")
@click.argument("query")
@click.option("--all-teams", is_flag=True, help="Search across all teams")
def search(query: str, all_teams: bool) -> None:
    """Search notes by keyword."""
    team_id = None
    if not all_teams:
        team_id = ConfigManager().get("team_id")

    with get_connection() as db:
        rows = db.search_notes(query, team_id=team_id)
    if not rows:
        print_warning("No matches found.")
        return
    notes = [Note.from_row(row) for row in rows]
    console.print(render_notes_table(notes))
