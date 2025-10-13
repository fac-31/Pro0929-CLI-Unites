from __future__ import annotations

import click

from ..core import console, print_warning, display_note_view
from ..core.db import get_connection
from ..models.note import Note


@click.command(name="semantic-search")
@click.argument("query")
@click.option("--limit", "-l", default=10, help="Maximum number of results to return")
def semantic_search(query: str, limit: int) -> None:
    """Search notes using semantic similarity (AI-powered)."""
    with get_connection() as db:
        rows = db.semantic_search(query, limit=limit)

    if not rows:
        print_warning("No matches found.")
        return

    # Display results with similarity scores
    notes = [Note.from_row(row) for row in rows]
    
    console.print(f"\nFound [bold]{len(notes)}[/] matching notes:")

    for note, row in zip(notes, rows):
        display_note_view(note)
