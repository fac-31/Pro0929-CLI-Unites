"""Rich console helpers for consistent CLI styling."""
from __future__ import annotations

from datetime import datetime
from typing import Sequence

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme
from rich.markup import escape

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


def print_error(message: str) -> None:
    console.print(f"[error]✗ {message}")


def render_note_panel(note: Note) -> Panel:
    created = _format_timestamp(note.created_at)
    tags = ", ".join(note.tags) if note.tags else "—"
    team = note.team_id or "—"
    git = f"{note.git_branch} @ {note.git_commit[:7]}" if note.git_commit and note.git_branch else ""

    lines = [
        f"[note.meta]Title:[/] {escape(note.title)}",
        f"[note.meta]Team:[/] {escape(team)}",
        f"[note.meta]Created:[/] {escape(created)}",
        f"[note.meta]Tags:[/] {escape(tags)}",
    ]
    if git:
        lines.append(f"[note.meta]Git:[/] {escape(git)}")

    lines.extend([
        "",
        "[note.meta]Summary:[/]",
        escape(note.body.strip() or "(empty)")
    ])

    content = "\n".join(lines)
    return Panel.fit(content, border_style="note.title", title="note")


def render_notes_table(
    notes: Sequence[Note],
    show_index: bool = False,
    include_team: bool = True,
    include_summary: bool = False,
) -> Table:
    table = Table(box=None, highlight=True)
    if show_index:
        table.add_column("#", style="note.meta", no_wrap=True, justify="right")
    table.add_column("ID", style="note.id", no_wrap=True)
    table.add_column("Title", style="note.title")
    if include_summary:
        table.add_column("Summary", style="note.meta")
    table.add_column("Tags", style="note.tag")
    if include_team:
        table.add_column("Team", style="note.meta", no_wrap=True)
    table.add_column("Created", style="note.meta", no_wrap=True)
    table.add_column("Git", style="note.meta")

    for idx, note in enumerate(notes, start=1):
        created = _format_timestamp(note.created_at)
        tags = ", ".join(note.tags) if note.tags else "—"
        team = note.team_id or "—"
        git = f"{note.git_branch} @ {note.git_commit[:7]}" if note.git_commit and note.git_branch else ""
        summary = _summarise(note) if include_summary else None

        row: list[str] = []
        if show_index:
            row.append(str(idx))
        row.extend([note.id[:8], note.title])
        if include_summary and summary is not None:
            row.append(summary)
        row.append(tags)
        if include_team:
            row.append(team)
        row.extend([created, git])
        table.add_row(*row)

    return table


def _format_timestamp(value: datetime) -> str:
    if not isinstance(value, datetime):
        return ""
    if value.tzinfo is None:
        return value.strftime("%Y-%m-%d %H:%M")
    return value.astimezone().strftime("%Y-%m-%d %H:%M")


def _summarise(note: Note) -> str:
    text = note.body.strip()
    if not text:
        return "—"
    first_line = text.splitlines()[0].strip()
    if len(first_line) <= 80:
        return first_line
    return f"{first_line[:77]}…"


def render_status_panel(status_lines: Sequence[str], context_lines: Sequence[str] | None = None) -> Panel:
    body_lines = list(status_lines)
    if context_lines:
        body_lines.append("")
        body_lines.extend(context_lines)
    body = "\n".join(body_lines)
    return Panel.fit(body, border_style="note.title", title="status")
