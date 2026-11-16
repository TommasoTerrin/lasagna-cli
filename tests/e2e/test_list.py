import json

import pytest
from typer.testing import CliRunner

import lasagna.cli

# Registry order is alpha, beta, gamma; beta is disabled.
REGISTRY_L = (
    'lasagna: "3.0"\n'
    "pipelines:\n"
    "  - id: alpha\n"
    "    path: pipelines/alpha\n"
    "  - id: beta\n"
    "    path: pipelines/beta\n"
    "    enabled: false\n"
    "  - id: gamma\n"
    "    path: pipelines/gamma\n"
)

DESCRIPTION_ALPHA = "Descrizione | con barra è è."

PIPELINE_ALPHA = f"""\
lasagna: "3.0"
id: alpha
name: "Alpha"
version: "1.0.0"
description: "{DESCRIPTION_ALPHA}"
entry: start
nodes:
  - id: start
    description: "Start."
    started_by: human
edges: []
"""

PIPELINE_BETA = """\
lasagna: "3.0"
id: beta
name: "Beta"
version: "2.0"
description: "Altro."
entry: start
nodes:
  - id: start
    description: "Start."
    started_by: agent
edges: []
"""

# gamma: no `version`; its entry node declares started_by: agent explicitly.
PIPELINE_GAMMA = """\
lasagna: "3.0"
id: gamma
name: "Gamma"
description: "Terza."
entry: start
nodes:
  - id: start
    description: "Start."
    started_by: agent
edges: []
"""

PIPELINES_L = {"alpha": PIPELINE_ALPHA, "beta": PIPELINE_BETA, "gamma": PIPELINE_GAMMA}

LIST_ENABLED = (
    "# Pipelines\n"
    "\n"
    "- alpha 1.0.0 started_by=human: Descrizione | con barra è è.\n"
    "- gamma - started_by=agent: Terza.\n"
)


def build_project_l(root, registry=REGISTRY_L, pipelines=None):
    lasagna_dir = root / ".lasagna"
    lasagna_dir.mkdir()
    (lasagna_dir / "pipelines.yaml").write_bytes(registry.encode("utf-8"))
    for name, text in (PIPELINES_L if pipelines is None else pipelines).items():
        pipeline_dir = lasagna_dir / "pipelines" / name
        pipeline_dir.mkdir(parents=True)
        (pipeline_dir / "pipeline.yaml").write_bytes(text.encode("utf-8"))


# AC-V3-020
def test_list_shows_enabled_pipelines_in_registry_order_without_disabled_ones(
    tmp_path, monkeypatch
):
    build_project_l(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["list"])

    assert result.exit_code == 0
    assert result.stdout == LIST_ENABLED
    assert "beta" not in result.stdout


LIST_ALL = (
    "# Pipelines\n"
    "\n"
    "- alpha 1.0.0 started_by=human: Descrizione | con barra è è.\n"
    "- beta 2.0 started_by=agent (disabled): Altro.\n"
    "- gamma - started_by=agent: Terza.\n"
)


# AC-V3-020
def test_list_all_marks_only_the_disabled_pipeline_with_disabled(tmp_path, monkeypatch):
    build_project_l(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["list", "--all"])

    assert result.exit_code == 0
    assert result.stdout == LIST_ALL
    assert result.stdout.count("(disabled)") == 1


# AC-V3-020
def test_list_builtin_prints_only_the_three_builtin_ids_sorted_not_the_project_list(
    tmp_path, monkeypatch
):
    build_project_l(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["list", "--builtin"])

    assert result.exit_code == 0
    lines = result.stdout.splitlines()
    assert lines[0] == "# Built-in pipelines"
    ids = [line[2:].split(" ")[0] for line in lines if line.startswith("- ")]
    assert ids == ["implementation", "project-manager", "quick-fix"]
    assert "alpha" not in result.stdout
    assert "gamma" not in result.stdout


