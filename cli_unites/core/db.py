"""Supabase persistence for notes."""
from __future__ import annotations

import os
import json
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, List, Optional
from uuid import uuid4
import logging
import re
import secrets
import sqlite3
import string

from dotenv import load_dotenv
from supabase import create_client, Client
try:  # pragma: no cover - optional dependency
    from postgrest.exceptions import APIError as PostgrestAPIError  # type: ignore
except Exception:  # pragma: no cover
    PostgrestAPIError = None  # type: ignore
from cli_unites.core.match_notes import match_notes
from .auth import get_auth_manager
from .config import _resolve_config_dir

load_dotenv()

logger = logging.getLogger(__name__)

DB_FILENAME = "notes.db"

UUID_REGEX = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


class TeamServiceUnavailable(RuntimeError):
    """Raised when Supabase is unavailable for team operations."""


class DuplicateResourceError(RuntimeError):
    """Raised when attempting to create an already existing resource."""


class AuthorizationError(RuntimeError):
    """Raised when an operation lacks required permissions."""


def _resolve_db_path(explicit: Optional[Path] = None) -> Optional[Path]:
    if explicit is not None:
        return Path(explicit)
    override = os.environ.get("CLI_UNITES_DB_PATH")
    if override:
        return Path(override).expanduser()
    # Fallback to local SQLite when Supabase credentials are missing.
    if not (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY")):
        return _resolve_config_dir() / DB_FILENAME
    return None


def slugify(value: str) -> str:
    """Convert a team name into a slug."""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "team"


def is_uuid(value: str) -> bool:
    return bool(UUID_REGEX.match(value))


INVITE_CODE_ALPHABET = string.ascii_uppercase + string.digits


def generate_invite_code(length: int = 6) -> str:
    return "".join(secrets.choice(INVITE_CODE_ALPHABET) for _ in range(length))


class Database:
    """Thin wrapper around Supabase client with SQLite fallback for notes operations."""

    def __init__(self, supabase_client: Optional[Client] = None, db_path: Optional[Path] = None) -> None:
        self.auth_manager = get_auth_manager()
        self.mode = "supabase"
        self.client: Optional[Client] = None
        self.sqlite_conn: Optional[sqlite3.Connection] = None
        self.db_path: Optional[Path] = None
        self.supports_team_slug: bool = True
        self.supports_team_description: bool = True
        self.supports_team_created_by: bool = True
        self.supports_user_team_role: bool = True
        self.supports_user_team_invited_by: bool = True
        self.supports_team_invitations: bool = True
        self.supports_note_team_id: bool = True

        resolved_db_path = _resolve_db_path(db_path)
        if resolved_db_path is not None:
            self.mode = "sqlite"
            self._init_sqlite(resolved_db_path)
        else:
            self._init_supabase(supabase_client)

        self.user_id = self.auth_manager.get_current_user_id() or os.getenv("USER_ID")

    def _init_supabase(self, supabase_client: Optional[Client]) -> None:
        if supabase_client is not None:
            self.client = supabase_client
            self.supports_team_slug = True
            return

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
        self.client = create_client(url, key)
        self.supports_team_slug = True

    def _init_sqlite(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.sqlite_conn = sqlite3.connect(self.db_path)
        self.sqlite_conn.row_factory = sqlite3.Row
        self._ensure_sqlite_schema()
        self.supports_team_slug = False
        self.supports_team_description = False
        self.supports_team_created_by = False
        self.supports_user_team_role = False
        self.supports_user_team_invited_by = False
        self.supports_team_invitations = False
        self.supports_note_team_id = False

    def _ensure_sqlite_schema(self) -> None:
        assert self.sqlite_conn is not None
        self.sqlite_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                tags TEXT,
                created_at TEXT NOT NULL,
                git_commit TEXT,
                git_branch TEXT,
                project_path TEXT,
                team_id TEXT
            )
            """
        )
        self.sqlite_conn.commit()
        self._ensure_sqlite_column("team_id", "TEXT")

    def _ensure_sqlite_column(self, column: str, definition: str) -> None:
        assert self.sqlite_conn is not None
        cursor = self.sqlite_conn.execute("PRAGMA table_info(notes)")
        existing = {row[1] for row in cursor.fetchall()}
        if column not in existing:
            self.sqlite_conn.execute(f"ALTER TABLE notes ADD COLUMN {column} {definition}")
            self.sqlite_conn.commit()

    def _sqlite_add_note(
        self,
        title: str,
        body: str,
        tags: Optional[Iterable[str]],
        git_commit: Optional[str],
        git_branch: Optional[str],
        project_path: Optional[str],
        team_id: Optional[str],
    ) -> str:
        assert self.sqlite_conn is not None
        note_id = str(uuid4())
        tag_string = ",".join(sorted({t.strip() for t in tags if t.strip()})) if tags else None
        self.sqlite_conn.execute(
            """
            INSERT INTO notes (id, title, body, tags, created_at, git_commit, git_branch, project_path, team_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                note_id,
                title,
                body,
                tag_string,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                git_commit,
                git_branch,
                project_path,
                team_id,
            ),
        )
        self.sqlite_conn.commit()
        return note_id

    def _sqlite_list_notes(
        self,
        limit: Optional[int],
        tag: Optional[str],
        team_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        assert self.sqlite_conn is not None
        sql = "SELECT * FROM notes"
        params: List[Any] = []
        if tag:
            sql += " WHERE tags LIKE ?"
            params.append(f"%{tag}%")
        if team_id:
            sql += " AND" if "WHERE" in sql else " WHERE"
            sql += " team_id = ?"
            params.append(team_id)
        sql += " ORDER BY datetime(created_at) DESC"
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        cursor = self.sqlite_conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def _sqlite_get_note(self, note_id: str) -> Optional[Dict[str, Any]]:
        assert self.sqlite_conn is not None
        cursor = self.sqlite_conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def _sqlite_search_notes(self, query: str, team_id: Optional[str]) -> List[Dict[str, Any]]:
        assert self.sqlite_conn is not None
        pattern = f"%{query}%"
        params: List[Any] = [pattern, pattern, pattern]
        team_clause = ""
        if team_id:
            team_clause = " AND team_id = ?"
            params.append(team_id)
        cursor = self.sqlite_conn.execute(
            f"""
            SELECT * FROM notes
            WHERE (title LIKE ? OR body LIKE ? OR IFNULL(tags, '') LIKE ?){team_clause}
            ORDER BY datetime(created_at) DESC
            """,
            params,
        )
        return [dict(row) for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # Helpers
    def _require_user_id(self) -> str:
        if self.mode == "sqlite":
            # Offline mode: use cached user id or a placeholder.
            return self.auth_manager.get_current_user_id() or self.user_id or "offline-user"

        user_id = self.auth_manager.get_current_user_id() or self.user_id
        if not user_id:
            raise AuthorizationError("You must be authenticated. Run `notes login` to continue.")
        return user_id

    def _require_supabase_client(self) -> Client:
        if self.mode != "supabase" or self.client is None:
            raise TeamServiceUnavailable("Supabase is not configured for this operation.")
        return self.client

    def _handle_slug_capability_error(self, exc: Exception) -> bool:
        """Detect missing slug column and downgrade capability."""
        message = str(exc).lower()
        if "slug" in message and ("does not exist" in message or "unknown column" in message):
            if self.supports_team_slug:
                logger.info("Team slug column unavailable; falling back to legacy name-based teams.")
            self.supports_team_slug = False
            return True
        if PostgrestAPIError and isinstance(exc, PostgrestAPIError):
            details = getattr(exc, "details", None)
            if details and "slug" in str(details).lower():
                self.supports_team_slug = False
                return True
        return False

    def _handle_team_column_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        handled = False
        if self.supports_team_description and "description" in message and "teams" in message:
            self.supports_team_description = False
            handled = True
        if self.supports_team_created_by and ("created_by" in message and "teams" in message):
            self.supports_team_created_by = False
            handled = True
        if handled:
            logger.info("Disabling advanced team columns due to schema mismatch: %s", message)
        return handled

    def _handle_users_team_column_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        handled = False
        if self.supports_user_team_role and "role" in message and "users_teams" in message:
            self.supports_user_team_role = False
            handled = True
        if self.supports_user_team_invited_by and ("invited_by" in message and "users_teams" in message):
            self.supports_user_team_invited_by = False
            handled = True
        if handled:
            logger.info("Disabling users_teams optional columns due to schema mismatch: %s", message)
        return handled

    def _handle_invitations_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        if "team_invitations" in message and ("does not exist" in message or "relation" in message):
            if self.supports_team_invitations:
                logger.info("Team invitations table missing; disabling invitation features.")
            self.supports_team_invitations = False
            return True
        return False

    def _handle_notes_column_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        if (
            self.supports_note_team_id
            and "notes" in message
            and "team_id" in message
            and ("does not exist" in message or "unknown column" in message or "column" in message)
        ):
            self.supports_note_team_id = False
            logger.info("Notes table lacks team_id column; falling back to project-based filtering.")
            return True
        return False

    def _unique_team_slug(self, name: str, exclude_team_id: Optional[str] = None) -> Optional[str]:
        if not self.supports_team_slug:
            return None

        client = self._require_supabase_client()
        base_slug = slugify(name)
        candidate = base_slug
        attempt = 1

        while True:
            try:
                query = client.table("teams").select("id").eq("slug", candidate)
                response = query.execute()
            except Exception as exc:
                if self._handle_slug_capability_error(exc):
                    return None
                raise TeamServiceUnavailable("Unable to generate unique team slug.") from exc

            if not response.data:
                return candidate

            if exclude_team_id and any(row["id"] == exclude_team_id for row in response.data):
                return candidate

            attempt += 1
            candidate = f"{base_slug}-{attempt}"
            if attempt > 50:
                raise RuntimeError("Unable to generate unique team slug after multiple attempts.")

    def _fetch_team(self, field: str, value: Any) -> Optional[Dict[str, Any]]:
        client = self._require_supabase_client()
        try:
            response = client.table("teams").select("*").eq(field, value).limit(1).execute()
        except Exception as exc:
            if field == "slug" and self._handle_slug_capability_error(exc):
                return None
            raise TeamServiceUnavailable("Failed to fetch team information.") from exc

        if not response.data:
            return None
        return response.data[0]

    def _fetch_team_by_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
        if not identifier:
            return None

        if self.mode != "supabase":
            # Offline mode does not maintain team entities.
            return None

        if is_uuid(identifier):
            team = self._fetch_team("id", identifier)
            if team:
                return team

        # Try slug, then name case-insensitive
        if self.supports_team_slug:
            team = self._fetch_team("slug", identifier)
            if team:
                return team

        try:
            response = self._require_supabase_client().table("teams").select("*").ilike("name", identifier).limit(1).execute()
            if response.data:
                return response.data[0]
        except Exception:
            pass
        return None

    def _resolve_team_id(self, identifier: str) -> Optional[str]:
        if self.mode == "sqlite":
            return identifier
        team = self._fetch_team_by_identifier(identifier)
        return team["id"] if team else None

    def _fetch_membership(self, user_id: str, team_id: str) -> Optional[Dict[str, Any]]:
        client = self._require_supabase_client()
        while True:
            columns = ["user_id", "team_id", "joined_at"]
            if self.supports_user_team_role:
                columns.append("role")
            if self.supports_user_team_invited_by:
                columns.append("invited_by")
            try:
                response = (
                    client.table("users_teams")
                    .select(", ".join(columns))
                    .eq("user_id", user_id)
                    .eq("team_id", team_id)
                    .limit(1)
                    .execute()
                )
                break
            except Exception as exc:
                if self._handle_users_team_column_error(exc):
                    continue
                raise TeamServiceUnavailable("Failed to fetch team membership.") from exc

        if not response.data:
            return None
        return response.data[0]

    def _assert_role(self, team_id: str, allowed_roles: Iterable[str]) -> None:
        if not self.supports_user_team_role:
            return  # Legacy schema has no role concept; allow operation
        user_id = self._require_user_id()
        membership = self._fetch_membership(user_id, team_id)
        if not membership or membership.get("role") not in set(allowed_roles):
            raise AuthorizationError("You don't have permission to manage this team.")

    def _project_ids_for_team(self, team_id: str) -> List[str]:
        client = self._require_supabase_client()
        try:
            response = (
                client.table("projects")
                .select("id")
                .eq("team_id", team_id)
                .execute()
            )
        except Exception as exc:
            raise TeamServiceUnavailable("Failed to load team projects.") from exc

        return [row["id"] for row in response.data or []]

    # ------------------------------------------------------------------
    # Team management
    def create_team(self, name: str, description: Optional[str] = None) -> str:
        client = self._require_supabase_client()
        user_id = self._require_user_id()

        slug_value: Optional[str] = None

        while True:
            payload: Dict[str, Any] = {"name": name}

            if description is not None and self.supports_team_description:
                payload["description"] = description

            if self.supports_team_slug:
                slug_value = self._unique_team_slug(name)
                if slug_value:
                    payload["slug"] = slug_value

            if self.supports_team_created_by:
                payload["created_by"] = user_id

            try:
                response = client.table("teams").insert(payload).execute()
                break
            except Exception as exc:
                if self._handle_slug_capability_error(exc) or self._handle_team_column_error(exc):
                    continue
                message = str(exc).lower()
                if "duplicate" in message or "unique constraint" in message:
                    raise DuplicateResourceError("Team name already exists. Try a different name.") from exc
                raise TeamServiceUnavailable("Failed to create team.") from exc

        team = None
        if response.data:
            team = response.data[0]
        if not team and slug_value:
            team = self._fetch_team("slug", slug_value)
        if not team:
            team = self._fetch_team("name", name)
        if not team:
            raise TeamServiceUnavailable("Supabase did not return the created team.")

        # Ensure creator is marked as owner.
        try:
            self.add_user_to_team(user_id, team["id"], role="owner", invited_by=user_id)
        except DuplicateResourceError:
            pass  # Already owner

        return team["id"]

    def get_team(self, team_identifier: str) -> Optional[Dict[str, Any]]:
        client = self._require_supabase_client()
        team = self._fetch_team_by_identifier(team_identifier)
        if not team:
            return None

        try:
            member_resp = (
                client.table("users_teams")
                .select("user_id")
                .eq("team_id", team["id"])
                .execute()
            )
            team["member_count"] = len(member_resp.data or [])
        except Exception:
            team["member_count"] = None

        return team

    def list_user_teams(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        client = self._require_supabase_client()
        target_user_id = user_id or self._require_user_id()
        while True:
            membership_columns = ["team_id", "joined_at"]
            if self.supports_user_team_role:
                membership_columns.insert(1, "role")
            if self.supports_user_team_invited_by:
                membership_columns.append("invited_by")
            try:
                membership_resp = (
                    client.table("users_teams")
                    .select(", ".join(membership_columns))
                    .eq("user_id", target_user_id)
                    .execute()
                )
                break
            except Exception as exc:
                if self._handle_users_team_column_error(exc):
                    continue
                raise TeamServiceUnavailable("Failed to load team memberships.") from exc

        memberships = membership_resp.data or []
        if not memberships:
            return []

        team_ids = [row["team_id"] for row in memberships]
        while True:
            columns = ["id", "name", "description", "created_at", "updated_at"]
            if self.supports_team_slug:
                columns.insert(2, "slug")
            try:
                teams_resp = (
                    client.table("teams")
                    .select(", ".join(columns))
                    .in_("id", team_ids)
                    .execute()
                )
                break
            except Exception as exc:
                handled = False
                if self._handle_slug_capability_error(exc) or self._handle_team_column_error(exc):
                    handled = True
                if handled:
                    continue
                raise TeamServiceUnavailable("Failed to fetch teams.") from exc

        team_map = {team["id"]: team for team in teams_resp.data or []}

        results: List[Dict[str, Any]] = []
        for row in memberships:
            team = team_map.get(row["team_id"])
            if not team:
                continue
            results.append(
                {
                    "team": team,
                    "role": row.get("role", "member"),
                    "joined_at": row.get("joined_at"),
                }
            )

        return sorted(results, key=lambda item: item["team"].get("name", "").lower())

    def get_user_teams(self, user_id: str) -> List[Dict[str, Any]]:
        return self.list_user_teams(user_id)

    def update_team(self, team_id: str, **updates: Any) -> bool:
        self._assert_role(team_id, {"owner", "admin"})
        client = self._require_supabase_client()

        payload: Dict[str, Any] = {}
        if "name" in updates and updates["name"]:
            payload["name"] = updates["name"]
            slug_candidate = self._unique_team_slug(updates["name"], exclude_team_id=team_id)
            if slug_candidate:
                payload["slug"] = slug_candidate

        if "description" in updates:
            payload["description"] = updates["description"]

        if "slug" in updates and updates["slug"] and self.supports_team_slug:
            slug_candidate = self._unique_team_slug(updates["slug"], exclude_team_id=team_id)
            if slug_candidate:
                payload["slug"] = slug_candidate

        if not payload:
            return False

        payload["updated_at"] = datetime.now(timezone.utc).isoformat()

        try:
            response = (
                client.table("teams")
                .update(payload)
                .eq("id", team_id)
                .execute()
            )
        except Exception as exc:
            message = str(exc).lower()
            if "duplicate" in message or "unique constraint" in message:
                raise DuplicateResourceError("Team slug already exists.") from exc
            raise TeamServiceUnavailable("Failed to update team.") from exc

        return bool(response.data)

    def delete_team(self, team_id: str) -> bool:
        self._assert_role(team_id, {"owner"})
        client = self._require_supabase_client()
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            response = (
                client.table("teams")
                .update({"deleted_at": now_iso})
                .eq("id", team_id)
                .execute()
            )
            if response.data:
                return True
        except Exception as exc:
            message = str(exc).lower()
            if "column" in message and "deleted_at" in message:
                # Soft-delete column not available yet; fallback to hard delete.
                try:
                    client.table("teams").delete().eq("id", team_id).execute()
                    return True
                except Exception as inner_exc:
                    raise TeamServiceUnavailable("Failed to delete team.") from inner_exc
            raise TeamServiceUnavailable("Failed to delete team.") from exc

        return False

    def add_user_to_team(
        self,
        user_id: str,
        team_id: str,
        role: str = "member",
        invited_by: Optional[str] = None,
    ) -> bool:
        client = self._require_supabase_client()
        while True:
            payload = {
                "user_id": user_id,
                "team_id": team_id,
                "joined_at": datetime.now(timezone.utc).isoformat(),
            }
            if self.supports_user_team_role:
                payload["role"] = role
            if self.supports_user_team_invited_by and invited_by:
                payload["invited_by"] = invited_by

            try:
                client.table("users_teams").insert(payload).execute()
                return True
            except Exception as exc:
                message = str(exc).lower()
                if "foreign key" in message and "users" in message:
                    user_payload = self.auth_manager.get_current_user()
                    if user_payload:
                        self.auth_manager.ensure_user_exists(user_payload)
                        continue
                if self._handle_users_team_column_error(exc):
                    continue
                if "duplicate" in message or "unique constraint" in message:
                    raise DuplicateResourceError("User is already a member of this team.") from exc
                raise TeamServiceUnavailable(f"Failed to add user to team: {exc}") from exc

    def remove_user_from_team(self, user_id: str, team_id: str) -> bool:
        current_user_id = self._require_user_id()
        if current_user_id != user_id:
            self._assert_role(team_id, {"owner", "admin"})

        try:
            response = (
                self._require_supabase_client().table("users_teams")
                .delete()
                .eq("user_id", user_id)
                .eq("team_id", team_id)
                .execute()
            )
        except Exception as exc:
            raise TeamServiceUnavailable("Failed to remove user from team.") from exc

        return bool(response.data)

    def get_team_members(self, team_id: str) -> List[Dict[str, Any]]:
        client = self._require_supabase_client()
        while True:
            membership_columns = ["user_id", "joined_at"]
            if self.supports_user_team_role:
                membership_columns.insert(1, "role")
            if self.supports_user_team_invited_by:
                membership_columns.append("invited_by")
            try:
                membership_resp = (
                    client.table("users_teams")
                    .select(", ".join(membership_columns))
                    .eq("team_id", team_id)
                    .execute()
                )
                break
            except Exception as exc:
                if self._handle_users_team_column_error(exc):
                    continue
                raise TeamServiceUnavailable("Failed to load team members.") from exc

        memberships = membership_resp.data or []
        if not memberships:
            return []

        user_ids = [row["user_id"] for row in memberships]

        try:
            users_resp = (
                client.table("users")
                .select("id, email, full_name, avatar_url, created_at")
                .in_("id", user_ids)
                .execute()
            )
        except Exception as exc:
            raise TeamServiceUnavailable("Failed to load user details.") from exc

        user_map = {user["id"]: user for user in users_resp.data or []}

        results: List[Dict[str, Any]] = []
        for row in memberships:
            user = user_map.get(row["user_id"], {"id": row["user_id"]})
            results.append(
                {
                    **user,
                    "role": row.get("role", "member"),
                    "joined_at": row.get("joined_at"),
                }
            )

        return sorted(results, key=lambda item: (item.get("role") != "owner", item.get("email") or ""))

    def list_notes_for_team(self, team_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        if self.mode == "sqlite":
            return self._sqlite_list_notes(limit=limit, tag=None, team_id=team_id)

        client = self._require_supabase_client()
        query = (
            client.table("notes")
            .select("*")
            .order("created_at", desc=True)
        )

        if self.supports_note_team_id:
            query = query.eq("team_id", team_id)

        try:
            project_ids = self._project_ids_for_team(team_id)
        except Exception:
            project_ids = None
        if project_ids:
            query = query.in_("project_id", project_ids)

        if limit:
            query = query.limit(limit)

        try:
            response = query.execute()
        except Exception as exc:
            if self._handle_notes_column_error(exc):
                return self.list_notes_for_team(team_id, limit=limit)
            raise TeamServiceUnavailable("Failed to list team notes.") from exc

        return response.data or []

    def search_team_notes(self, team_id: str, query_text: str) -> List[Dict[str, Any]]:
        if self.mode == "sqlite":
            return self._sqlite_search_notes(query_text, team_id)

        client = self._require_supabase_client()

        try:
            project_ids = self._project_ids_for_team(team_id)
        except Exception:
            project_ids = None

        try:
            body_query = client.table("notes").select("*").text_search("body_tsv", query_text)
            if self.supports_note_team_id:
                body_query = body_query.eq("team_id", team_id)
            if project_ids:
                body_query = body_query.in_("project_id", project_ids)
            body_query = body_query.order("created_at", desc=True).execute()

            title_query = client.table("notes").select("*").ilike("title", f"%{query_text}%")
            if self.supports_note_team_id:
                title_query = title_query.eq("team_id", team_id)
            if project_ids:
                title_query = title_query.in_("project_id", project_ids)
            title_query = title_query.order("created_at", desc=True).execute()
        except Exception as exc:
            if self._handle_notes_column_error(exc):
                return self.search_team_notes(team_id, query_text)
            raise TeamServiceUnavailable("Failed to search team notes.") from exc

        seen_ids = set()
        combined: List[Dict[str, Any]] = []
        for item in (body_query.data or []) + (title_query.data or []):
            if item["id"] in seen_ids:
                continue
            seen_ids.add(item["id"])
            combined.append(item)

        return combined

    def get_team_activity(self, team_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        if self.mode == "sqlite":
            rows = self._sqlite_list_notes(limit=limit, tag=None, team_id=team_id)
            return rows

        client = self._require_supabase_client()
        try:
            project_ids = self._project_ids_for_team(team_id)
        except Exception:
            project_ids = None

        try:
            query = (
                client.table("notes")
                .select("id, title, updated_at, created_at, user_id, project_id")
                .order("updated_at", desc=True)
                .limit(limit)
            )
            if self.supports_note_team_id:
                query = query.eq("team_id", team_id)
            if project_ids:
                query = query.in_("project_id", project_ids)
            response = query.execute()
        except Exception as exc:
            if self._handle_notes_column_error(exc):
                return self.get_team_activity(team_id, limit=limit)
            raise TeamServiceUnavailable("Failed to load team activity.") from exc

        return response.data or []

    # ------------------------------------------------------------------
    # Invitations
    def create_team_invitation(
        self,
        email: str,
        team_id: str,
        role: str = "member",
        invite_code: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        self._assert_role(team_id, {"owner", "admin"})
        inviter_id = self._require_user_id()
        if not self.supports_team_invitations:
            raise TeamServiceUnavailable(
                "Team invitations require the latest Supabase migration. Apply the migration to enable invite codes."
            )
        client = self._require_supabase_client()

        code = invite_code or generate_invite_code()
        expiry = expires_at or datetime.now(timezone.utc) + timedelta(days=7)
        expiry_iso = expiry.isoformat()

        # Prevent duplicates for same email + active invite.
        try:
            existing = (
                client.table("team_invitations")
                .select("code")
                .eq("team_id", team_id)
                .eq("email", email)
                .is_("redeemed_at", None)
                .execute()
            )
            if existing.data:
                raise DuplicateResourceError("An active invitation already exists for this email.")
        except DuplicateResourceError:
            raise
        except Exception as exc:
            if self._handle_invitations_error(exc):
                raise TeamServiceUnavailable(
                    "Team invitations require the latest Supabase migration. Apply the migration to enable invite codes."
                )
            # Ignore lookup errors—still try to insert.
            pass

        payload = {
            "code": code,
            "team_id": team_id,
            "email": email,
            "role": role,
            "invited_by": inviter_id,
            "expires_at": expiry_iso,
        }

        try:
            response = client.table("team_invitations").insert(payload).execute()
        except Exception as exc:
            if self._handle_invitations_error(exc):
                raise TeamServiceUnavailable(
                    "Team invitations require the latest Supabase migration. Apply the migration to enable invite codes."
                )
            message = str(exc).lower()
            if "duplicate" in message or "unique constraint" in message:
                raise DuplicateResourceError("Invitation code already in use.") from exc
            raise TeamServiceUnavailable("Failed to create invitation.") from exc

        return response.data[0] if response.data else payload

    def list_team_invitations(self, team_id: str) -> List[Dict[str, Any]]:
        self._assert_role(team_id, {"owner", "admin"})
        if not self.supports_team_invitations:
            raise TeamServiceUnavailable(
                "Team invitations require the latest Supabase migration. Apply the migration to enable invite codes."
            )
        client = self._require_supabase_client()
        try:
            response = (
                client.table("team_invitations")
                .select("*")
                .eq("team_id", team_id)
                .order("created_at", desc=True)
                .execute()
            )
        except Exception as exc:
            if self._handle_invitations_error(exc):
                raise TeamServiceUnavailable(
                    "Team invitations require the latest Supabase migration. Apply the migration to enable invite codes."
                )
            raise TeamServiceUnavailable("Failed to list team invitations.") from exc

        return response.data or []

    def revoke_team_invitation(self, code: str) -> bool:
        if not self.supports_team_invitations:
            raise TeamServiceUnavailable(
                "Team invitations require the latest Supabase migration. Apply the migration to enable invite codes."
            )
        try:
            response = (
                self._require_supabase_client().table("team_invitations")
                .delete()
                .eq("code", code)
                .execute()
            )
        except Exception as exc:
            if self._handle_invitations_error(exc):
                raise TeamServiceUnavailable(
                    "Team invitations require the latest Supabase migration. Apply the migration to enable invite codes."
                )
            raise TeamServiceUnavailable("Failed to revoke invitation.") from exc

        return bool(response.data)

    def accept_team_invitation(self, code: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        target_user_id = user_id or self._require_user_id()
        if not self.supports_team_invitations:
            raise TeamServiceUnavailable(
                "Team invitations require the latest Supabase migration. Apply the migration to enable invite codes."
            )
        client = self._require_supabase_client()

        try:
            response = (
                client.table("team_invitations")
                .select("*")
                .eq("code", code)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            if self._handle_invitations_error(exc):
                raise TeamServiceUnavailable(
                    "Team invitations require the latest Supabase migration. Apply the migration to enable invite codes."
                )
            raise TeamServiceUnavailable("Failed to look up invitation.") from exc

        if not response.data:
            return None

        invite = response.data[0]
        expires_at_raw = invite.get("expires_at")
        if expires_at_raw:
            try:
                expires_at_dt = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
                if expires_at_dt < datetime.now(timezone.utc):
                    return None
            except ValueError:
                pass

        team_id = invite["team_id"]
        role = invite.get("role", "member")
        inviter = invite.get("invited_by")

        try:
            self.add_user_to_team(target_user_id, team_id, role=role, invited_by=inviter)
        except DuplicateResourceError:
            pass

        try:
            client.table("team_invitations").update(
                {"redeemed_at": datetime.now(timezone.utc).isoformat()}
            ).eq("code", code).execute()
        except Exception as exc:
            logger.debug("Failed to mark invitation as redeemed: %s", exc)

        return {"team_id": team_id, "user_email": invite.get("email"), "role": role}

    def add_note(
        self,
        title: str,
        body: str,
        tags: Optional[Iterable[str]] = None,
        git_commit: Optional[str] = None,
        git_branch: Optional[str] = None,
        project_path: Optional[str] = None,
        team_id: Optional[str] = None,
    ) -> str:
        if self.mode == "sqlite":
            return self._sqlite_add_note(
                title,
                body,
                tags,
                git_commit,
                git_branch,
                project_path,
                team_id,
            )

        note_id = str(uuid4())

        # First, ensure project exists if project_path is provided
        project_id = None
        if project_path and self.mode != "sqlite":
            project_id = self._ensure_project(project_path, team_id)

        # Resolve team identifier if possible
        team_uuid: Optional[str] = None
        if team_id:
            try:
                team_uuid = self._resolve_team_id(team_id)
            except TeamServiceUnavailable:
                team_uuid = None
            if not team_uuid and is_uuid(team_id):
                team_uuid = team_id

        # Insert the note
        user_id = self._require_user_id()
        note_data = {
            "id": note_id,
            "title": title,
            "body": body,
            "user_id": user_id,
            "project_id": project_id,
        }
        if team_uuid and self.supports_note_team_id:
            note_data["team_id"] = team_uuid

        client = self._require_supabase_client()
        while True:
            try:
                response = client.table("notes").insert(note_data).execute()
                break
            except Exception as exc:
                if "queue" in str(exc).lower():  # unrelated errors -> raise
                    raise
                if "duplicate" in str(exc).lower() and "id" in str(exc).lower():
                    note_data["id"] = str(uuid4())
                    note_id = note_data["id"]
                    continue
                if self._handle_notes_column_error(exc):
                    note_data.pop("team_id", None)
                    continue
                raise TeamServiceUnavailable(f"Failed to add note: {exc}") from exc

        # Handle tags if provided
        if tags:
            self._add_tags_to_note(note_id, tags)

        return note_id

    def _ensure_project(self, project_path: str, team_id: Optional[str] = None) -> str:
        """Ensure project exists, create if not. Returns project_id."""
        client = self._require_supabase_client()
        # Check if project exists
        response = client.table("projects").select("id").eq("absolute_path", project_path).execute()

        if response.data:
            return response.data[0]["id"]

        # Create new project and associate with team if provided
        project_id = str(uuid4())
        project_data = {
            "id": project_id,
            "name": project_path.split("/")[-1],  # Use last part of path as name
            "absolute_path": project_path,
        }
        
        # If team_id is provided, try to find or create the team
        if team_id:
            team_uuid = self._ensure_team(team_id)
            project_data["team_id"] = team_uuid
        
        client.table("projects").insert(project_data).execute()
        return project_id

    def _ensure_team(self, team_identifier: str) -> str:
        """Resolve a team identifier or create a new team when given a name."""
        if self.mode == "sqlite":
            return team_identifier

        team = self._fetch_team_by_identifier(team_identifier)
        if team:
            return team["id"]

        if is_uuid(team_identifier):
            raise TeamServiceUnavailable("Team identifier not found.")

        # Treat as name and create a new team.
        return self.create_team(team_identifier)

    def _add_tags_to_note(self, note_id: str, tags: Iterable[str]) -> None:
        """Add tags to a note."""
        client = self._require_supabase_client()
        tag_list = sorted({t.strip() for t in tags if t.strip()})

        for tag_name in tag_list:
            # Ensure tag exists
            response = client.table("tags").select("id").eq("name", tag_name).execute()

            if response.data:
                tag_id = response.data[0]["id"]
            else:
                # Create new tag
                tag_id = str(uuid4())
                client.table("tags").insert({"id": tag_id, "name": tag_name}).execute()

            # Link tag to note
            client.table("notes_tags").insert({
                "note_id": note_id,
                "tag_id": tag_id
            }).execute()

    def list_notes(
        self,
        limit: Optional[int] = None,
        tag: Optional[str] = None,
        team_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if self.mode == "sqlite":
            return self._sqlite_list_notes(limit=limit, tag=tag, team_id=team_id)

        client = self._require_supabase_client()
        query = client.table("notes").select("*")

        resolved_team_id: Optional[str] = None
        if team_id:
            resolved_team_id = self._resolve_team_id(team_id)
            if not resolved_team_id:
                resolved_team_id = team_id  # fall back to provided identifier
        if resolved_team_id:
            if self.supports_note_team_id:
                query = query.eq("team_id", resolved_team_id)

            try:
                project_ids = self._project_ids_for_team(resolved_team_id)
            except Exception:
                project_ids = None
            if project_ids:
                query = query.in_("project_id", project_ids)

        if tag:
            try:
                tag_rows = client.table("tags").select("id").eq("name", tag).limit(1).execute()
            except Exception:
                tag_rows = None
            if not tag_rows or not tag_rows.data:
                return []
            tag_id = tag_rows.data[0]["id"]
            try:
                note_tag_rows = (
                    client.table("notes_tags")
                    .select("note_id")
                    .eq("tag_id", tag_id)
                    .execute()
                )
            except Exception:
                note_tag_rows = None
            note_ids = [row["note_id"] for row in (note_tag_rows.data if note_tag_rows and note_tag_rows.data else [])]
            if not note_ids:
                return []
            query = query.in_("id", note_ids)

        query = query.order("created_at", desc=True)

        if limit:
            query = query.limit(limit)

        try:
            response = query.execute()
        except Exception as exc:
            if self._handle_notes_column_error(exc):
                return self.list_notes(limit=limit, tag=tag, team_id=team_id)
            raise TeamServiceUnavailable("Failed to list notes.") from exc
        return response.data or []

    def get_note(self, note_id: str) -> Optional[Dict[str, Any]]:
        if self.mode == "sqlite":
            return self._sqlite_get_note(note_id)

        response = self._require_supabase_client().table("notes").select("*").eq("id", note_id).execute()
        return response.data[0] if response.data else None

    def search_notes(self, query: str, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
        # Get project IDs if team_id is provided
        if self.mode == "sqlite":
            return self._sqlite_search_notes(query, team_id)

        client = self._require_supabase_client()

        resolved_team_id: Optional[str] = None
        if team_id:
            resolved_team_id = self._resolve_team_id(team_id)
            if not resolved_team_id:
                resolved_team_id = team_id

        try:
            project_ids = self._project_ids_for_team(resolved_team_id) if resolved_team_id else None
        except Exception:
            project_ids = None

        body_query = client.table("notes").select("*").text_search("body_tsv", query)
        if resolved_team_id and self.supports_note_team_id:
            body_query = body_query.eq("team_id", resolved_team_id)
        if project_ids:
            body_query = body_query.in_("project_id", project_ids)
        try:
            response = body_query.order("created_at", desc=True).execute()
        except Exception as exc:
            if self._handle_notes_column_error(exc):
                return self.search_notes(query, team_id)
            raise TeamServiceUnavailable("Failed to search notes.") from exc

        title_query = client.table("notes").select("*").ilike("title", f"%{query}%")
        if resolved_team_id and self.supports_note_team_id:
            title_query = title_query.eq("team_id", resolved_team_id)
        if project_ids:
            title_query = title_query.in_("project_id", project_ids)
        try:
            title_results = title_query.order("created_at", desc=True).execute()
        except Exception as exc:
            if self._handle_notes_column_error(exc):
                return self.search_notes(query, team_id)
            raise TeamServiceUnavailable("Failed to search notes.") from exc

        # Combine and deduplicate results
        seen_ids = set()
        combined = []
        for item in (response.data or []) + (title_results.data or []):
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                combined.append(item)

        return combined

    def semantic_search(self, query: str, limit: int = 10, threshold: float = 0.3) -> List[Dict[str, Any]]:
        """Perform semantic search using vector embeddings."""
        if self.mode == "sqlite":
            raise TeamServiceUnavailable("Semantic search requires Supabase configuration.")

        import sys
        import supabase

        # Generate embedding for the query by calling the 'search-embed' edge function
        response = self._require_supabase_client().functions.invoke("search-embed", invoke_options={'body': {'query': query}})
        query_embedding = json.loads(response)['embedding']

        return match_notes(self, query_embedding, limit=limit, threshold=threshold)

    def close(self) -> None:
        if self.sqlite_conn is not None:
            self.sqlite_conn.close()
            self.sqlite_conn = None


@contextmanager
def get_connection(supabase_client: Optional[Client] = None, db_path: Optional[Path] = None) -> Generator[Database, None, None]:
    db = Database(supabase_client, db_path=db_path)
    try:
        yield db
    finally:
        db.close()
