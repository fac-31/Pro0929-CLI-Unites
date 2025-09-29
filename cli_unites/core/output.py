"""Rich console helpers for consistent CLI styling."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable, Sequence

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from ..models.note import Note

_THEME = Theme(
    {
        "success": "bold green",
        "warning": "yellow",
        "error": "bold red",
        "note.title": "bold cyan",
        "note.meta": "dim",
        "note.id": "magenta",
        "note.tag": "green",
    }
)

console = Console(theme=_THEME)


def print_success(message: str) -> None:
    console.print(f"[success]✓ {message}")


def print_warning(message: str) -> None:
    console.print(f"[warning]! {message}")


def render_note_panel(note: Note) -> Panel:
    meta_bits: list[str] = []
    if note.tags:
        meta_bits.append(f"[note.tag]{', '.join(note.tags)}[/]")
    if note.git_commit and note.git_branch:
        meta_bits.append(f"{note.git_branch} · {note.git_commit[:7]}")
    if note.project_path:
        meta_bits.append(note.project_path)
    subtitle = " | ".join(meta_bits) if meta_bits else ""
    body = Text(note.body.rstrip() or "(empty)")
    return Panel(body, title=f"[note.title]{note.title}", subtitle=subtitle)


def render_notes_table(notes: Sequence[Note]) -> Table:
    table = Table(box=None, highlight=True)
    table.add_column("ID", style="note.id", no_wrap=True)
    table.add_column("Title", style="note.title")
    table.add_column("Tags", style="note.tag")
    table.add_column("Created", style="note.meta", no_wrap=True)
    table.add_column("Git", style="note.meta")

    for note in notes:
        created = ""
        if isinstance(note.created_at, datetime):
            dt = note.created_at
            if dt.tzinfo is None:
                created = dt.strftime("%Y-%m-%d %H:%M")
            else:
                created = dt.astimezone().strftime("%Y-%m-%d %H:%M")
        tags = ", ".join(note.tags) if note.tags else "—"
        git = f"{note.git_branch} @ {note.git_commit[:7]}" if note.git_commit and note.git_branch else ""
        table.add_row(note.id[:8], note.title, tags, created, git)

    return table
