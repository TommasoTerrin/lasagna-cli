import json
import os
import re
import subprocess

import pytest
from typer.testing import CliRunner

import lasagna.cli

REGISTRY_S = (
    'lasagna: "3.0"\n'
    "pipelines:\n"
    "  - id: demo\n"
    "    path: pipelines/demo\n"
    "    params:\n"
    '      cmd: "pytest -q"\n'
)

PIPELINE_S = """\
lasagna: "3.0"
id: demo
name: "Demo"
version: "1.0.0"
description: "Demo for {{ params.area }}."
params:
  area: { default: "core", description: "Area {{ params.area }}." }
  cmd: { default: "pytest" }
inputs:
  ticket: { description: "Ticket of {{ params.area }}." }
  note: { required: false }
outputs:
  line: { description: "A line." }
entry: first
nodes:
  - id: first
    name: "First"
    description: "Work on {{ inputs.ticket }} in {{ params.area }}."
    started_by: human
    steps:
      - "Read {{inputs.ticket}}."
      - "Keep {{ foo }} and ${{ github.x }}."
    resources:
      - { type: doc, ref: "$pipeline/assets/guide.md", description: "Guide for {{ inputs.ticket }}." }
      - { type: path, ref: "{{ inputs.ticket }}", access: write, required: false }
    gate:
      type: check
      run: "{{ params.cmd }} {{ inputs.ticket }}"
  - id: second
    description: "Second."
    gate: { type: human, message: "OK {{ inputs.ticket }}?" }
edges:
  - { type: direct, from: first, to: second }
  - { type: loop, from: second, to: first, when: "Redo {{ inputs.ticket }}", max_iterations: 2 }
"""

G_A = """\
# Demo
id: demo
version: 1.0.0
entry: first

Demo for core.

## Params
- area = "core" (default): Area core.
- cmd = "pytest -q" (registry)

## Inputs
- ticket (required): Ticket of core.
- note (optional)

## Outputs
- line: A line.

## Nodes
- first (First) started_by=human gate=check
- second (second) started_by=agent gate=human

## Edges
- first -> second
- second -> first [loop when: Redo a.md, max: 2]
"""

G_B = """# demo › first (First)
started_by: human

Work on a.md in core.

## Steps
1. Read a.md.
2. Keep {{ foo }} and ${{ github.x }}.

## Resources
- doc .lasagna/pipelines/demo/assets/guide.md (access: read, required): Guide for a.md.
- path a.md (access: write, optional)

## Gate
type: check
at: exit
by: self
run: pytest -q {{ inputs.ticket }}

## Outgoing edges
- first -> second

## Next nodes
- second (second)
"""

G_C = """# demo › first (First)
started_by: human

Work on {{ inputs.ticket }} in core.

## Steps
1. Read {{inputs.ticket}}.
2. Keep {{ foo }} and ${{ github.x }}.

## Resources
- doc .lasagna/pipelines/demo/assets/guide.md (access: read, required): Guide for {{ inputs.ticket }}.
- path {{ inputs.ticket }} (access: write, optional)

## Gate
type: check
at: exit
by: self
run: pytest -q {{ inputs.ticket }}

## Outgoing edges
- first -> second

## Next nodes
- second (second)
"""

G_D = """\
{
  "id": "demo",
  "name": "Demo",
  "version": "1.0.0",
  "description": "Demo for core.",
  "entry": "first",
  "params": {
    "area": {
      "value": "core",
      "source": "default",
      "description": "Area core."
    },
    "cmd": {
      "value": "pytest -q",
      "source": "registry",
      "description": null
    }
  },
  "inputs": {
    "ticket": {
      "required": true,
      "description": "Ticket of core."
    },
    "note": {
      "required": false,
      "description": null
    }
  },
  "outputs": {
    "line": {
      "description": "A line."
    }
  },
  "nodes": [
    {
      "id": "first",
      "name": "First",
      "started_by": "human",
      "gate": "check"
    },
    {
      "id": "second",
      "name": null,
      "started_by": "agent",
      "gate": "human"
    }
  ],
  "edges": [
    {
      "type": "direct",
      "from": "first",
      "to": "second"
    },
    {
      "type": "loop",
      "from": "second",
      "to": "first",
      "when": "Redo a.md",
      "max_iterations": 2
    }
  ]
}
"""

