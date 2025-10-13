from __future__ import annotations

import json
import functools
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import rich_click as click
from rich import box
from rich.table import Table

from ..core import console, print_error, print_success, print_warning
from ..core.auth import get_auth_manager
from ..core.config import ConfigManager
from ..core.db import (
    AuthorizationError,
    Database,
    DuplicateResourceError,
    TeamServiceUnavailable,
    get_connection,
)


def _format_timestamp(timestamp: Optional[str]) -> str:
    if not timestamp:
        return "-"
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return timestamp


def _resolve_team(
    db: Database,
    config: ConfigManager,
    identifier: Optional[str],
    *,
    required: bool = True,
) -> Optional[Dict[str, Any]]:
    candidate = identifier or config.get_current_team()
    if not candidate:
        if required:
            print_warning("No team selected. Use `notes team switch <team>` first.")
        return None

    team = db.get_team(candidate)
    if team:
        return team

    if required:
        print_error(f"Could not find a team matching '{candidate}'.")
    return None


def _handle_db_errors(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DuplicateResourceError as exc:
            print_error(str(exc))
        except AuthorizationError as exc:
            print_error(str(exc))
        except TeamServiceUnavailable as exc:
            print_error(str(exc))
        except Exception as exc:  # pragma: no cover - defensive
            print_error(f"Unexpected error: {exc}")

    return wrapper


def _render_team_table(teams: List[Dict[str, Any]], current_team_id: Optional[str]) -> None:
    table = Table(title="Your Teams", box=box.SIMPLE_HEAVY)
    table.add_column("Current", justify="center")
    table.add_column("Name", overflow="fold")
    table.add_column("Role", justify="center")
    table.add_column("Slug")
    table.add_column("Team ID", overflow="fold")

    for entry in teams:
        team = entry["team"]
        indicator = "•" if team["id"] == current_team_id else ""
        table.add_row(
            indicator,
            team.get("name", ""),
            entry.get("role", "member"),
            team.get("slug", ""),
            team["id"],
        )

    console.print(table)


def _render_members_table(members: List[Dict[str, Any]]) -> None:
    table = Table(title="Team Members", box=box.SIMPLE_HEAVY)
    table.add_column("Role", justify="center")
    table.add_column("Email", overflow="fold")
    table.add_column("Name", overflow="fold")
    table.add_column("Joined")

    for member in members:
        table.add_row(
            member.get("role", "member"),
            member.get("email") or "-",
            member.get("full_name") or "-",
            _format_timestamp(member.get("joined_at")),
        )

    console.print(table)


@click.group(invoke_without_command=True)
@click.option("--set", "legacy_set", help="Set the default team identifier (legacy option).")
@click.option("--recent", "legacy_recent", is_flag=True, help="Show recently used team identifiers (legacy option).")
@click.pass_context
def team(ctx: click.Context, legacy_set: Optional[str], legacy_recent: bool) -> None:
    """Manage teams."""
    if ctx.invoked_subcommand:
        if legacy_set or legacy_recent:
            print_warning("Ignoring legacy team options when using subcommands.")
        return

    manager = ConfigManager()

    if legacy_set:
        manager.set_current_team(legacy_set)
        print_success(f"Team id set to {legacy_set}")
        return

    if legacy_recent:
        history = manager.get_recent_teams()
        if history:
            for idx, entry in enumerate(history, start=1):
                team_id = entry.get("id") or "-"
                name = entry.get("name") or team_id
                print_success(f"{idx}. {name} ({team_id})")
        else:
            print_warning("No previously used teams yet.")
        return

    current = manager.get_current_team()
    if current:
        print_success(f"Current team id: {current}")
    else:
        print_warning("No team configured.")


@team.command("create")
@click.argument("name")
@click.option("--description", "-d", help="Optional description for the team.")
@_handle_db_errors
def create_team(name: str, description: Optional[str]) -> None:
    """Create a new team and switch to it."""
    with get_connection() as db:
        team_id = db.create_team(name, description=description)
        team = db.get_team(team_id) or {"id": team_id, "name": name}

    config = ConfigManager()
    config.set_current_team(team["id"], team.get("name"))

    print_success(f"Created team '{team.get('name')}' (id: {team['id']}).")
    print_success("You are now switched to this team.")


@team.command("list")
@click.option("--json", "json_output", is_flag=True, help="Emit raw JSON.")
@_handle_db_errors
def list_teams(json_output: bool) -> None:
    """List teams you belong to."""
    with get_connection() as db:
        teams = db.list_user_teams()

    if not teams:
        print_warning("You are not a member of any teams yet.")
        return

    if json_output:
        click.echo(json.dumps(teams, indent=2))
        return

    current_team_id = ConfigManager().get_current_team()
    _render_team_table(teams, current_team_id)


@team.command("show")
@click.argument("team_identifier", required=False)
@click.option("--json", "json_output", is_flag=True, help="Emit raw JSON.")
@_handle_db_errors
def show_team(team_identifier: Optional[str], json_output: bool) -> None:
    """Display details about a team."""
    config = ConfigManager()
    with get_connection() as db:
        team = _resolve_team(db, config, team_identifier)
        if not team:
            return

        if json_output:
            click.echo(json.dumps(team, indent=2))
            return

        console.print(f"[bold]{team['name']}[/bold] ({team['id']})")
        console.print(f"Slug: {team.get('slug') or '-'}")
        console.print(f"Description: {team.get('description') or '-'}")
        console.print(f"Members: {team.get('member_count') or '?'}")
        console.print(f"Created: {_format_timestamp(team.get('created_at'))}")
        console.print(f"Updated: {_format_timestamp(team.get('updated_at'))}")


@team.command("update")
@click.argument("team_identifier", required=False)
@click.option("--name", help="New team name.")
@click.option("--description", help="New description.")
@click.option("--slug", help="Override team slug.")
@_handle_db_errors
def update_team(team_identifier: Optional[str], name: Optional[str], description: Optional[str], slug: Optional[str]) -> None:
    """Update team metadata."""
    if not any([name, description, slug]):
        print_warning("Nothing to update. Provide at least one option (name, description, slug).")
        return

    config = ConfigManager()
    with get_connection() as db:
        team = _resolve_team(db, config, team_identifier)
        if not team:
            return

        updates: Dict[str, Any] = {}
        if name:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if slug:
            updates["slug"] = slug

        changed = db.update_team(team["id"], **updates)
        if not changed:
            print_warning("No changes applied.")
            return

        updated_team = db.get_team(team["id"]) or team

    config.set_current_team(updated_team["id"], updated_team.get("name"))
    print_success(f"Updated team '{updated_team.get('name')}'.")


@team.command("delete")
@click.argument("team_identifier", required=False)
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt.")
@_handle_db_errors
def delete_team(team_identifier: Optional[str], confirm: bool) -> None:
    """Delete a team. Owners only."""
    config = ConfigManager()
    with get_connection() as db:
        team = _resolve_team(db, config, team_identifier)
        if not team:
            return

        if not confirm and not click.confirm(f"Delete team '{team['name']}'? This cannot be undone.", default=False):
            print_warning("Aborted.")
            return

        db.delete_team(team["id"])

    if config.get_current_team() == team["id"]:
        config.set_current_team(None)

    print_success(f"Deleted team '{team['name']}'.")


@team.command("switch")
@click.argument("team_identifier")
@_handle_db_errors
def switch_team(team_identifier: str) -> None:
    """Switch CLI context to the given team."""
    config = ConfigManager()
    with get_connection() as db:
        team = db.get_team(team_identifier)
        if not team:
            print_error(f"No team found for '{team_identifier}'.")
            return

    config.set_current_team(team["id"], team.get("name"))
    print_success(f"Now working in team '{team.get('name')}'.")


@team.command("current")
def current_team() -> None:
    """Show the current team context."""
    config = ConfigManager()
    current = config.get_current_team()
    if not current:
        print_warning("No current team. Use `notes team switch` to pick one.")
        return

    with get_connection() as db:
        team = db.get_team(current)
        if not team:
            print_warning("Current team not found. It may have been deleted.")
            return

    print_success(f"Current team: {team['name']} ({team['id']})")


@team.command("recent")
def recent_teams() -> None:
    """Show recently used teams."""
    config = ConfigManager()
    recent = config.get_recent_teams()
    if not recent:
        print_warning("No recent teams yet.")
        return

    table = Table(title="Recent Teams", box=box.SIMPLE_HEAVY)
    table.add_column("Name", overflow="fold")
    table.add_column("Team ID", overflow="fold")
    table.add_column("Last switched")

    for entry in recent:
        table.add_row(entry.get("name") or "-", entry.get("id") or "-", _format_timestamp(entry.get("switched_at")))

    console.print(table)


@team.command("members")
@click.argument("team_identifier", required=False)
@_handle_db_errors
def team_members(team_identifier: Optional[str]) -> None:
    """List members of a team."""
    config = ConfigManager()
    with get_connection() as db:
        team = _resolve_team(db, config, team_identifier)
        if not team:
            return

        members = db.get_team_members(team["id"])

    if not members:
        print_warning("No members found.")
        return

    _render_members_table(members)


@team.command("invite")
@click.argument("email")
@click.option("--role", type=click.Choice(["member", "admin", "owner"], case_sensitive=False), default="member")
@click.option("--team", "team_identifier", help="Override team to invite into.")
@click.option("--expires-in", type=int, default=7, show_default=True, help="Invitation expiry in days.")
@_handle_db_errors
def invite_member(email: str, role: str, team_identifier: Optional[str], expires_in: int) -> None:
    """Invite a new member to the current team."""
    config = ConfigManager()
    expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in)

    with get_connection() as db:
        team = _resolve_team(db, config, team_identifier)
        if not team:
            return

        invite = db.create_team_invitation(
            email=email,
            team_id=team["id"],
            role=role,
            expires_at=expires_at,
        )

    print_success(f"Invitation created for {email}. Code: {invite['code']}")
    print_success(f"Expires at {_format_timestamp(invite.get('expires_at'))}")


