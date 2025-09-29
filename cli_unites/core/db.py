"""Local SQLite persistence for notes."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, Generator, Iterable, List, Optional
from uuid import uuid4

from .config import _resolve_config_dir

DB_FILENAME = "notes.db"


def _resolve_db_path(explicit: Optional[Path] = None) -> Path:
    if explicit is not None:
        return explicit
    override = os.environ.get("CLI_UNITES_DB_PATH")
    if override:
        return Path(override).expanduser()
    return _resolve_config_dir() / DB_FILENAME


class Database:
    """Thin wrapper around an SQLite connection with schema helpers."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = _resolve_db_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.ensure_schema()

    def ensure_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                tags TEXT,
                created_at TEXT NOT NULL,
                git_commit TEXT,
                git_branch TEXT,
                project_path TEXT
            )
            """
        )
        self.conn.commit()

    def add_note(
        self,
        title: str,
        body: str,
        tags: Optional[Iterable[str]] = None,
        git_commit: Optional[str] = None,
        git_branch: Optional[str] = None,
        project_path: Optional[str] = None,
    ) -> str:
        note_id = str(uuid4())
        tag_string = ",".join(sorted({t.strip() for t in tags if t.strip()})) if tags else None
        self.conn.execute(
            """
            INSERT INTO notes (id, title, body, tags, created_at, git_commit, git_branch, project_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                note_id,
                title,
                body,
                tag_string,
                datetime.now(UTC).isoformat(timespec="seconds"),
                git_commit,
                git_branch,
                project_path,
            ),
        )
        self.conn.commit()
        return note_id

    def list_notes(self, limit: Optional[int] = None, tag: Optional[str] = None) -> List[Dict[str, str]]:
        sql = "SELECT * FROM notes"
        params: List[object] = []
        if tag:
            sql += " WHERE tags LIKE ?"
            params.append(f"%{tag}%")
        sql += " ORDER BY datetime(created_at) DESC"
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        cursor = self.conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_note(self, note_id: str) -> Optional[Dict[str, str]]:
        cursor = self.conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def search_notes(self, query: str) -> List[Dict[str, str]]:
        pattern = f"%{query}%"
        cursor = self.conn.execute(
            """
            SELECT * FROM notes
            WHERE title LIKE ? OR body LIKE ? OR IFNULL(tags, '') LIKE ?
            ORDER BY datetime(created_at) DESC
            """,
            (pattern, pattern, pattern),
        )
        return [dict(row) for row in cursor.fetchall()]

    def close(self) -> None:
        self.conn.close()


@contextmanager
def get_connection(db_path: Optional[Path] = None) -> Generator[Database, None, None]:
    db = Database(db_path)
    try:
        yield db
    finally:
        db.close()
