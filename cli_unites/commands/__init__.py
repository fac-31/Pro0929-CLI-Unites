"""CLI command registrations."""

from __future__ import annotations

from typing import Iterable

from click import Group

from .add import add
from .auth import auth
from .help import help_command
from .list import list_notes
from .onboarding import onboarding
from .semantic_search import semantic_search
from .team import team
from .login import login
from .logout import logout  
from .realtime import realtime
from .email import email_group

COMMANDS = (
    add,
    auth,
    list_notes,
    semantic_search,
    team,
    email_group,
    realtime,
    help_command,
    onboarding,
    login,
    logout,
)    


def register(group: Group, commands: Iterable = COMMANDS) -> None:
    for command in commands:
        group.add_command(command)


__all__ = ["register"]
