"""M8 — CLI: parser wiring + offline commands."""

from azmath.cli import main


def test_version(capsys):
    assert main(["version"]) == 0
    out = capsys.readouterr().out
    assert "azmath" in out and "python" in out


def test_unknown_command_fails():
    import pytest
    with pytest.raises(SystemExit):
        main(["frobnicate"])


def test_skills_stats(capsys):
    assert main(["skills", "stats"]) == 0
    assert "133" in capsys.readouterr().out


def test_skills_search(capsys):
    assert main(["skills", "search", "test suite"]) == 0
    out = capsys.readouterr().out
    assert "running-tests" in out


def test_tools_list(capsys):
    assert main(["tools", "list"]) == 0
    out = capsys.readouterr().out
    assert "fs.list" in out and "shell.run" in out


def test_config_shows_effective(capsys):
    assert main(["config"]) == 0
    assert "qwen3:4b" in capsys.readouterr().out