@team.command("invitations")
@click.option("--team", "team_identifier", help="Which team to show invitations for.")
@_handle_db_errors
def list_invitations(team_identifier: Optional[str]) -> None:
    """Show pending invitations for a team."""
    config = ConfigManager()
    with get_connection() as db:
        team = _resolve_team(db, config, team_identifier)
        if not team:
            return

        invitations = db.list_team_invitations(team["id"])

    if not invitations:
        print_warning("No pending invitations.")
        return

    table = Table(title=f"Invitations for {team.get('name')}", box=box.SIMPLE_HEAVY)
    table.add_column("Code")
    table.add_column("Email")
    table.add_column("Role")
    table.add_column("Expires")
    table.add_column("Redeemed")

    for invite in invitations:
        table.add_row(
            invite.get("code") or "-",
            invite.get("email") or "-",
            invite.get("role") or "member",
            _format_timestamp(invite.get("expires_at")),
            _format_timestamp(invite.get("redeemed_at")),
        )

    console.print(table)


@team.command("join")
@click.argument("code")
@_handle_db_errors
def join_team(code: str) -> None:
    """Join a team using an invite code."""
    with get_connection() as db:
        result = db.accept_team_invitation(code)
        if not result:
            print_error("Invitation not found or expired.")
            return

        team = db.get_team(result["team_id"])

    config = ConfigManager()
    config.set_current_team(result["team_id"], team.get("name") if team else None)

    name = team.get("name") if team else result["team_id"]
    print_success(f"Joined team '{name}'.")


