from __future__ import annotations

import click

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
        click.echo("No notes found.")
        return
    for row in rows:
        note = Note.from_row(row)
        click.echo(note.to_cli_output())
        click.echo("-")
