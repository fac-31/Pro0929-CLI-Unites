from __future__ import annotations

import os

from .config import ConfigManager
from .db import Database, get_connection
from .output import console, render_status_panel

SAMPLE_NOTES = [
    {
        "title": "Welcome to cli-unites",
        "body": (
            "Use `notes add` to capture learnings and decisions. Share them with your team for fast onboarding."
        ),
        "tags": ["onboarding", "tips"],
    },
    {
        "title": "Try searching",
        "body": "Run `notes search \"git\"` to recall previous debugging sessions.",
        "tags": ["search"],
    },
]


def run_onboarding() -> None:
    if os.environ.get("CLI_UNITES_SKIP_ONBOARDING") == "1":
        return

    manager = ConfigManager()
    if manager.get("first_run_completed"):
        return

    with get_connection() as db:
        if db.list_notes(limit=1):
            manager.set("first_run_completed", True)
            return

        for note in SAMPLE_NOTES:
            db.add_note(
                title=note["title"],
                body=note["body"],
                tags=note["tags"],
                team_id=manager.get("team_id"),
            )

    manager.set("first_run_completed", True)
    status_lines = [
        "[success]Sample workspace ready[/success]",
        "Capture your own note with `notes add \"First win\" --body \"What we shipped\"`",
    ]
    context_lines = []
    if manager.get("team_id"):
        context_lines.append(f"Team: {manager.get('team_id')}")
    console.print(render_status_panel(status_lines, context_lines))
