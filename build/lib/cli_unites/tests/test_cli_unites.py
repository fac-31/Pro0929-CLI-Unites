from click.testing import CliRunner
from cli_unites.cli import cli


def test_version():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["--version"], env={"CLI_UNITES_SKIP_ONBOARDING": "1"})
        assert result.exit_code == 0
        assert result.output.startswith("cli, version ")