@team.command("leave")
@click.argument("team_identifier", required=False)
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt.")
@_handle_db_errors
def leave_team(team_identifier: Optional[str], confirm: bool) -> None:
    """Leave a team you belong to."""
    config = ConfigManager()
    auth_manager = get_auth_manager()
    current_user_id = auth_manager.get_current_user_id()
    if not current_user_id:
        print_error("You must be logged in to leave a team.")
        return

    with get_connection() as db:
        team = _resolve_team(db, config, team_identifier)
        if not team:
            return

        if not confirm and not click.confirm(f"Leave team '{team['name']}'?", default=False):
            print_warning("Aborted.")
            return

        success = db.remove_user_from_team(current_user_id, team["id"])

    if not success:
        print_warning("You were not a member of that team.")
        return

    if config.get_current_team() == team["id"]:
        config.set_current_team(None)

    print_success(f"Left team '{team['name']}'.")


@team.command("remove")
@click.argument("user_id")
@click.option("--team", "team_identifier", help="Team to remove the user from (defaults to current).")
@_handle_db_errors
def remove_member(user_id: str, team_identifier: Optional[str]) -> None:
    """Remove a teammate (admin/owner only)."""
    config = ConfigManager()
    with get_connection() as db:
        team = _resolve_team(db, config, team_identifier)
        if not team:
            return

        removed = db.remove_user_from_team(user_id, team["id"])

    if removed:
        print_success(f"Removed user {user_id} from '{team['name']}'.")
    else:
        print_warning("User was not a member of that team.")
