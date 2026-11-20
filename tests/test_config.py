from pathlib import Path

import pytest

from lasagna_cli.config import Config, load_config
from lasagna_cli.issues import Issue
from lasagna_cli.project import templates_dir

LABEL = ".lasagna/config/lasagna.yaml"


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "lasagna.yaml"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def test_template_config_loads_without_issues():
    config, issues = load_config(templates_dir() / "config/lasagna.yaml", LABEL)
    assert config == Config()
    assert issues == []


def test_valid_overrides_are_applied(tmp_path):
    path = write(
        tmp_path,
        "version: 1\nlimits:\n  max_depth: 0\nworktrees:\n  dir: wt\n"
        "  branch_prefix: x/\n",
    )
    config, issues = load_config(path, LABEL)
    assert issues == []
    assert config == Config(max_depth=0, worktrees_dir="wt", branch_prefix="x/")


ABSOLUTE = "C:/Git/bin/bash.exe" if Path("C:/").anchor == "C:\\" else "/bin/bash"


def test_absolute_shell_is_accepted(tmp_path):
    config, issues = load_config(write(tmp_path, f"shell: {ABSOLUTE}\n"), LABEL)
    assert issues == [] and config.shell == ABSOLUTE


@pytest.mark.parametrize(
    ("text", "field", "message"),
    [
        ("version: 2\n", "version", "must be 1"),
        ("version: true\n", "version", "must be 1"),
        ("shell: bash\n", "shell", 'must be "auto" or an absolute path'),
        ("shell: 3\n", "shell", 'must be "auto" or an absolute path'),
        ("limits:\n  max_depth: -1\n", "limits.max_depth", "must be an integer >= 0"),
        ("limits:\n  max_depth: true\n", "limits.max_depth", "must be an integer >= 0"),
        ("limits:\n  max_depth: '2'\n", "limits.max_depth", "must be an integer >= 0"),
        (
            "worktrees:\n  dir: ''\n",
            "worktrees.dir",
            "must be a non-empty relative path",
        ),
        (
            "worktrees:\n  dir: /abs/wt\n",
            "worktrees.dir",
            "must be a non-empty relative path",
        ),
        (
            "worktrees:\n  branch_prefix: ''\n",
            "worktrees.branch_prefix",
            "must be a non-empty string",
        ),
        ("limits:\n  foo: 1\n", "limits.foo", "unknown key"),
        ("worktrees:\n  foo: 1\n", "worktrees.foo", "unknown key"),
        ("foo: 1\n", "foo", "unknown key"),
        ("limits: 3\n", "limits", "must be a mapping"),
    ],
)
def test_invalid_values(tmp_path, text, field, message):
    _, issues = load_config(write(tmp_path, text), LABEL)
    assert issues == [Issue(LABEL, field, message)]


def test_invalid_value_falls_back_to_default(tmp_path):
    config, _ = load_config(write(tmp_path, "limits:\n  max_depth: -1\n"), LABEL)
    assert config.max_depth == Config().max_depth


def test_missing_file(tmp_path):
    config, issues = load_config(tmp_path / "nope.yaml", LABEL)
    assert config == Config()
    assert issues == [Issue(LABEL, "", "missing config/lasagna.yaml")]


def test_invalid_yaml(tmp_path):
    config, issues = load_config(write(tmp_path, "a: [1, 2\n"), LABEL)
    assert config == Config()
    assert len(issues) == 1 and issues[0].field == ""
    assert issues[0].message.startswith("invalid YAML: ")


def test_empty_file_gives_defaults(tmp_path):
    assert load_config(write(tmp_path, ""), LABEL) == (Config(), [])
