"""Startup-failure UX (spec Phase-2 gotcha, fixed in Phase 4): a server that
won't start prints one friendly line and exits 1 — never an anyio traceback."""

from typer.testing import CliRunner

from mcpdoctor.cli import app

runner = CliRunner()


def _all_output(result) -> str:
    """click >=8.2 captures stdout/stderr separately; combine them."""
    text = result.output or ""
    try:
        if result.stderr:
            text += result.stderr
    except ValueError:
        pass  # stderr not separately captured in this click build
    return text


def test_bad_spec_exits_one_with_friendly_line():
    result = runner.invoke(app, ["doctor", "fixtures/does_not_exist.py"])
    out = _all_output(result)
    assert result.exit_code == 1
    assert "Could not start MCP server" in out
    assert "fixtures/does_not_exist.py" in out
    assert "run that command by hand" in out


def test_bad_spec_shows_no_python_traceback():
    result = runner.invoke(app, ["doctor", "fixtures/does_not_exist.py"])
    out = _all_output(result)
    # the whole point: the ugly anyio/Python traceback must not reach the user
    assert "Traceback (most recent call last)" not in out
    assert "anyio" not in out
