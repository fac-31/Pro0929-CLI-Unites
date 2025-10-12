"""CLI command registrations."""
from __future__ import annotations

from typing import Iterable

from click import Group

from .activity import activity
from .add import add
from .auth import auth
from .help import help_command
from .list import list_notes
from .search import search
from .team import team

COMMANDS = (add, auth, list_notes, search, team, help_command, activity)


def register(group: Group, commands: Iterable = COMMANDS) -> None:
    for command in commands:
        group.add_command(command)


__all__ = ["register"]