G_E = """\
{
  "pipeline": "demo",
  "node": {
    "id": "first",
    "description": "Work on a.md in core.",
    "name": "First",
    "started_by": "human",
    "steps": [
      "Read a.md.",
      "Keep {{ foo }} and ${{ github.x }}."
    ],
    "resources": [
      {
        "type": "doc",
        "ref": ".lasagna/pipelines/demo/assets/guide.md",
        "access": "read",
        "required": true,
        "description": "Guide for a.md."
      },
      {
        "type": "path",
        "ref": "a.md",
        "access": "write",
        "required": false,
        "description": null
      }
    ],
    "gate": {
      "type": "check",
      "at": "exit",
      "message": null,
      "run": "pytest -q {{ inputs.ticket }}",
      "criteria": null,
      "by": "self"
    }
  },
  "edges": [
    {
      "type": "direct",
      "from": "first",
      "to": "second"
    }
  ],
  "next": [
    {
      "id": "second",
      "name": null
    }
  ]
}
"""


def build_project_s(root, registry=REGISTRY_S, pipeline=PIPELINE_S, extra_pipelines=None):
    lasagna_dir = root / ".lasagna"
    demo_dir = lasagna_dir / "pipelines" / "demo"
    demo_dir.mkdir(parents=True)
    (lasagna_dir / "pipelines.yaml").write_bytes(registry.encode("utf-8"))
    (demo_dir / "pipeline.yaml").write_bytes(pipeline.encode("utf-8"))
    for name, text in (extra_pipelines or {}).items():
        extra_dir = lasagna_dir / "pipelines" / name
        extra_dir.mkdir(parents=True)
        (extra_dir / "pipeline.yaml").write_bytes(text.encode("utf-8"))


# AC-V3-018
# AC-V3-016
def test_show_pipeline_prints_overview_with_registry_params_and_inputs(tmp_path, monkeypatch):
    build_project_s(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["show", "demo", "--input", "ticket=a.md"])

    assert result.exit_code == 0
    assert result.stdout == G_A
    assert result.stderr == ""


# AC-V3-019
@pytest.mark.parametrize(
    ("extra_args", "expected"),
    [(["--input", "ticket=a.md"], G_B), ([], G_C)],
    ids=["with-input", "without-input"],
)
def test_show_node_prints_detail_substituting_only_declared_inputs(
    tmp_path, monkeypatch, extra_args, expected
):
    build_project_s(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["show", "demo", "first", *extra_args])

    assert result.exit_code == 0
    assert result.stdout == expected
    assert result.stderr == ""


# AC-V3-018
# AC-V3-019
@pytest.mark.parametrize(
    ("args", "expected"),
    [(["demo"], G_D), (["demo", "first"], G_E)],
    ids=["pipeline-overview", "node-detail"],
)
def test_show_json_prints_only_the_exact_json_document_on_stdout(
    tmp_path, monkeypatch, args, expected
):
    build_project_s(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        lasagna.cli.app, ["show", *args, "--json", "--input", "ticket=a.md"]
    )

    assert result.exit_code == 0
    assert result.stdout == expected
    assert result.stderr == ""


REGISTRY_HEAD = 'lasagna: "3.0"\npipelines:\n  - id: demo\n    path: pipelines/demo\n'
REGISTRY_CMD = '    params:\n      cmd: "pytest -q"\n'
REGISTRY_OTHER = "  - id: other\n    path: pipelines/other\n"

PIPELINE_V07_V10 = PIPELINE_S.replace("entry: first", "entry: ghost").replace(
    "edges:\n", "edges:\n  - { type: direct, from: first, to: second }\n", 1
)


# AC-V3-016
@pytest.mark.parametrize(
    ("registry", "check"),
    [
        (REGISTRY_HEAD, "default"),
        (REGISTRY_HEAD + '    params:\n      zz: "v"\n', "undeclared"),
    ],
    ids=["no-registry-params", "undeclared-registry-param"],
)
def test_show_json_params_origin_ignores_undeclared_registry_overrides(
    tmp_path, monkeypatch, registry, check
):
    build_project_s(tmp_path, registry=registry)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["show", "demo", "--json"])

    assert result.exit_code == 0
    params = json.loads(result.stdout)["params"]
    if check == "default":
        assert params["cmd"] == {"value": "pytest", "source": "default", "description": None}
    else:
        assert list(params) == ["area", "cmd"]


