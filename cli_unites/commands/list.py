from __future__ import annotations

import click

from ..core import console, print_warning, render_notes_table
from ..core.db import get_connection
from ..models.note import Note


@click.command(name="list")
@click.option("-t", "--tag", help="Filter notes by tag")
@click.option("-n", "--limit", type=int, help="Limit the number of notes shown")
def list_notes(tag: str | None, limit: int | None) -> None:
    """List stored notes."""
    with get_connection() as db:
        rows = db.list_notes(limit=limit, tag=tag)
    if not rows:
        print_warning("No notes found.")
        return
    notes = [Note.from_row(row) for row in rows]
    console.print(render_notes_table(notes))
