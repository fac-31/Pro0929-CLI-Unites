from __future__ import annotations

import click

from ..core.db import get_connection
from ..models.note import Note


@click.command(name="search")
@click.argument("query")
def search(query: str) -> None:
    """Search notes by keyword."""
    with get_connection() as db:
        rows = db.search_notes(query)
    if not rows:
        click.echo("No matches found.")
        return
    for row in rows:
        note = Note.from_row(row)
        click.echo(note.to_cli_output())
        click.echo("-")
