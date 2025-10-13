from __future__ import annotations

import rich_click as click
from rich.panel import Panel

from ..core import console

HELP_CONTENT = """[bold]cli-unites quick start[/bold]

Run `notes --help` to see all available commands.

For first-time setup and onboarding, please refer to the onboarding guide.

"""


@click.command(name="help")
@click.argument("topic", required=False)
def help_command(topic: str | None) -> None:
    """Show usage tips and quick links."""
    console.print(Panel.fit(HELP_CONTENT, border_style="cyan"))
