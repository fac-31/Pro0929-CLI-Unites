from __future__ import annotations

import os
import sys
from typing import Iterable

import click

from ..core import (
    console,
    print_error,
    print_success,
    print_warning,
    render_note_panel,
    render_status_panel,
)
from ..core.config import ConfigManager
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
        console.print("[note.meta]No body supplied. Let's capture it now.[/note.meta]")
        editor_cmd = next(
            (os.environ.get(var) for var in ("CLICK_EDITOR", "VISUAL", "EDITOR") if os.environ.get(var)),
            None,
        )
        use_editor = False
        if editor_cmd:
            use_editor = click.confirm(
                f"Open {editor_cmd} to write the note?", default=True
            )
        if use_editor:
            template = "# Write your note below. Lines starting with # are ignored.\n"
            edited = click.edit(template)
            if edited is None:
                raise click.Abort()
            content = "\n".join(line for line in edited.splitlines() if not line.startswith("#")).strip()
        else:
            content = click.prompt("Note body", default="", show_default=False)
    else:
        content = sys.stdin.read().strip()

    if not content and not allow_empty:
        print_error("No note content provided.")
        print_warning("Add text with --body, pipe content, or confirm using --allow-empty.")
        raise click.Abort()

    manager = ConfigManager()
    config = manager.as_dict()
    current_team = config.get("team_id")

    git_context = get_git_context()
    with get_connection() as db:
        note_id = db.add_note(
            title=title,
            body=content,
            tags=tags,
            git_commit=git_context.get("commit"),
            git_branch=git_context.get("branch"),
            project_path=git_context.get("root"),
            team_id=current_team,
        )
        stored = db.get_note(note_id)
    note = Note.from_row(stored) if stored else None

    print_success(f"Saved note {note_id} for {note.title if note else title}.")
    if note is not None:
        console.print(render_note_panel(note))

    status_lines = ["[success]Saved locally[/success]"]
    if config.get("supabase_url") and config.get("supabase_key"):
        status_lines.append("[success]Supabase sync configured[/success]")
    else:
        status_lines.append(
            "[warning]Sync not configured. Run `notes auth --supabase-url ... --supabase-key ...`[/warning]"
        )

    context_bits = []
    if config.get("team_id"):
        context_bits.append(f"Team: [note.title]{config['team_id']}[/note.title]")
    if git_context.get("branch"):
        context_bits.append(f"Branch: {git_context['branch']}")
    if git_context.get("commit"):
        context_bits.append(f"Commit: {git_context['commit'][:7]}")

    console.print(render_status_panel(status_lines, context_bits))
