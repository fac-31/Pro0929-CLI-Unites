from __future__ import annotations

import sys
from typing import Iterable

import click

from ..core import print_success, render_note_panel, console
from ..core.db import get_connection
from ..core.git import get_git_context
from ..models.note import Note


@click.command(name="add")
@click.argument("title")
@click.option("--body", "body", help="Body for the note. Read from stdin when omitted.")
@click.option("--allow-empty", is_flag=True, help="Permit saving an empty note body.")
@click.option("-t", "--tag", "tags", multiple=True, help="Attach one or more tags to the note.")
def add(title: str, body: str | None, allow_empty: bool, tags: Iterable[str]) -> None:
    """Add a note to the local knowledge base."""
    content: str
    if body is not None:
        content = body
    elif sys.stdin.isatty():
        # No body flag and no piped stdin – avoid waiting on user input.
        content = ""
    else:
        content = sys.stdin.read().strip()

    if not content and not allow_empty:
        raise click.UsageError(
            "No note content provided. Use --body, pipe text into the command, or pass --allow-empty."
        )

    git_context = get_git_context()
    with get_connection() as db:
        note_id = db.add_note(
            title=title,
            body=content,
            tags=tags,
            git_commit=git_context.get("commit"),
            git_branch=git_context.get("branch"),
            project_path=git_context.get("root"),
        )
        stored = db.get_note(note_id)
    note = Note.from_row(stored) if stored else None

    print_success(f"Saved note {note_id} for {note.title if note else title}.")
    if note is not None:
        console.print(render_note_panel(note))
