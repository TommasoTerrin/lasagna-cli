import shutil
from pathlib import Path

import pytest
from conftest import base_pipeline, write_pipeline

from lasagna_cli.issues import Issue
from lasagna_cli.loader import load_project
from lasagna_cli.validation.actors import check_actors

ROOT = Path(__file__).parent.parent
PIPE = ".lasagna/pipelines/p/p.yaml"

NO_INTERACTIVE = """\
type: agent
name: plain
params:
  prompt:
    required: true
commands:
  run: echo "$LASAGNA_PARAM_PROMPT"
"""


def check(project):
    return check_actors(load_project(project))


def sub_pipeline(project):
    child = {
        "name": "q",
        "inputs": {"need": {}, "opt": {"required": False}, "dflt": {"default": "d"}},
        "phases": [{"id": "x", "actor": "machine", "with": {"command": "true"}}],
    }
    write_pipeline(project, child)
    data = base_pipeline()
    data["phases"][1] = {"id": "b", "needs": ["a"], "pipeline": "q"}
    return data


def prompt_agent(d, **extra):
    d["phases"][0].update(actor="claude", **extra)
    d["phases"][0]["with"] = {"prompt": "hi"}


def human(d, **with_):
    d["phases"][0].update(actor="human", **{"with": with_})


CASES = {
    "A1a": (
        lambda d: d["phases"][0].pop("with"),
        "phases[0].with.command",
        "required for a machine actor",
    ),
    "A1b": (
        lambda d: d["phases"][0]["with"].update(extra="x"),
        "phases[0].with.extra",
        "not allowed for a machine actor",
    ),
    "A2": (
        lambda d: human(d, instructions="x", extra="y"),
        "phases[0].with.extra",
        "not allowed for a human actor",
    ),
    "A3a": (
        lambda d: (prompt_agent(d), d["phases"][0]["with"].update(bogus="x")),
        "phases[0].with.bogus",
        "agent 'claude' has no param 'bogus'",
    ),
    "A3b": (
        lambda d: (prompt_agent(d), d["phases"][0]["with"].pop("prompt")),
        "phases[0].with",
        "missing required param 'prompt' for agent 'claude'",
    ),
    "A4-machine": (
        lambda d: d["phases"][0].update(interactive=True),
        "phases[0].interactive",
        "requires an agent with commands.run_interactive",
    ),
    "A4-no-run-interactive": (
        lambda d: (
            prompt_agent(d),
            d["phases"][0].update(actor="plain", interactive=True),
        ),
        "phases[0].interactive",
        "requires an agent with commands.run_interactive",
    ),
    "A5": (
        lambda d: d["phases"][0].update(harness={"main_skill": False}),
        "phases[0].harness",
        "only allowed on phases run by an agent",
    ),
    "D1a-prompt": (
        lambda d: d["phases"][1].update(trigger={"by": "machine", "prompt": "x"}),
        "phases[1].trigger.prompt",
        "not allowed when a machine decides",
    ),
    "D1a-instructions": (
        lambda d: d["phases"][1].update(trigger={"by": "machine", "instructions": "x"}),
        "phases[1].trigger.instructions",
        "not allowed when a machine decides",
    ),
    "D1a-loop": (
        lambda d: d["phases"][1].update(
            loop={"max_iterations": 2, "until": {"by": "machine", "prompt": "x"}}
        ),
        "phases[1].loop.until.prompt",
        "not allowed when a machine decides",
    ),
    "D1b": (
        lambda d: d["phases"][0].update(route={"by": "machine"}),
        "phases[0].route.check",
        "required when a machine decides a route",
    ),
    "D1c": (
        lambda d: d["phases"][1].update(
            loop={"max_iterations": 2, "until": {"by": "machine"}}
        ),
        "phases[1].loop.until.check",
        "required when a machine decides a loop",
    ),
    "D2a": (
        lambda d: d["phases"][1].update(trigger={"by": "claude"}),
        "phases[1].trigger.prompt",
        "required when an agent decides",
    ),
    "D2b-check": (
        lambda d: d["phases"][1].update(
            trigger={"by": "claude", "prompt": "p", "check": "true"}
        ),
        "phases[1].trigger.check",
        "not allowed when an agent decides",
    ),
    "D2b-instructions": (
        lambda d: d["phases"][0].update(
            route={"by": "claude", "prompt": "p", "instructions": "i"}
        ),
        "phases[0].route.instructions",
        "not allowed when an agent decides",
    ),
    "D3-check": (
        lambda d: d["phases"][1].update(trigger={"by": "human", "check": "true"}),
        "phases[1].trigger.check",
        "not allowed when a human decides",
    ),
    "D3-prompt": (
        lambda d: d["phases"][1].update(trigger={"by": "human", "prompt": "p"}),
        "phases[1].trigger.prompt",
        "not allowed when a human decides",
    ),
}


@pytest.mark.parametrize("case", CASES)
def test_rule_reports_issue(project, case):
    fn, field, message = CASES[case]
    (project / ".lasagna/actors/plain.yaml").write_text(
        NO_INTERACTIVE, encoding="utf-8", newline="\n"
    )
    data = base_pipeline()
    fn(data)
    write_pipeline(project, data)
    assert Issue(PIPE, field, message) in check(project)


def test_human_command_is_allowed(project):
    data = base_pipeline()
    human(data, instructions="x", command="true")
    write_pipeline(project, data)
    assert check(project) == []


def test_interactive_agent_with_run_interactive_is_allowed(project):
    data = base_pipeline()
    prompt_agent(data, interactive=True)
    write_pipeline(project, data)
    assert check(project) == []


def test_unknown_actor_is_skipped(project):
    data = base_pipeline()
    data["phases"][0].update(actor="ghost")
    data["phases"][1]["trigger"] = {"by": "ghost", "prompt": "p"}
    write_pipeline(project, data)
    assert check(project) == []


def test_missing_required_sub_pipeline_input(project):
    data = sub_pipeline(project)
    write_pipeline(project, data)
    assert Issue(
        PIPE, "phases[1].inputs", "missing input 'need' required by pipeline 'q'"
    ) in check(project)


def test_undeclared_sub_pipeline_input(project):
    data = sub_pipeline(project)
    data["phases"][1]["inputs"] = {"need": "x", "zzz": "y"}
    write_pipeline(project, data)
    found = check(project)
    assert (
        Issue(PIPE, "phases[1].inputs.zzz", "pipeline 'q' has no input 'zzz'") in found
    )
    assert not [i for i in found if i.field == "phases[1].inputs"]


def test_optional_and_defaulted_inputs_are_not_required(project):
    data = sub_pipeline(project)
    data["phases"][1]["inputs"] = {"need": "x"}
    write_pipeline(project, data)
    assert check(project) == []


def test_fixtures_and_example_have_no_actor_issues(project):
    pipelines = project / ".lasagna/pipelines"
    for folder in (ROOT / "tests/fixtures/pipelines").iterdir():
        shutil.copytree(folder, pipelines / folder.name)
    example = ROOT / "examples/pipelines/spec-to-code"
    shutil.copytree(example, pipelines / example.name)
    assert check(project) == []
