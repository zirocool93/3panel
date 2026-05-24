from typer.testing import CliRunner

from app.cli.main import app


def test_cli_help_lists_diagnostic_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "doctor" in result.output
    assert "check-db" in result.output
    assert "check-redis" in result.output
