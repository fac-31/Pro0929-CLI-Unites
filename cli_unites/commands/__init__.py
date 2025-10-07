"""CLI command registrations."""
from __future__ import annotations

from typing import Iterable

from click import Group

from .add import add
from .auth import auth
from .list import list_notes
from .search import search
from .semantic_search import semantic_search
from .team import team

COMMANDS = (add, auth, list_notes, search, semantic_search, team)


def register(group: Group, commands: Iterable = COMMANDS) -> None:
    for command in commands:
        group.add_command(command)


__all__ = ["register"]
