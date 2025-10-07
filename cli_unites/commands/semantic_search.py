from __future__ import annotations

import click

from ..core import console, print_warning, render_notes_table
from ..core.db import get_connection
from ..models.note import Note


@click.command(name="semantic-search")
@click.argument("query")
@click.option("--limit", "-l", default=10, help="Maximum number of results to return")
def semantic_search(query: str, limit: int) -> None:
    """Search notes using semantic similarity (AI-powered)."""
    with get_connection() as db:
        rows = db.semantic_search(query, limit=limit)

    if not rows:
        print_warning("No matches found.")
        return

    # Display results with similarity scores
    notes = [Note.from_row(row) for row in rows]
    console.print(render_notes_table(notes))

    # Show similarity scores
    console.print("\n[dim]Similarity scores:[/dim]")
    for row in rows:
        similarity_percent = row.get("similarity", 0) * 100
        console.print(f"  • {row['title'][:50]}: [green]{similarity_percent:.1f}%[/green]")
