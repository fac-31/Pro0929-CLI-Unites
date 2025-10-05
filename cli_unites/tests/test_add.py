from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from cli_unites.cli import cli
from cli_unites.core.db import Database


def test_add_note_writes_to_database(tmp_path: Path) -> None:
    runner = CliRunner()
    config_dir = tmp_path / "config"
    db_path = config_dir / "notes.db"

    result = runner.invoke(
        cli,
        ["add", "First note", "--body", "This is a body.", "--tag", "alpha", "--tag", "beta"],
        env={
            "CLI_UNITES_CONFIG_DIR": str(config_dir),
            "CLI_UNITES_DB_PATH": str(db_path),
            "CLI_UNITES_DISABLE_GIT": "1",
        },
    )

    assert result.exit_code == 0, result.output
    assert "Saved note" in result.output

    db = Database(db_path=db_path)
    notes = db.list_notes()
    db.close()

    assert len(notes) == 1
    stored = notes[0]
    assert stored["title"] == "First note"
    assert "alpha" in stored["tags"]
    assert "beta" in stored["tags"]


def test_add_requires_content_without_allow_empty(tmp_path: Path) -> None:
    runner = CliRunner()
    config_dir = tmp_path / "config"
    db_path = config_dir / "notes.db"

    result = runner.invoke(
        cli,
        ["add", "Title"],
        env={
            "CLI_UNITES_CONFIG_DIR": str(config_dir),
            "CLI_UNITES_DB_PATH": str(db_path),
            "CLI_UNITES_DISABLE_GIT": "1",
        },
    )

    assert result.exit_code != 0
    assert "No note content provided" in result.output


def test_add_allow_empty_succeeds(tmp_path: Path) -> None:
    runner = CliRunner()
    config_dir = tmp_path / "config"
    db_path = config_dir / "notes.db"

    result = runner.invoke(
        cli,
        ["add", "Title", "--allow-empty"],
        env={
            "CLI_UNITES_CONFIG_DIR": str(config_dir),
            "CLI_UNITES_DB_PATH": str(db_path),
            "CLI_UNITES_DISABLE_GIT": "1",
        },
    )

    assert result.exit_code == 0, result.output
    db = Database(db_path=db_path)
    notes = db.list_notes()
    db.close()
    assert len(notes) == 1
    assert notes[0]["body"] == ""
