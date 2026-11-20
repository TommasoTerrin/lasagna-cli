import shutil
from pathlib import Path

import pytest
from conftest import base_pipeline, write_pipeline

from lasagna_cli.issues import Issue
from lasagna_cli.loader import load_project
from lasagna_cli.validation import validate_project
from lasagna_cli.validation.references import check_references

FIXTURES = Path(__file__).parent / "fixtures" / "pipelines"
PIPE = ".lasagna/pipelines/p/p.yaml"


def machine(id_, *needs, **extra):
    phase = {"id": id_, "actor": "machine", "with": {"command": "true"}, **extra}
    if needs:
        phase["needs"] = list(needs)
    return phase


def issues_of(project):
    return validate_project(load_project(project))


def mutated(fn):
    data = base_pipeline()
    fn(data)
    return data


def set_max_depth(project, depth):
    path = project / ".lasagna/config/lasagna.yaml"
    path.write_text(f"version: 1\nlimits:\n  max_depth: {depth}\n", encoding="utf-8")


def test_base_pipeline_is_clean(project):
    write_pipeline(project, base_pipeline())
    assert issues_of(project) == []


def test_fixtures_have_no_reference_issues(project):
    for folder in FIXTURES.iterdir():
        shutil.copytree(folder, project / ".lasagna/pipelines" / folder.name)
    assert check_references(load_project(project)) == []


CASES = {
    "R1": (
        lambda d: d["phases"][0].update(actor="ghost"),
        "phases[0].actor",
        "unknown actor 'ghost'",
    ),
    "R2-trigger": (
        lambda d: d["phases"][1].update(trigger={"by": "ghost"}),
        "phases[1].trigger.by",
        "unknown actor 'ghost'",
    ),
    "R2-route": (
        lambda d: d["phases"][1].update(route={"by": "ghost", "prompt": "x"}),
        "phases[1].route.by",
        "unknown actor 'ghost'",
    ),
    "R2-loop": (
        lambda d: d["phases"][1].update(
            loop={"max_iterations": 2, "until": {"by": "ghost", "prompt": "x"}}
        ),
        "phases[1].loop.until.by",
        "unknown actor 'ghost'",
    ),
    "R3": (
        lambda d: d.update(trigger={"by": ["human", "ghost"]}),
        "trigger.by",
        "unknown actor 'ghost'",
    ),
    "R4": (
        lambda d: d["phases"].__setitem__(
            1, {"id": "b", "needs": ["a"], "pipeline": "nope"}
        ),
        "phases[1].pipeline",
        "unknown pipeline 'nope'",
    ),
    "R5": (
        lambda d: d["phases"][1].update(id="a"),
        "phases[1].id",
        "duplicate phase id 'a'",
    ),
    "R6": (
        lambda d: d["phases"][1].update(needs=["ghost"]),
        "phases[1].needs",
        "unknown phase 'ghost'",
    ),
    "R7-two-starts": (
        lambda d: d["phases"][1].pop("needs"),
        "phases",
        "exactly one phase without needs is required, found 2",
    ),
    "R7-no-start": (
        lambda d: d["phases"][0].update(needs=["b"]),
        "phases",
        "exactly one phase without needs is required, found 0",
    ),
    "R8": (
        lambda d: d["phases"].extend([machine("c", "a", "d"), machine("d", "c")]),
        "phases",
        "cycle between phases: c -> d -> c",
    ),
    "R9a": (
        lambda d: d["phases"].append(machine("c", "a")),
        "phases[0]",
        "phase 'a' has 2 children and needs a route",
    ),
    "R9b": (
        lambda d: d["phases"][0].update(route={"by": "machine", "check": "true"}),
        "phases[0].route",
        "route is only allowed on a phase with more than one child",
    ),
    "R12": (
        lambda d: d["phases"][0].update(harness={"main_skill": True}),
        "phases[0].harness.main_skill",
        "missing harness/phases/a/SKILL.md",
    ),
    "R13-phase": (
        lambda d: d["phases"][0].update(harness={"skills": ["s1"]}),
        "phases[0].harness.skills",
        "missing skill 's1' (harness/skills/s1/SKILL.md)",
    ),
    "R13-pipeline": (
        lambda d: d.update(harness={"skills": ["s1"]}),
        "harness.skills",
        "missing skill 's1' (harness/skills/s1/SKILL.md)",
    ),
    "R14-phase": (
        lambda d: d["phases"][0].update(harness={"mcp": ["m1"]}),
        "phases[0].harness.mcp",
        "missing MCP file 'm1' (harness/mcp/m1.json)",
    ),
    "R14-pipeline": (
        lambda d: d.update(harness={"mcp": ["m1"]}),
        "harness.mcp",
        "missing MCP file 'm1' (harness/mcp/m1.json)",
    ),
}


