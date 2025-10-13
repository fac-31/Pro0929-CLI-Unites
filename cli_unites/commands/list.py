from __future__ import annotations

import sys

import click


from ..core import console, print_warning, render_note_panel, render_notes_table, fullscreen_display
from ..core.config import ConfigManager
from ..core.db import get_connection
from ..models.note import Note


@click.command(name="list")
@click.option("-t", "--tag", help="Filter notes by tag")
@click.option("-n", "--limit", type=int, help="Limit the number of notes shown")
@click.option("--team", help="Show notes for a specific team id")
@click.option("--fullscreen", is_flag=True, help="Display in fullscreen mode")
def list_notes(tag: str | None, limit: int | None, team: str | None, fullscreen: bool = False) -> None:
    """List stored notes."""
    manager = ConfigManager()
    team_identifier = team or manager.get_current_team()
    with get_connection() as db:
        rows = db.list_notes(limit=limit, tag=tag, team_id=team_identifier)
    if not rows:
        print_warning("No notes found.")
        return
    if not team_identifier:
        print_warning("No team selected; showing recent notes across all teams. Use `notes team switch` to scope results.")
    notes = [Note.from_row(row) for row in rows]
    
    table = render_notes_table(
        notes,
        show_index=True,
        include_team=False,
        include_summary=True,
    )
    
    if fullscreen:
        fullscreen_display(table, title=f"notes ({len(notes)} found)")
        return
    
    console.print(table)

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
