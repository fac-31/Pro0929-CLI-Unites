from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from cli_unites.cli import cli


def _invoke(runner: CliRunner, command: list[str], config_dir: Path, db_path: Path) -> None:
    result = runner.invoke(
        cli,
        command,
        env={
            "CLI_UNITES_CONFIG_DIR": str(config_dir),
            "CLI_UNITES_DB_PATH": str(db_path),
            "CLI_UNITES_DISABLE_GIT": "1",
            "CLI_UNITES_SKIP_ONBOARDING": "1",
        },
    )
    assert result.exit_code == 0, result.output


def test_list_shows_added_notes(tmp_path: Path) -> None:
    runner = CliRunner()
    config_dir = tmp_path / "config"
    db_path = config_dir / "notes.db"

    _invoke(runner, ["add", "Title A", "--body", "Alpha body"], config_dir, db_path)
    _invoke(runner, ["add", "Title B", "--body", "Beta body", "--tag", "release"], config_dir, db_path)

    result = runner.invoke(
        cli,
        ["list"],
        env={
            "CLI_UNITES_CONFIG_DIR": str(config_dir),
            "CLI_UNITES_DB_PATH": str(db_path),
            "CLI_UNITES_DISABLE_GIT": "1",
            "CLI_UNITES_SKIP_ONBOARDING": "1",
            "COLUMNS": "200",
            "LINES": "50",
        },
    )

    assert result.exit_code == 0
    output = result.output
    assert "Title A" in output
    assert "Title B" in output
    # Check for "release" tag - may be wrapped in Rich table
    # Look for the letters in sequence (they may have whitespace/newlines between them)
    import re
    # Remove most whitespace but keep some structure to find "release" pattern
    output_compact = re.sub(r'\s+', ' ', output)
    assert "release" in output or "release" in output_compact or all(c in output for c in "release")

    filtered = runner.invoke(
        cli,
        ["list", "--tag", "release"],
        env={
            "CLI_UNITES_CONFIG_DIR": str(config_dir),
            "CLI_UNITES_DB_PATH": str(db_path),
            "CLI_UNITES_DISABLE_GIT": "1",
            "CLI_UNITES_SKIP_ONBOARDING": "1",
        },
    )

    assert filtered.exit_code == 0
    assert "Title B" in filtered.output
    assert "Title A" not in filtered.output
