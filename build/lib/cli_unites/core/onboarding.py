from __future__ import annotations

import os
import sys
import click

from .config import ConfigManager
from .db import get_connection
from .git import get_git_context
from .output import (
    console,
    print_success,
    print_warning,
    render_note_panel,
    render_notes_table,
    render_status_panel,
)
from ..models.note import Note

WELCOME_PANEL = """[bold]👋 Welcome to cli-unites[/bold]

Capture project learnings as searchable notes your whole team can query.
We will guide you through setting a team, adding your first note, and
highlight where to look things up later."""


def run_onboarding() -> None:
    if os.environ.get("CLI_UNITES_SKIP_ONBOARDING") == "1":
        return

    # Avoid interactive prompts when running in a non-interactive context.
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return

    manager = ConfigManager()
    if manager.get("first_run_completed"):
        return

    with get_connection() as db:
        has_notes = bool(db.list_notes(limit=1))
    if has_notes and not click.confirm(
        "Existing notes detected. Launch the guided tour anyway?", default=False
    ):
        manager.set("first_run_completed", True)
        return

    try:
        _guided_tour(manager)
        manager.set("first_run_completed", True)
    except (click.Abort, KeyboardInterrupt):
        console.print(
            "[warning]Onboarding aborted. You can rerun it later; start with `notes help` for tips."
        )


def _guided_tour(manager: ConfigManager) -> None:
    console.print(render_status_panel([WELCOME_PANEL], None))
    console.print()

    team_id = _ensure_team(manager)
    console.print()

    note = _capture_first_note(manager, team_id)
    console.print()

    _show_feature_highlights(manager, team_id, note)

    console.print()
    console.print(
        render_status_panel(
            [
                "[success]You're ready to work as a team![/success]",
                "Next steps: share `notes install` with teammates or connect Supabase via `notes auth`.",
            ],
            ["Run `notes help` anytime for a refresher."],
        )
    )


def _ensure_team(manager: ConfigManager) -> str | None:
    current_team = manager.get("team_id")
    console.print(
        render_status_panel(
            [
                "[bold]Step 1 · Choose your team[/bold]",
                "Notes are scoped to a team so you can share context quickly.",
            ],
            (
                [f"Current team: [note.title]{current_team}[/note.title]"]
                if current_team
                else ["No team configured yet."]
            ),
        )
    )
    console.print()

    if current_team and not click.confirm(
        f"Keep using team '{current_team}'?", default=True
    ):
        current_team = None

    if not current_team:
        team_id = click.prompt(
            "Enter a team id (e.g. awesome-squad)", default="", show_default=False
        ).strip()
        if team_id:
            manager.set("team_id", team_id)
            current_team = team_id
            print_success(f"Team set to {team_id}")
        else:
            print_warning("No team selected. You can set one later with `notes team --set`.")
    return current_team


def _capture_first_note(manager: ConfigManager, team_id: str | None) -> Note:
    console.print(
        render_status_panel(
            [
                "[bold]Step 2 · Capture your first note[/bold]",
                "We'll walk through creating a note with title, body, and tags.",
            ],
            [
                "Use the arrow keys (or y/n) to answer prompts.",
                "You can skip by pressing Ctrl+C at any time.",
                "Tip: capture notes later with `notes add \"Title\" --body \"Summary\"`.",
            ],
        )
    )

    title_default = "First win"
    title = click.prompt("Note title", default=title_default).strip()
    title = title or title_default

    console.print(
        "[dim]No editor needed—capture the key points right here in the terminal.[/dim]"
    )
    body = click.prompt(
        "Summarise the note", default="Shipped our first collaborative note."
    ).strip()

    tags_default = "onboarding,first-note"
    tag_input = click.prompt("Tags (comma separated)", default=tags_default)
    tags = [tag.strip() for tag in tag_input.split(",") if tag.strip()]

    git_context = get_git_context()
    with get_connection() as db:
        note_id = db.add_note(
            title=title,
            body=body,
            tags=tags,
            git_commit=git_context.get("commit"),
            git_branch=git_context.get("branch"),
            project_path=git_context.get("root"),
            team_id=team_id,
        )
        stored = db.get_note(note_id)
        assert stored is not None
        note = Note.from_row(stored)

    console.print()
    print_success("First note captured!")
    console.print(render_note_panel(note))

    status_lines = ["[success]Saved locally[/success]"]
    if manager.get("supabase_url") and manager.get("supabase_key"):
        status_lines.append("[success]Supabase sync configured[/success]")
    else:
        status_lines.append(
            "[warning]Sync not configured. Run `notes auth --supabase-url ... --supabase-key ...`"
        )

    context_lines = []
    if team_id:
        context_lines.append(f"Team: [note.title]{team_id}[/note.title]")
    if git_context.get("branch"):
        context_lines.append(f"Branch: {git_context['branch']}")
    if git_context.get("commit"):
        context_lines.append(f"Commit: {git_context['commit'][:7]}")

    console.print(render_status_panel(status_lines, context_lines))
    return note


def _show_feature_highlights(
    manager: ConfigManager, team_id: str | None, note: Note
) -> None:
    console.print(
        render_status_panel(
            ["[bold]Step 3 · Explore your workspace[/bold]"],
            [
                "We'll preview list, search, and team activity so you know where to look next.",
            ],
        )
    )

    with get_connection() as db:
        notes_rows = db.list_notes(limit=5, team_id=team_id)
        search_rows = db.search_notes(note.title.split()[0], team_id=team_id)
        recent_rows = db.list_notes(limit=5)

    notes = [Note.from_row(row) for row in notes_rows]
    search_notes = [Note.from_row(row) for row in search_rows]
    recent_notes = [Note.from_row(row) for row in recent_rows]

    console.print()
    console.print("[bold]notes list[/bold] — browse recent notes")
    console.print(render_notes_table(notes))
    console.print("[dim]Tip: Add `--tag release` to focus on relevant streams.[/dim]")

    if search_notes:
        console.print("[bold]notes search " + f"\"{note.title.split()[0]}\"")
        console.print(render_notes_table(search_notes))
    else:
        console.print("[warning]Search results will appear once you add more notes.")

    console.print()
    console.print("[bold]notes activity[/bold] — team timeline")
    console.print(render_notes_table(recent_notes))
    console.print(
        "[dim]Use `notes activity --team your-team` to inspect other squads or workspaces.[/dim]"
    )

    console.print()
    console.print(
        "[bold]More commands[/bold]: `notes team --recent`, `notes help`, `notes auth`, `notes search --all-teams`"
    )
