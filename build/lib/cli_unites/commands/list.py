from __future__ import annotations

import sys

import click

from ..core import console, print_warning, render_note_panel, render_notes_table
from ..core.config import ConfigManager
from ..core.db import get_connection
from ..models.note import Note


@click.command(name="list")
@click.option("-t", "--tag", help="Filter notes by tag")
@click.option("-n", "--limit", type=int, help="Limit the number of notes shown")
@click.option("--team", help="Show notes for a specific team id")
def list_notes(tag: str | None, limit: int | None, team: str | None) -> None:
    """List stored notes."""
    manager = ConfigManager()
    team_id = team or manager.get("team_id")
    if not team_id:
        print_warning(
            "No team configured. Set one with `notes team --set <name>` or pass `--team`."
        )
        return
    with get_connection() as db:
        rows = db.list_notes(limit=limit, tag=tag, team_id=team_id)
    if not rows:
        print_warning("No notes found.")
        return
    notes = [Note.from_row(row) for row in rows]
    console.print(
        render_notes_table(
            notes,
            show_index=True,
            include_team=False,
            include_summary=True,
        )
    )

    if sys.stdin.isatty() and sys.stdout.isatty():
        try:
            selection = click.prompt(
                "Enter a note number to view details",
                default="",
                show_default=False,
            ).strip()
        except (click.Abort, EOFError):
            return

        if not selection:
            return

        try:
            index = int(selection)
        except ValueError:
            print_warning("Please enter a number from the list.")
            return

        if not 1 <= index <= len(notes):
            print_warning("Selection out of range.")
            return

        console.print(render_note_panel(notes[index - 1]))
