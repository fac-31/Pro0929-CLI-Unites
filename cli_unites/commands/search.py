from __future__ import annotations

import rich_click as click

from ..core import console, print_warning, display_notes_list
from ..core.config import ConfigManager
from ..core.db import get_connection
from ..models.note import Note


@click.command(name="search")
@click.argument("query")
@click.option("--all-teams", is_flag=True, help="Search across all teams")
def search(query: str, all_teams: bool) -> None:
    """Search notes by keyword."""
    manager = ConfigManager()
    team_identifier = None if all_teams else manager.get_current_team()

    with get_connection() as db:
        rows = db.search_notes(query, team_id=team_identifier)
    if not rows:
        print_warning("No matches found.")
        return
    notes = [Note.from_row(row) for row in rows]
    display_notes_list(notes)
