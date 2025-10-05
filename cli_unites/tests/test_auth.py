from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from cli_unites.cli import cli
from cli_unites.core.config import ConfigManager


def test_auth_updates_configuration(tmp_path: Path) -> None:
    runner = CliRunner()
    config_dir = tmp_path / "config"

    result = runner.invoke(
        cli,
        [
            "auth",
            "--token",
            "secret",
            "--team-id",
            "team-123",
            "--supabase-url",
            "https://example.supabase.co",
        ],
        env={"CLI_UNITES_CONFIG_DIR": str(config_dir)},
    )
    assert result.exit_code == 0, result.output

    manager = ConfigManager(config_dir=config_dir)
    stored = manager.as_dict()
    assert stored["auth_token"] == "secret"
    assert stored["team_id"] == "team-123"
    assert stored["supabase_url"] == "https://example.supabase.co"

    show = runner.invoke(
        cli,
        ["auth", "--show"],
        env={"CLI_UNITES_CONFIG_DIR": str(config_dir)},
    )
    assert show.exit_code == 0
    assert "team-123" in show.output
    assert "secret" in show.output
