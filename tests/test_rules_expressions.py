import shutil
from pathlib import Path

import pytest
from conftest import base_pipeline, write_pipeline

from lasagna_cli.issues import Issue
from lasagna_cli.loader import load_project
from lasagna_cli.validation.expr_rules import check_expressions

ROOT = Path(__file__).parent.parent
PIPE = ".lasagna/pipelines/p/p.yaml"
SHELL_MESSAGE = (
    "expressions are not allowed in shell commands; use environment variables"
)

BAD_ACTOR = """\
type: agent
name: bad
params:
  prompt:
    required: true
commands:
  check:
    - 'true'
    - 'echo ${{ inputs.a }}'
  inject: 'echo ${{ inputs.a }}'
  run: 'echo ${{ inputs.a }}'
  run_interactive: 'echo ${{ inputs.a }}'
  cleanup: 'echo ${{ inputs.a }}'
"""


def check(project):
    return check_expressions(load_project(project))


def agent_phase(d, index, prompt, **extra):
    """Make phase `index` a claude phase whose prompt is `prompt`."""
    base = d["phases"][index]
    phase = {"id": base["id"], "actor": "claude", "with": {"prompt": prompt}}
    if "needs" in base:
        phase["needs"] = base["needs"]
    phase.update(extra)
    d["phases"][index] = phase


def with_(index, **values):
    def apply(d):
        d["phases"][index].setdefault("with", {}).update(values)

    return apply


def phase_field(index, key, value):
    return lambda d: d["phases"][index].update({key: value})


CASES = {
    "E1-command": (
        with_(0, command="echo ${{ inputs.a }}"),
        PIPE,
        "phases[0].with.command",
        SHELL_MESSAGE,
    ),
    "E1-trigger-check": (
        phase_field(1, "trigger", {"by": "machine", "check": "echo ${{ inputs.a }}"}),
        PIPE,
        "phases[1].trigger.check",
        SHELL_MESSAGE,
    ),
    "E1-route-check": (
        phase_field(0, "route", {"by": "machine", "check": "${{ inputs.a }}"}),
        PIPE,
        "phases[0].route.check",
        SHELL_MESSAGE,
    ),
    "E1-loop-check": (
        phase_field(
            1,
            "loop",
            {"max_iterations": 2, "until": {"by": "machine", "check": "${{ x"}},
        ),
        PIPE,
        "phases[1].loop.until.check",
        SHELL_MESSAGE,
    ),
    "E2": (
        phase_field(0, "inputs", {"x": "${{ inputs.Bad }}"}),
        PIPE,
        "phases[0].inputs.x",
        "invalid expression: unknown reference 'inputs.Bad'",
    ),
    "E2-unclosed": (
        phase_field(0, "inputs", {"x": "${{ pipeline.inputs.a"}),
        PIPE,
        "phases[0].inputs.x",
        "invalid expression: unclosed '${{'",
    ),
    "E3-inputs-in-trigger": (
        phase_field(1, "trigger", {"by": "claude", "prompt": "${{ inputs.a }}"}),
        PIPE,
        "phases[1].trigger.prompt",
        "inputs.* is not allowed here",
    ),
    "E3-inputs-in-inputs": (
        phase_field(1, "inputs", {"x": "${{ inputs.a }}"}),
        PIPE,
        "phases[1].inputs.x",
        "inputs.* is not allowed here",
    ),
    "E3-outputs-in-with": (
        lambda d: agent_phase(d, 1, "${{ outputs.o }}"),
        PIPE,
        "phases[1].with.prompt",
        "outputs.* is not allowed here",
    ),
    "E3-outputs-in-trigger": (
        phase_field(1, "trigger", {"by": "claude", "prompt": "${{ outputs.o }}"}),
        PIPE,
        "phases[1].trigger.prompt",
        "outputs.* is not allowed here",
    ),
    "E3-outputs-in-inputs": (
        phase_field(1, "inputs", {"x": "${{ outputs.o }}"}),
        PIPE,
        "phases[1].inputs.x",
        "outputs.* is not allowed here",
    ),
    "E3-main-skill-in-pipeline-outputs": (
        lambda d: d.update(outputs={"r": "${{ harness.main_skill }}"}),
        PIPE,
        "outputs.r",
        "harness.main_skill is not allowed here",
    ),
    "E3-pipeline-inputs-in-pipeline-outputs": (
        lambda d: d.update(outputs={"r": "${{ pipeline.inputs.a }}"}),
        PIPE,
        "outputs.r",
        "pipeline.inputs.* is not allowed here",
    ),
    "E3-main-skill-in-inputs": (
        phase_field(1, "inputs", {"x": "${{ harness.main_skill }}"}),
        PIPE,
        "phases[1].inputs.x",
        "harness.main_skill is not allowed here",
    ),
    "E4a-descendant": (
        phase_field(0, "inputs", {"x": "${{ phases.b.outputs.o }}"}),
        PIPE,
        "phases[0].inputs.x",
        "phase 'b' is not an ancestor of 'a'",
    ),
    "E4a-self": (
        phase_field(1, "inputs", {"x": "${{ phases.b.outputs.o }}"}),
        PIPE,
        "phases[1].inputs.x",
        "phase 'b' is not an ancestor of 'b'",
    ),
    "E4b": (
        phase_field(1, "inputs", {"x": "${{ phases.a.outputs.nope }}"}),
        PIPE,
        "phases[1].inputs.x",
        "phase 'a' has no output 'nope'",
    ),
    "E4b-pipeline-outputs": (
        lambda d: d.update(outputs={"r": "${{ phases.a.outputs.nope }}"}),
        PIPE,
        "outputs.r",
        "phase 'a' has no output 'nope'",
    ),
    "E4-pipeline-outputs-unknown-phase": (
        lambda d: d.update(outputs={"r": "${{ phases.ghost.outputs.o }}"}),
        PIPE,
        "outputs.r",
        "unknown phase 'ghost'",
    ),
    "E5": (
        phase_field(0, "inputs", {"x": "${{ pipeline.inputs.zzz }}"}),
        PIPE,
        "phases[0].inputs.x",
        "pipeline has no input 'zzz'",
    ),
    "E6": (
        lambda d: agent_phase(d, 1, "${{ inputs.zzz }}"),
        PIPE,
        "phases[1].with.prompt",
        "phase 'b' has no input 'zzz'",
    ),
    "E7a": (
        phase_field(0, "route", {"by": "claude", "prompt": "${{ outputs.nope }}"}),
        PIPE,
        "phases[0].route.prompt",
        "phase 'a' has no output 'nope'",
    ),
    "E7a-loop": (
        phase_field(
            0,
            "loop",
            {
                "max_iterations": 2,
                "until": {"by": "claude", "instructions": "${{ outputs.nope }}"},
            },
        ),
        PIPE,
        "phases[0].loop.until.instructions",
        "phase 'a' has no output 'nope'",
    ),
    "E7b": (
        phase_field(
            0,
            "outputs",
            {
                "f": {"type": "file", "path": "f.txt"},
                "g": {"type": "file", "path": "${{ outputs.f }}"},
            },
        ),
        PIPE,
        "phases[0].outputs.g.path",
        "only value outputs are allowed in a file path",
    ),
    "E8": (
        lambda d: agent_phase(d, 1, "${{ harness.main_skill }}"),
        PIPE,
        "phases[1].with.prompt",
        "requires harness.main_skill: true",
    ),
    "E1-actor-check": (
        None,
        ".lasagna/actors/bad.yaml",
        "commands.check[1]",
        SHELL_MESSAGE,
    ),
    "E1-actor-inject": (
        None,
        ".lasagna/actors/bad.yaml",
        "commands.inject",
        SHELL_MESSAGE,
    ),
    "E1-actor-run": (None, ".lasagna/actors/bad.yaml", "commands.run", SHELL_MESSAGE),
    "E1-actor-run-interactive": (
        None,
        ".lasagna/actors/bad.yaml",
        "commands.run_interactive",
        SHELL_MESSAGE,
    ),
    "E1-actor-cleanup": (
        None,
        ".lasagna/actors/bad.yaml",
        "commands.cleanup",
        SHELL_MESSAGE,
    ),
}


