"""CLI entrypoint for cli-unites."""
from __future__ import annotations

import rich_click as click
from rich_click import rich_click

from .commands import register
from .core.onboarding import run_onboarding

rich_click.TEXT_MARKUP = True
rich_click.MAX_WIDTH = 100
rich_click.STYLE_HELPTEXT = "dim"
rich_click.STYLE_HEADER_TEXT = "bold cyan"
rich_click.GROUP_ARGUMENTS_OPTIONS = True
rich_click.SHOW_ARGUMENTS = True
rich_click.OPTIONS_TABLE_COLUMN_TYPES = ["required", "opt_long", "help"]


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option()
def cli() -> None:
    """Unite your team with query-able project notes.

    **Popular commands**

    • `notes add "Title" --body "What happened"`
    • `notes list --tag release`
    • `notes search "keyword"`
    """
    run_onboarding()


register(cli)