@pytest.mark.parametrize("case", CASES)
def test_rule_reports_issue(project, case):
    fn, field, message = CASES[case]
    write_pipeline(project, mutated(fn))
    assert Issue(PIPE, field, message) in issues_of(project)


def test_existing_harness_files_are_accepted(project):
    data = base_pipeline()
    data["harness"] = {"skills": ["s1"], "mcp": ["m1"]}
    data["phases"][0] = {
        "id": "a",
        "actor": "claude",
        "with": {"prompt": "hi"},
        "harness": {"main_skill": True, "skills": ["s2"], "mcp": ["m2"]},
    }
    write_pipeline(
        project, data, main_skill=["a"], skills=["s1", "s2"], mcp=["m1", "m2"]
    )
    assert issues_of(project) == []


def sub(name, child):
    data = {
        "name": name,
        "phases": [{"id": "x", "pipeline": child}] if child else [machine("x")],
    }
    return data


def test_pipeline_cycle(project):
    write_pipeline(project, sub("p", "q"))
    write_pipeline(project, sub("q", "p"))
    found = issues_of(project)
    assert (
        Issue(PIPE, "phases[0].pipeline", "cycle between pipelines: p -> q -> p")
        in found
    )
    assert not [i for i in found if "nesting depth" in i.message]


def test_pipeline_self_cycle(project):
    write_pipeline(project, sub("p", "p"))
    assert Issue(
        PIPE, "phases[0].pipeline", "cycle between pipelines: p -> p"
    ) in issues_of(project)


def test_nesting_depth_exceeded(project):
    set_max_depth(project, 1)
    write_pipeline(project, sub("p", "q"))
    write_pipeline(project, sub("q", "r"))
    write_pipeline(project, sub("r", None))
    assert Issue(
        PIPE, "phases[0].pipeline", "nesting depth 2 exceeds limits.max_depth 1"
    ) in issues_of(project)


def test_nesting_depth_zero_forbids_sub_pipelines(project):
    set_max_depth(project, 0)
    write_pipeline(project, sub("p", "q"))
    write_pipeline(project, sub("q", None))
    assert Issue(
        PIPE, "phases[0].pipeline", "nesting depth 1 exceeds limits.max_depth 0"
    ) in issues_of(project)


def test_nesting_within_limit_is_accepted(project):
    set_max_depth(project, 2)
    write_pipeline(project, sub("p", "q"))
    write_pipeline(project, sub("q", "r"))
    write_pipeline(project, sub("r", None))
    assert not [i for i in issues_of(project) if "nesting" in i.message]


def test_validate_project_sorts_by_file_then_field(project):
    data = base_pipeline()
    data["phases"][1]["needs"] = ["ghost"]
    data["phases"][0]["actor"] = "ghost"
    write_pipeline(project, data)
    found = issues_of(project)
    assert found == sorted(found, key=lambda i: (i.file, i.field))


def test_issues_use_natural_order(tmp_path):
    from lasagna_cli.config import Config
    from lasagna_cli.model import Project

    given = [
        Issue("a.yaml", "phases[10].id", "x"),
        Issue("a.yaml", "phases[2].id", "x"),
        Issue("a.yaml", "phases[2]", "x"),
        Issue("a.yaml", "phases[1].id", "x"),
    ]
    project = Project(root=tmp_path, config=Config(), issues=given)
    found = [i.field for i in validate_project(project) if i.file == "a.yaml"]
    assert found == ["phases[1].id", "phases[2]", "phases[2].id", "phases[10].id"]
