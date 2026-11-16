import re

import pytest
from typer.testing import CliRunner

import lasagna.cli

MALFORMED_YAML = 'lasagna: "3.0"\npipelines: [\n'
UNKNOWN_KEY_ENTRY = (
    'lasagna: "3.0"\n'
    "pipelines:\n"
    "  - { id: demo, path: pipelines/demo, bogus: 1 }\n"
)


def assert_registry_failure(result):
    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr != ""
    assert "pipelines.yaml" in result.stderr
    assert "Traceback" not in result.stderr
    assert result.exception is None or isinstance(result.exception, SystemExit)


# AC-V3-020
# AC-V3-021
@pytest.mark.parametrize(
    "registry", [MALFORMED_YAML, UNKNOWN_KEY_ENTRY], ids=["malformed", "unknown-key"]
)
def test_unreadable_registry_fails_list_and_graph_but_not_list_builtin(
    tmp_path, monkeypatch, registry
):
    lasagna_dir = tmp_path / ".lasagna"
    lasagna_dir.mkdir()
    (lasagna_dir / "pipelines.yaml").write_bytes(registry.encode("utf-8"))
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    assert_registry_failure(runner.invoke(lasagna.cli.app, ["list"]))
    assert_registry_failure(runner.invoke(lasagna.cli.app, ["graph", "demo"]))
    assert_registry_failure(runner.invoke(lasagna.cli.app, ["graph", "nope"]))

    builtin = runner.invoke(lasagna.cli.app, ["list", "--builtin"])
    assert builtin.exit_code == 0
    ids = re.findall(r"^- (\S+) ", builtin.stdout, flags=re.MULTILINE)
    assert sorted(ids) == ["implementation", "project-manager", "quick-fix"]
