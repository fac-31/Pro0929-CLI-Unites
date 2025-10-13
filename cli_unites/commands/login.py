from __future__ import annotations
import rich_click as click
from ..core.auth import handle_login_flow


@click.command(name="login")
def login() -> None:
    """Login with your github account."""
    handle_login_flow()