# AC-V3-018
@pytest.mark.parametrize("case", ["disabled", "faulty-other", "rule-violations"])
def test_show_ignores_validate_rules_and_other_entries_faults(tmp_path, monkeypatch, case):
    if case == "disabled":
        build_project_s(tmp_path, registry=REGISTRY_HEAD + "    enabled: false\n" + REGISTRY_CMD)
    elif case == "faulty-other":
        build_project_s(
            tmp_path,
            registry=REGISTRY_HEAD + REGISTRY_CMD + REGISTRY_OTHER,
            extra_pipelines={"other": "a: 1\nb: [1, 2\nc: 3\n"},
        )
    else:
        build_project_s(tmp_path, pipeline=PIPELINE_V07_V10)
    monkeypatch.chdir(tmp_path)

    args = ["show", "demo"] if case == "rule-violations" else ["show", "demo", "--input", "ticket=a.md"]
    result = CliRunner().invoke(lasagna.cli.app, args)

    assert result.exit_code == 0
    if case == "rule-violations":
        lines = result.stdout.splitlines()
        assert "entry: ghost" in lines
        assert lines.count("- first -> second") == 2
    else:
        assert result.stdout == G_A
    if case == "faulty-other":
        assert result.stderr == ""


# AC-V3-019
@pytest.mark.parametrize(
    ("args", "present", "absent"),
    [
        (["--input", "ticket=a.md", "--input", "ticket=b.md"], "Read b.md.", "a.md"),
        (["--input", "ticket=x=y"], "Read x=y.", None),
        (["--input", "note=n", "--input", "ticket=a.md"], "Read a.md.", None),
    ],
    ids=["last-wins", "value-with-equals", "two-declared-inputs"],
)
def test_show_input_repeated_last_wins_and_value_may_contain_equals(
    tmp_path, monkeypatch, args, present, absent
):
    build_project_s(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["show", "demo", "first", *args])

    assert result.exit_code == 0
    assert present in result.stdout
    if absent is not None:
        assert absent not in result.stdout


# AC-V3-019
@pytest.mark.parametrize("json_flag", [[], ["--json"]], ids=["text", "json"])
@pytest.mark.parametrize(
    ("args", "quoted"),
    [
        (["demo", "--input", "ticket"], "'ticket'"),
        (["demo", "first", "--input", "ghost=1"], "'ghost'"),
    ],
    ids=["no-equals", "undeclared-input"],
)
def test_show_input_usage_errors_exit_2_with_format_f_on_stderr(
    tmp_path, monkeypatch, args, quoted, json_flag
):
    build_project_s(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["show", *args, *json_flag])

    assert result.exit_code == 2
    assert result.stdout == ""
    line = result.stderr.splitlines()[0]
    assert line.startswith("error: ")
    message = line[len("error: "):]
    problem, fix = message.rsplit("; ", 1)
    assert problem.strip()
    assert re.fullmatch(r"[a-z]\S*( \S+)+\.", fix)
    assert quoted in message


# AC-V3-018
@pytest.mark.parametrize("args", [["show", "demo"], ["show", "demo", "--json"]], ids=["plain", "json"])
def test_show_exits_2_naming_lasagna_dir_when_no_project_found_in_both_modes(
    tmp_path, monkeypatch, args
):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    monkeypatch.chdir(empty_dir)
    resolved = empty_dir.resolve()
    if any((parent / ".lasagna").is_dir() for parent in resolved.parents):
        pytest.skip("an ancestor of tmp_path has a .lasagna/ directory")

    result = CliRunner().invoke(lasagna.cli.app, args)

    assert result.exit_code == 2
    assert ".lasagna/" in result.stderr
    assert result.stdout == ""


