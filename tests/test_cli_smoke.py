"""Smoke tests for the drumgen CLI: ensures every subcommand is wired."""

from __future__ import annotations

from typer.testing import CliRunner

from beatforge.cli.main import app

runner = CliRunner()

EXPECTED_SUBCOMMANDS = {
    "make-empty",
    "validate-midi",
    "generate-basic",
    "parse-prompt",
    "generate",
    "analyze",
    "groove",
    "edit",
    "generate-ml",
    "models",
}

# Subcommands that have already been wired with required options and therefore
# cannot be invoked with no arguments. They are still expected to appear in
# ``--help`` (verified by ``test_help_lists_all_expected_subcommands``).
IMPLEMENTED_SUBCOMMANDS = {
    "make-empty",
    "validate-midi",
    "generate-basic",
    "parse-prompt",
    "generate",
}


def test_help_exits_zero() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0, result.output


def test_help_lists_all_expected_subcommands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0, result.output
    for sub in EXPECTED_SUBCOMMANDS:
        assert sub in result.output, f"missing subcommand in --help: {sub}"


def test_each_stub_subcommand_exits_zero() -> None:
    for sub in EXPECTED_SUBCOMMANDS - IMPLEMENTED_SUBCOMMANDS:
        result = runner.invoke(app, [sub])
        assert result.exit_code == 0, f"{sub} exited {result.exit_code}: {result.output}"
