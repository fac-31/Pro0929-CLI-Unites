from __future__ import annotations

import click

from ..core.onboarding import launch_guided_tour


@click.command(name="onboarding")
def onboarding() -> None:
    """Launch the interactive onboarding tour."""
    launch_guided_tour()