@pytest.mark.parametrize("case", CASES)
def test_rule_reports_issue(project, case):
    fn, file, field, message = CASES[case]
    (project / ".lasagna/actors/bad.yaml").write_text(
        BAD_ACTOR, encoding="utf-8", newline="\n"
    )
    data = base_pipeline()
    if fn:
        fn(data)
    write_pipeline(project, data)
    assert Issue(file, field, message) in check(project)


def test_clean_actor_commands_are_not_reported(project):
    assert check(project) == []


def test_every_scope_is_valid_where_allowed(project):
    data = base_pipeline()
    data["inputs"] = {"a": {}}
    data["outputs"] = {"r": "${{ phases.b.outputs.v }}"}
    data["phases"][0]["outputs"] = {"v": {"type": "value"}}
    data["phases"][1] = {
        "id": "b",
        "needs": ["a"],
        "actor": "claude",
        "trigger": {
            "by": "claude",
            "prompt": "${{ pipeline.inputs.a }} ${{ phases.a.outputs.v }}",
        },
        "harness": {"main_skill": True},
        "inputs": {"x": "${{ phases.a.outputs.v }}", "y": "${{ pipeline.inputs.a }}"},
        "with": {"prompt": "${{ inputs.x }} ${{ harness.main_skill }}"},
        "outputs": {
            "v": {"type": "value"},
            "f": {"type": "file", "path": "d/${{ outputs.v }}/${{ inputs.y }}.md"},
        },
        "route": {"by": "claude", "prompt": "${{ outputs.f }} ${{ outputs.v }}"},
        "loop": {
            "max_iterations": 2,
            "until": {"by": "claude", "prompt": "${{ outputs.f }} ${{ inputs.x }}"},
        },
    }
    write_pipeline(project, data, main_skill=["b"])
    assert check(project) == []


def test_sub_pipeline_outputs_come_from_the_child(project):
    child = {
        "name": "q",
        "outputs": {"res": "${{ phases.x.outputs.v }}"},
        "phases": [
            {
                "id": "x",
                "actor": "machine",
                "with": {"command": "true"},
                "outputs": {"v": {"type": "value"}},
            }
        ],
    }
    write_pipeline(project, child)
    data = base_pipeline()
    data["phases"][1] = {"id": "b", "needs": ["a"], "pipeline": "q"}
    data["outputs"] = {
        "ok": "${{ phases.b.outputs.res }}",
        "bad": "${{ phases.b.outputs.v }}",
    }
    write_pipeline(project, data)
    found = check(project)
    assert Issue(PIPE, "outputs.bad", "phase 'b' has no output 'v'") in found
    assert not [i for i in found if i.field == "outputs.ok"]


def test_fixtures_and_example_have_no_expression_issues(project):
    pipelines = project / ".lasagna/pipelines"
    for folder in (ROOT / "tests/fixtures/pipelines").iterdir():
        shutil.copytree(folder, pipelines / folder.name)
    example = ROOT / "examples/pipelines/spec-to-code"
    shutil.copytree(example, pipelines / example.name)
    assert check(project) == []
