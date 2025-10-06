from __future__ import annotations

import click
from rich.panel import Panel

from ..core import console

HELP_CONTENT = """[bold]cli-unites quick start[/bold]

• [bold]Authenticate[/bold]: `notes auth --token TOKEN --team-id TEAM`
• [bold]Add notes[/bold]: `notes add "Title" --body "Details"`
• [bold]List notes[/bold]: `notes list --tag release`
• [bold]Search[/bold]: `notes search "keyword"`
• [bold]Switch team[/bold]: `notes team --set my-team`
• [bold]Team activity[/bold]: `notes activity --limit 5`

Tips:
- Omit `--body` to open an editor or pipe text from another command.
- Use `--allow-empty` when logging quick todo stubs.
- Run with `--debug` for verbose trace output when something breaks.
"""


@click.command(name="help")
@click.argument("topic", required=False)
def help_command(topic: str | None) -> None:
    """Show usage tips and quick links."""
    console.print(Panel.fit(HELP_CONTENT, border_style="cyan"))
    if topic:
        console.print(f"[dim]No detailed walkthrough for [bold]{topic}[/bold] yet. Try the README or `notes help` without a topic.[/dim]")
