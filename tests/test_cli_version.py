from conftest import invoke

from lasagna_cli.cli import app


def app_command_names() -> list[str]:
    return [c.name or c.callback.__name__ for c in app.registered_commands]


def test_version_prints_name_and_version():
    result = invoke("--version")
    assert result.exit_code == 0
    assert result.output == "lasagna 0.1.0\n"


def test_help_lists_commands():
    result = invoke("--help")
    assert result.exit_code == 0
    for name in app_command_names():
        assert name in result.output
