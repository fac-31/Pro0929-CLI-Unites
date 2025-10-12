"""CLI command registrations."""

from __future__ import annotations

from typing import Iterable

from click import Group

from .activity import activity
from .add import add
from .auth import auth
from .help import help_command
from .list import list_notes
from .onboarding import onboarding
from .search import search
from .team import team
from .login import login
from .logout import logout  
from .realtime import realtime

COMMANDS = (
    add,
    auth,
    list_notes,
    search,
    team, 
    realtime,
    help_command,
    activity,
    onboarding,
    login,
    logout,
)    


def register(group: Group, commands: Iterable = COMMANDS) -> None:
    for command in commands:
        group.add_command(command)


__all__ = ["register"]