# AC-V3-018
@pytest.mark.parametrize("json_flag", [[], ["--json"]], ids=["text", "json"])
@pytest.mark.parametrize(
    ("case", "prefix"),
    [
        ("pipeline-malformed", "error V01 .lasagna/pipelines/demo/pipeline.yaml: "),
        ("pipeline-extra-key", "error V01 .lasagna/pipelines/demo/pipeline.yaml bogus: "),
        ("pipeline-missing", "error V05 .lasagna/pipelines.yaml pipelines[0].path: "),
        ("registry-malformed", "error V01 .lasagna/pipelines.yaml: "),
    ],
)
def test_show_unreadable_registry_or_pipeline_exits_1_with_validate_line_on_stderr(
    tmp_path, monkeypatch, case, prefix, json_flag
):
    if case == "pipeline-malformed":
        build_project_s(tmp_path, pipeline="a: 1\nb: [1, 2\nc: 3\n")
    elif case == "pipeline-extra-key":
        build_project_s(tmp_path, pipeline=PIPELINE_S + "bogus: 1\n")
    elif case == "pipeline-missing":
        build_project_s(tmp_path)
        (tmp_path / ".lasagna" / "pipelines" / "demo" / "pipeline.yaml").unlink()
    else:
        build_project_s(tmp_path, registry="a: [1\n")
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["show", "demo", *json_flag])

    assert result.exit_code == 1
    assert result.stdout == ""
    assert any(line.startswith(prefix) for line in result.stderr.splitlines()), result.stderr


def make_dir_link(link, target):
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        try:
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                check=True,
                capture_output=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            pytest.skip(f"cannot create a directory link: {exc}")


def pipeline_with_single_ref(ref):
    start = PIPELINE_S.index("    resources:\n")
    end = PIPELINE_S.index("    gate:\n      type: check")
    resource = f'    resources:\n      - {{ type: doc, ref: "{ref}" }}\n'
    return PIPELINE_S[:start] + resource + PIPELINE_S[end:]


# AC-V3-017
@pytest.mark.parametrize("json_flag", [[], ["--json"]], ids=["text", "json"])
@pytest.mark.parametrize(
    ("case", "quoted"),
    [
        ("dotdot", "'$pipeline/../../x'"),
        ("input-climbs", "'$pipeline/../../x'"),
        ("dir-link", "'$pipeline/assets/link/s.md'"),
    ],
)
def test_show_node_ref_leaving_pipeline_folder_exits_1_with_format_f_error(
    tmp_path, monkeypatch, case, quoted, json_flag
):
    extra = []
    if case == "dotdot":
        ref = "$pipeline/../../x"
    elif case == "input-climbs":
        ref = "$pipeline/{{ inputs.ticket }}"
        extra = ["--input", "ticket=../../x"]
    else:
        ref = "$pipeline/assets/link/s.md"
    build_project_s(tmp_path, pipeline=pipeline_with_single_ref(ref))
    if case == "dir-link":
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "s.md").write_text("s")
        assets = tmp_path / ".lasagna" / "pipelines" / "demo" / "assets"
        assets.mkdir()
        make_dir_link(assets / "link", outside)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["show", "demo", "first", *extra, *json_flag])

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr != ""
    line = result.stderr.splitlines()[0]
    assert line.startswith("error: ")
    message = line[len("error: "):]
    problem, fix = message.rsplit("; ", 1)
    assert problem.strip()
    assert re.fullmatch(r"[a-z]\S*( \S+)+\.", fix)
    assert quoted in message


# AC-V3-017
def test_show_node_ref_with_input_staying_inside_pipeline_folder_prints_resolved_path(
    tmp_path, monkeypatch
):
    build_project_s(tmp_path, pipeline=pipeline_with_single_ref("$pipeline/{{ inputs.ticket }}"))
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        lasagna.cli.app, ["show", "demo", "first", "--input", "ticket=assets/ok.md"]
    )

    assert result.exit_code == 0
    assert ".lasagna/pipelines/demo/assets/ok.md" in result.stdout


# AC-V3-017
def test_show_pipeline_overview_does_not_read_refs_even_when_one_leaves_the_folder(
    tmp_path, monkeypatch
):
    build_project_s(tmp_path, pipeline=pipeline_with_single_ref("$pipeline/../../x"))
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(lasagna.cli.app, ["show", "demo"])

    assert result.exit_code == 0


# AC-V3-017
@pytest.mark.parametrize(
    "registry_path", ["./pipelines/demo", "pipelines//demo"], ids=["dot-slash", "double-slash"]
)
def test_show_node_pipeline_ref_resolves_when_registry_path_is_not_normalized(
    tmp_path, monkeypatch, registry_path
):
    registry = REGISTRY_S.replace("path: pipelines/demo", f'path: "{registry_path}"')
    build_project_s(tmp_path, registry=registry)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        lasagna.cli.app, ["show", "demo", "first", "--input", "ticket=a.md"]
    )

    assert result.exit_code == 0, result.stderr
    assert ".lasagna/pipelines/demo/assets/guide.md" in result.stdout
