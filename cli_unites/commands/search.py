from __future__ import annotations

import click

from ..core import console, print_warning, render_notes_table
from ..core.db import get_connection
from ..models.note import Note


@click.command(name="search")
@click.argument("query")
def search(query: str) -> None:
    """Search notes by keyword."""
    with get_connection() as db:
        rows = db.search_notes(query)
    if not rows:
        print_warning("No matches found.")
        return
    notes = [Note.from_row(row) for row in rows]
    console.print(render_notes_table(notes))
