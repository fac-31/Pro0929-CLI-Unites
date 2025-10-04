"""CLI entrypoint for cli-unites."""
from __future__ import annotations

import click

from .commands import register


@click.group()
@click.version_option()
def cli() -> None:
    "Unite your team with query-able project notes."


register(cli)