ITEM_ALPHA_JSON = {
    "id": "alpha",
    "version": "1.0.0",
    "description": "Descrizione | con barra è è.",
    "started_by": "human",
    "enabled": True,
}
ITEM_BETA_JSON = {
    "id": "beta",
    "version": "2.0",
    "description": "Altro.",
    "started_by": "agent",
    "enabled": False,
}
ITEM_GAMMA_JSON = {
    "id": "gamma",
    "version": None,
    "description": "Terza.",
    "started_by": "agent",
    "enabled": True,
}


# AC-V3-020
def test_list_json_gives_exact_documents_with_enabled_only_for_project_pipelines(
    tmp_path, monkeypatch
):
    build_project_l(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    default = runner.invoke(lasagna.cli.app, ["list", "--json"])
    everything = runner.invoke(lasagna.cli.app, ["list", "--all", "--json"])
    builtin = runner.invoke(lasagna.cli.app, ["list", "--builtin", "--json"])

    for result in (default, everything, builtin):
        assert result.exit_code == 0
        assert result.stdout.endswith("\n")
    assert json.loads(default.stdout) == {
        "pipelines": [ITEM_ALPHA_JSON, ITEM_GAMMA_JSON]
    }
    assert json.loads(everything.stdout) == {
        "pipelines": [ITEM_ALPHA_JSON, ITEM_BETA_JSON, ITEM_GAMMA_JSON]
    }
    assert DESCRIPTION_ALPHA in default.stdout
    assert DESCRIPTION_ALPHA in everything.stdout
    assert "\\u00e8" not in default.stdout
    builtin_items = json.loads(builtin.stdout)["pipelines"]
    assert [item["id"] for item in builtin_items] == [
        "implementation",
        "project-manager",
        "quick-fix",
    ]
    assert all("enabled" not in item for item in builtin_items)


BROKEN_BETA_CASES = {
    "malformed-yaml": 'lasagna: "3.0"\nid: beta\nentry: [start\nnodes: {\n',
    "pipeline-yaml-missing": None,
    "entry-missing": PIPELINE_BETA.replace("entry: start\n", ""),
    "entry-names-no-node": PIPELINE_BETA.replace("entry: start", "entry: nowhere"),
}


# AC-V3-020
@pytest.mark.parametrize("case", list(BROKEN_BETA_CASES))
def test_list_stops_on_unreadable_pipeline_to_show_and_ignores_it_when_disabled(
    tmp_path, monkeypatch, case
):
    broken = BROKEN_BETA_CASES[case]
    pipelines = dict(PIPELINES_L)
    if broken is None:
        del pipelines["beta"]
    else:
        pipelines["beta"] = broken
    enabled_registry = REGISTRY_L.replace("    enabled: false\n", "")
    assert enabled_registry != REGISTRY_L
    build_project_l(tmp_path, registry=enabled_registry, pipelines=pipelines)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    shown = runner.invoke(lasagna.cli.app, ["list"])

    assert shown.exit_code == 1
    assert shown.exception is None or isinstance(shown.exception, SystemExit)
    assert shown.stdout == ""
    assert shown.stderr.strip() != ""
    assert "Traceback" not in shown.stderr
    assert "beta" in shown.stderr
    finding_lines = [line for line in shown.stderr.splitlines() if line.strip()]
    assert len(finding_lines) == len(set(finding_lines))
    if case == "pipeline-yaml-missing":
        assert shown.stderr.count("pipelines[1].path") == 1

    (tmp_path / ".lasagna" / "pipelines.yaml").write_bytes(REGISTRY_L.encode("utf-8"))

    ignored = runner.invoke(lasagna.cli.app, ["list"])
    stopped = runner.invoke(lasagna.cli.app, ["list", "--all"])

    assert ignored.exit_code == 0
    assert ignored.stdout == LIST_ENABLED
    assert "beta" not in ignored.stdout
    assert stopped.exit_code == 1
    assert stopped.stdout == ""
    assert stopped.stderr.strip() != ""
    assert "Traceback" not in stopped.stderr


# AC-V3-020
def test_list_builtin_outside_a_project_exits_2_naming_lasagna_dir(
    tmp_path, monkeypatch
):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    monkeypatch.chdir(empty_dir)
    resolved = empty_dir.resolve()
    if any((parent / ".lasagna").is_dir() for parent in resolved.parents):
        pytest.skip("an ancestor of tmp_path has a .lasagna/ directory")

    result = CliRunner().invoke(lasagna.cli.app, ["list", "--builtin"])

    assert result.exit_code == 2
    assert result.stdout == ""
    assert ".lasagna/" in result.stderr
    assert "Traceback" not in result.stderr
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert "Built-in pipelines" not in result.stderr


# AC-V3-020
def test_list_builtin_ignores_all_so_both_forms_print_identical_output(
    tmp_path, monkeypatch
):
    build_project_l(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    text = runner.invoke(lasagna.cli.app, ["list", "--builtin"])
    text_all = runner.invoke(lasagna.cli.app, ["list", "--builtin", "--all"])
    as_json = runner.invoke(lasagna.cli.app, ["list", "--builtin", "--json"])
    as_json_all = runner.invoke(
        lasagna.cli.app, ["list", "--builtin", "--all", "--json"]
    )

    for result in (text, text_all, as_json, as_json_all):
        assert result.exit_code == 0
    assert text_all.stdout == text.stdout
    assert as_json_all.stdout == as_json.stdout
    ids = [
        line[2:].split(" ")[0]
        for line in text_all.stdout.splitlines()
        if line.startswith("- ")
    ]
    assert ids == ["implementation", "project-manager", "quick-fix"]
    for output in (text.stdout, text_all.stdout, as_json.stdout, as_json_all.stdout):
        assert "(disabled)" not in output
        assert "alpha" not in output
        assert "beta" not in output
        assert "gamma" not in output
    assert text_all.stdout.splitlines()[0] == "# Built-in pipelines"
    assert [item["id"] for item in json.loads(as_json_all.stdout)["pipelines"]] == ids


# AC-V3-020
# AC-V3-021
def test_list_and_graph_stop_when_the_pipeline_id_differs_from_the_registry_id(
    tmp_path, monkeypatch
):
    registry = 'lasagna: "3.0"\npipelines:\n  - id: a\n    path: pipelines/a\n'
    pipeline = PIPELINE_ALPHA.replace("id: alpha", "id: zzz")
    build_project_l(tmp_path, registry=registry, pipelines={"a": pipeline})
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    for args in (["list"], ["graph", "a"]):
        result = runner.invoke(lasagna.cli.app, args)

        assert result.exit_code == 1
        assert result.stdout == ""
        assert "V05" in result.stderr
        assert "pipelines[0].id" in result.stderr
        assert "Traceback" not in result.stderr


# AC-V3-020
def test_list_with_duplicate_registry_ids_and_a_malformed_second_file_reports_without_crashing(
    tmp_path, monkeypatch
):
    registry = (
        'lasagna: "3.0"\n'
        "pipelines:\n"
        "  - id: a\n"
        "    path: pipelines/a\n"
        "  - id: a\n"
        "    path: pipelines/a2\n"
    )
    pipeline_a = PIPELINE_ALPHA.replace("id: alpha", "id: a")
    malformed = 'lasagna: "3.0"\nid: a\nentry: [start\nnodes: {\n'
    build_project_l(
        tmp_path, registry=registry, pipelines={"a": pipeline_a, "a2": malformed}
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["list"])

    assert result.exit_code == 1
    assert "Traceback" not in result.stderr
    assert "KeyError" not in result.stderr
    assert not isinstance(result.exception, KeyError)
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert "a2" in result.stderr
