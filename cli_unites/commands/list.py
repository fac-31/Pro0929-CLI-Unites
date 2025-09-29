from __future__ import annotations

import click

from ..core import console, print_warning, render_notes_table
from ..core.config import ConfigManager
from ..core.db import get_connection
from ..models.note import Note


@click.command(name="list")
@click.option("-t", "--tag", help="Filter notes by tag")
@click.option("-n", "--limit", type=int, help="Limit the number of notes shown")
@click.option("--team", help="Show notes for a specific team id")
def list_notes(tag: str | None, limit: int | None, team: str | None) -> None:
    """List stored notes."""
    team_id = team or ConfigManager().get("team_id")
    with get_connection() as db:
        rows = db.list_notes(limit=limit, tag=tag, team_id=team_id)
    if not rows:
        print_warning("No notes found.")
        return
    notes = [Note.from_row(row) for row in rows]
    console.print(render_notes_table(notes))
