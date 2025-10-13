"""Configuration helpers for cli-unites.

This module keeps the CLI state (auth token, team id, remote URLs, etc.) in a
single JSON document stored under the user's home directory. The location can be
overridden via the `CLI_UNITES_CONFIG_DIR` environment variable which makes it
straightforward to isolate state during tests.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, List
import logging
import tempfile
from dotenv import load_dotenv, find_dotenv

# Load .env file early when this module is imported
load_dotenv(find_dotenv(usecwd=True))

logger = logging.getLogger(__name__)

CONFIG_DIR_ENV = "CLI_UNITES_CONFIG_DIR"
CONFIG_FILENAME = "config.json"
CONFIG_VERSION = 2
RECENT_TEAMS_LIMIT = 5

ENV_SUPABASE_URL = os.getenv("SUPABASE_URL")
ENV_SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ENV_SUPABASE_REALTIME_URL = os.getenv("SUPABASE_REALTIME_URL")
ENV_SUPABASE_REALTIME_CHANNEL = os.getenv("SUPABASE_REALTIME_CHANNEL")
ENV_SUPABASE_NOTE_TABLE = os.getenv("SUPABASE_NOTE_TABLE")
ENV_SUPABASE_MESSAGE_TABLE = os.getenv("SUPABASE_MESSAGE_TABLE")
ENV_RESEND_API_KEY = os.getenv("RESEND_API_KEY")
ENV_EMAIL_SERVICE = os.getenv("CLI_UNITES_EMAIL_SERVICE")
ENV_EMAIL_FROM = os.getenv("CLI_UNITES_EMAIL_FROM")
ENV_EMAIL_FROM_NAME = os.getenv("CLI_UNITES_EMAIL_FROM_NAME")
ENV_EMAIL_ENABLED = os.getenv("CLI_UNITES_EMAIL_ENABLED")

def _default_email_service() -> str:
    if ENV_EMAIL_SERVICE:
        return ENV_EMAIL_SERVICE.lower()
    if ENV_RESEND_API_KEY:
        return "resend"
    return "none"

def _default_email_enabled() -> bool:
    if ENV_EMAIL_ENABLED is not None:
        return ENV_EMAIL_ENABLED.lower() in {"1", "true", "yes", "on"}
    return bool(ENV_RESEND_API_KEY and ENV_EMAIL_FROM)

DEFAULT_CONFIG: Dict[str, Any] = {
    "config_version": CONFIG_VERSION,
    "auth_token": None,
    "refresh_token": None,
    "current_user_id": None,
    "session_expires_at": None,
    "team_id": None,  # Legacy key; kept for backwards compatibility
    "current_team_id": None,
    "recent_teams": [],
    "team_membership_cache": {},
    "team_permissions": {},
    "last_team_sync": None,
    "supabase_url": ENV_SUPABASE_URL,
    "supabase_key": ENV_SUPABASE_KEY,
    "supabase_realtime_url": ENV_SUPABASE_REALTIME_URL,
    "supabase_realtime_channel": ENV_SUPABASE_REALTIME_CHANNEL or "realtime:public:notes",
    "supabase_note_table": ENV_SUPABASE_NOTE_TABLE or "notes",
    "supabase_message_table": ENV_SUPABASE_MESSAGE_TABLE or "messages",
    "team_history": [],  # Legacy list of team ids
    "first_run_completed": False,
    "email_service": _default_email_service(),
    "email_notifications_enabled": _default_email_enabled(),
    "email_templates_enabled": True,
    "email_from_address": ENV_EMAIL_FROM,
    "email_from_name": ENV_EMAIL_FROM_NAME or "CLI-Unites",
    "resend_api_key": ENV_RESEND_API_KEY,
}


def _resolve_config_dir(explicit: Optional[Path] = None) -> Path:
    """Return the directory that should host the config file."""
    if explicit is not None:
        return explicit
    override = os.environ.get(CONFIG_DIR_ENV)
    return Path(override).expanduser() if override else Path.home() / ".cli-unites"


class ConfigManager:
    """Simple JSON-backed configuration helper."""

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        self.config_dir = _resolve_config_dir(config_dir)
        self.config_path = self.config_dir / CONFIG_FILENAME
        self._config: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            self._config = DEFAULT_CONFIG.copy()
            return self._config
        try:
            with self.config_path.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
        except json.JSONDecodeError:
            # Fall back to defaults when the config is corrupt rather than crash
            data = DEFAULT_CONFIG.copy()

        data = self._apply_migrations(data)

        # Merge configs, but for null values in data, use DEFAULT_CONFIG values.
        merged = DEFAULT_CONFIG.copy()
        for key, value in data.items():
            if value is not None:
                merged[key] = value
        self._config = merged
        return self._config

    def save(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)

        tmp_file = None
        tmp_path: Optional[Path] = None
        try:
            tmp_file = tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.config_dir, delete=False
            )
            json.dump(self._config, tmp_file, indent=2, sort_keys=True)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
            tmp_path = Path(tmp_file.name)
        finally:
            if tmp_file is not None:
                tmp_file.close()

        if tmp_path is None:
            raise RuntimeError("Failed to persist configuration file.")

        os.replace(tmp_path, self.config_path)

    def get(self, key: str, default: Any = None) -> Any:
        value = self._config.get(key, default)
        # If value is None, check if there's an env var for Supabase settings
        if value is None:
            if key == "supabase_url":
                value = os.getenv("SUPABASE_URL")
            elif key == "supabase_key":
                value = os.getenv("SUPABASE_KEY")
            elif key == "supabase_realtime_url":
                value = os.getenv("SUPABASE_REALTIME_URL")
            elif key == "supabase_realtime_channel":
                value = os.getenv("SUPABASE_REALTIME_CHANNEL") or "realtime:public:notes"
            elif key == "supabase_note_table":
                value = os.getenv("SUPABASE_NOTE_TABLE") or "notes"
            elif key == "supabase_message_table":
                value = ENV_SUPABASE_MESSAGE_TABLE or "messages"
            elif key == "email_service":
                value = _default_email_service()
            elif key == "email_from_address":
                value = ENV_EMAIL_FROM
            elif key == "email_from_name":
                value = ENV_EMAIL_FROM_NAME or "CLI-Unites"
            elif key == "resend_api_key":
                value = ENV_RESEND_API_KEY
            elif key == "email_notifications_enabled":
                value = _default_email_enabled()
        return value

    def set(self, key: str, value: Any) -> None:
        if key in {"team_id", "current_team_id"}:
            self.set_current_team(value, persist=True)
            return
        self._config[key] = value
        self.save()

    def update(self, updates: Dict[str, Any]) -> None:
        team_id = updates.pop("current_team_id", None)
        legacy_team_id = updates.pop("team_id", None)
        team_name = updates.pop("current_team_name", None)

        self._config.update(updates)

        resolved_team_id = team_id if team_id is not None else legacy_team_id
        if resolved_team_id is not None:
            self.set_current_team(resolved_team_id, team_name=team_name, persist=False)
            # Ensure legacy key is in sync for older parts of the app
            self._config["team_id"] = resolved_team_id

        self._config["config_version"] = CONFIG_VERSION
        self.save()

    def set_current_team(self, team_id: Optional[str], team_name: Optional[str] = None, persist: bool = True) -> None:
        self._set_current_team_internal(team_id, team_name)
        if persist:
            self.save()

    def get_current_team(self) -> Optional[str]:
        return self._config.get("current_team_id") or self._config.get("team_id")

    def get_recent_teams(self) -> List[Dict[str, Any]]:
        return list(self._config.get("recent_teams") or [])

    def as_dict(self) -> Dict[str, Any]:
        return dict(self._config)

    def _apply_migrations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        version = data.get("config_version", 1)
        if version < 2:
            self._migrate_v1_to_v2(data)
            version = 2
        data["config_version"] = CONFIG_VERSION
        return data

    def _migrate_v1_to_v2(self, data: Dict[str, Any]) -> None:
        logger.info("Upgrading CLI config with team support (v1 -> v2).")
        data.setdefault("current_team_id", data.get("team_id"))
        data.setdefault("recent_teams", [])
        data.setdefault("team_membership_cache", {})
        data.setdefault("team_permissions", {})
        data.setdefault("last_team_sync", None)
        data.setdefault("current_user_id", None)
        data.setdefault("session_expires_at", None)
        data.setdefault("email_service", _default_email_service())
        data.setdefault("email_notifications_enabled", _default_email_enabled())
        data.setdefault("email_templates_enabled", True)
        data.setdefault("email_from_address", ENV_EMAIL_FROM)
        data.setdefault("email_from_name", ENV_EMAIL_FROM_NAME or "CLI-Unites")
        data.setdefault("resend_api_key", ENV_RESEND_API_KEY)

        # Populate recent teams from legacy history when available.
        history = data.get("team_history") or []
        if history and not data["recent_teams"]:
            now = datetime.now(timezone.utc).isoformat()
            data["recent_teams"] = [
                {"id": tid, "name": None, "switched_at": now} for tid in history[:RECENT_TEAMS_LIMIT]
            ]

    def _set_current_team_internal(self, team_id: Optional[str], team_name: Optional[str]) -> None:
        self._config["current_team_id"] = team_id
        self._config["team_id"] = team_id  # Keep legacy key aligned

        if team_id:
            existing_name = None
            for item in self._config.get("recent_teams", []):
                if item.get("id") == team_id:
                    existing_name = item.get("name")
                    break

            entry = {
                "id": team_id,
                "name": team_name if team_name is not None else existing_name,
                "switched_at": datetime.now(timezone.utc).isoformat(),
            }
            recent = [item for item in self._config.get("recent_teams", []) if item.get("id") != team_id]
            recent.insert(0, entry)
            self._config["recent_teams"] = recent[:RECENT_TEAMS_LIMIT]

            history = list(self._config.get("team_history") or [])
            if team_id in history:
                history.remove(team_id)
            history.insert(0, team_id)
            self._config["team_history"] = history[:RECENT_TEAMS_LIMIT]
        else:
            # Clearing current team should not wipe history, but we ensure field exists.
            self._config.setdefault("recent_teams", [])
            self._config.setdefault("team_history", [])


def load_config(config_dir: Optional[Path] = None) -> Dict[str, Any]:
    return ConfigManager(config_dir=config_dir).as_dict()


def save_config(config: Dict[str, Any], config_dir: Optional[Path] = None) -> None:
    manager = ConfigManager(config_dir=config_dir)
    manager._config = {**DEFAULT_CONFIG, **config}
    manager.save()


def update_config(
    updates: Dict[str, Any], config_dir: Optional[Path] = None
) -> Dict[str, Any]:
    manager = ConfigManager(config_dir=config_dir)
    manager.update(updates)
    return manager.as_dict()
