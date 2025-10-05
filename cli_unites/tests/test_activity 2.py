from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from cli_unites.cli import cli


def test_activity_defaults_to_current_team(tmp_path: Path) -> None:
    runner = CliRunner()
    config_dir = tmp_path / "config"
    db_path = config_dir / "notes.db"

    # Seed notes for two teams
    for title, team_id in ("Alpha", "team-a"), ("Beta", "team-b"):
        runner.invoke(
            cli,
            ["team", "--set", team_id],
            env={
                "CLI_UNITES_CONFIG_DIR": str(config_dir),
                "CLI_UNITES_SKIP_ONBOARDING": "1",
            },
        )
        result = runner.invoke(
            cli,
            ["add", title, "--body", f"Body for {title}"],
            env={
                "CLI_UNITES_CONFIG_DIR": str(config_dir),
                "CLI_UNITES_DB_PATH": str(db_path),
                "CLI_UNITES_DISABLE_GIT": "1",
                "CLI_UNITES_SKIP_ONBOARDING": "1",
            },
        )
        assert result.exit_code == 0, result.output

    # Switch to team-a and ensure activity only shows that note
    runner.invoke(
        cli,
        ["team", "--set", "team-a"],
        env={
            "CLI_UNITES_CONFIG_DIR": str(config_dir),
            "CLI_UNITES_SKIP_ONBOARDING": "1",
        },
    )

    result = runner.invoke(
        cli,
        ["activity", "--limit", "5"],
        env={
            "CLI_UNITES_CONFIG_DIR": str(config_dir),
            "CLI_UNITES_DB_PATH": str(db_path),
            "CLI_UNITES_SKIP_ONBOARDING": "1",
        },
    )
    assert result.exit_code == 0, result.output
    assert "Alpha" in result.output
    assert "Beta" not in result.output
