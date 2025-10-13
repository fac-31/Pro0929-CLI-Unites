"""CLI entrypoint for cli-unites."""
from __future__ import annotations


import sys
import rich_click as click
from rich_click import rich_click
from dotenv import load_dotenv, find_dotenv

from .commands import register
from .core.onboarding import run_onboarding
from .core.output import ACCENT, SUBDUED, set_fullscreen_background

# Load environment variables from .env file (searches up directory tree)
load_dotenv(find_dotenv(usecwd=True))

rich_click.TEXT_MARKUP = True
rich_click.MAX_WIDTH = 100
rich_click.STYLE_HELPTEXT = SUBDUED
rich_click.STYLE_HEADER_TEXT = f"bold {ACCENT}"
rich_click.GROUP_ARGUMENTS_OPTIONS = True
rich_click.SHOW_ARGUMENTS = True
rich_click.OPTIONS_TABLE_COLUMN_TYPES = ["required", "opt_long", "help"]

# Track if we're in fullscreen mode
_FULLSCREEN_ENABLED = False

# Set up fullscreen mode immediately if interactive and no --no-fullscreen flag
if sys.stdout.isatty() and "--no-fullscreen" not in sys.argv:
    sys.stderr.write("DEBUG: Module-level fullscreen setup\n")
    sys.stderr.flush()
    set_fullscreen_background()

    _FULLSCREEN_ENABLED = True


def _exit_fullscreen():
    """Reset terminal when exiting."""
    if _FULLSCREEN_ENABLED and sys.stdout.isatty():
        # Reset background color but DON'T clear screen
        sys.stdout.write("\033[0m")
        sys.stdout.flush()


import atexit
atexit.register(_exit_fullscreen)


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
