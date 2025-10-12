"""Configuration helpers for cli-unites.

This module keeps the CLI state (auth token, team id, remote URLs, etc.) in a
single JSON document stored under the user's home directory. The location can be
overridden via the `CLI_UNITES_CONFIG_DIR` environment variable which makes it
straightforward to isolate state during tests.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

CONFIG_DIR_ENV = "CLI_UNITES_CONFIG_DIR"
CONFIG_FILENAME = "config.json"
DEFAULT_CONFIG: Dict[str, Any] = {
    "auth_token": None,
    "refresh_token": None,
    "team_id": None,
    "supabase_url": os.getenv("SUPABASE_URL"),
    "supabase_key": os.getenv("SUPABASE_KEY"),
    "supabase_realtime_url": os.getenv("SUPABASE_REALTIME_URL"),
    "supabase_realtime_channel": os.getenv("SUPABASE_REALTIME_CHANNEL") or "realtime:public:notes",
    "supabase_note_table": os.getenv("SUPABASE_NOTE_TABLE") or "notes",
    "supabase_message_table": os.getenv("SUPABASE_MESSAGE_TABLE") or "messages",
    "team_history": [],
    "first_run_completed": False,
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
        self._config = {**DEFAULT_CONFIG, **data}
        return self._config

    def save(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as fp:
            json.dump(self._config, fp, indent=2, sort_keys=True)

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._config[key] = value
        if key == "team_id" and value:
            history = list(self._config.get("team_history") or [])
            if value in history:
                history.remove(value)
            history.insert(0, value)
            self._config["team_history"] = history[:5]
        self.save()

    def update(self, updates: Dict[str, Any]) -> None:
        self._config.update(updates)
        self.save()

    def as_dict(self) -> Dict[str, Any]:
        return dict(self._config)


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
