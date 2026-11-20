import shutil
from pathlib import Path

import yaml

from lasagna_cli.issues import Issue
from lasagna_cli.loader import load_project
from lasagna_cli.model import Actor, AgentCommands, Param

FIXTURES = Path(__file__).parent / "fixtures" / "pipelines"


def install_fixtures(root: Path) -> None:
    for folder in FIXTURES.iterdir():
        shutil.copytree(folder, root / ".lasagna" / "pipelines" / folder.name)


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def test_loads_fixtures(project):
    install_fixtures(project)
    p = load_project(project)
    assert p.issues == []
    assert set(p.actors) == {"human", "machine", "claude", "opencode"}
    bug_fix = p.pipelines["bug-fix"]
    assert bug_fix.phase("triage").route.by == "claude"
    assert bug_fix.children("triage") == ["quick-fix", "tdd"]
    assert bug_fix.ancestors("review") == {
        "fetch-issue",
        "triage",
        "quick-fix",
        "tdd",
    }
    assert bug_fix.phase("tdd").pipeline == "tdd"
    assert bug_fix.dir == ".lasagna/pipelines/bug-fix"
    assert bug_fix.trigger_by == ("human", "claude")
    assert p.root == project


def test_phase_details_are_typed(project):
    install_fixtures(project)
    bug_fix = load_project(project).pipelines["bug-fix"]
    triage = bug_fix.phase("triage")
    assert triage.interactive is True and triage.main_skill is True
    assert triage.trigger.by == "human"
    assert triage.outputs["severity"].type == "value"
    assert triage.outputs["report"].path == "bugs/${{ inputs.issue }}/report.md"
    quick = bug_fix.phase("quick-fix")
    assert quick.loop.max_iterations == 3 and quick.loop.until.check == "npm test"
    assert quick.timeout == "30m"
    assert bug_fix.inputs["issue"].required is True
    assert bug_fix.skills == ("repo-conventions",)
    assert bug_fix.phase("fetch-issue").index == 0


def test_agent_actor_is_typed(project):
    actor = load_project(project).actors["claude"]
    assert isinstance(actor, Actor) and actor.type == "agent"
    assert actor.file == ".lasagna/actors/claude.yaml"
    assert actor.params["prompt"] == Param(required=True, default=None)
    assert actor.models["large"] == "opus"
    assert isinstance(actor.commands, AgentCommands)
    assert actor.commands.check == ("command -v claude",)
    assert actor.commands.run_interactive is not None
    assert actor.commands.inject is None and actor.commands.cleanup is None
    human = load_project(project).actors["human"]
    assert human.params == {} and human.models == {} and human.commands is None


def test_trigger_by_defaults_to_human(project):
    write(
        project,
        ".lasagna/pipelines/p/p.yaml",
        "name: p\nphases:\n  - id: a\n    actor: machine\n"
        "    with: {command: 'true'}\n",
    )
    assert load_project(project).pipelines["p"].trigger_by == ("human",)


def test_unknown_actor_type(project):
    write(project, ".lasagna/actors/x.yaml", "type: robot\nname: x\n")
    p = load_project(project)
    assert (
        Issue(
            ".lasagna/actors/x.yaml",
            "type",
            "unknown actor type 'robot' (extensions are not active in the MVP)",
        )
        in p.issues
    )
    assert "x" not in p.actors


def test_actor_without_type(project):
    write(project, ".lasagna/actors/x.yaml", "name: x\n")
    p = load_project(project)
    assert p.issues == [
        Issue(".lasagna/actors/x.yaml", "type", "missing required field 'type'")
    ]
    assert "x" not in p.actors


def test_duplicate_actor_name(project):
    write(project, ".lasagna/actors/zeta.yaml", "type: human\nname: human\n")
    p = load_project(project)
    assert p.issues == [
        Issue(
            ".lasagna/actors/zeta.yaml",
            "name",
            "duplicate actor name 'human' (also in .lasagna/actors/human.yaml)",
        )
    ]
    assert p.actors["human"].file == ".lasagna/actors/human.yaml"


def test_actor_schema_error_excludes_actor(project):
    write(project, ".lasagna/actors/bad.yaml", "type: agent\nname: bad\n")
    p = load_project(project)
    assert "bad" not in p.actors
    assert {i.file for i in p.issues} == {".lasagna/actors/bad.yaml"}


def test_missing_pipeline_file(project):
    (project / ".lasagna/pipelines/empty").mkdir()
    assert load_project(project).issues == [
        Issue(".lasagna/pipelines/empty", "", "missing pipeline file empty.yaml")
    ]


def test_pipeline_name_must_match_folder(project):
    write(
        project,
        ".lasagna/pipelines/x/x.yaml",
        "name: y\nphases:\n  - id: a\n    actor: machine\n",
    )
    p = load_project(project)
    assert p.issues == [
        Issue(".lasagna/pipelines/x/x.yaml", "name", "must match the folder name 'x'")
    ]
    assert p.pipelines == {}


def test_invalid_yaml_in_pipeline(project):
    write(project, ".lasagna/pipelines/x/x.yaml", "name: [x\n")
    (issue,) = load_project(project).issues
    assert (issue.file, issue.field) == (".lasagna/pipelines/x/x.yaml", "")
    assert issue.message.startswith("invalid YAML: ")


def test_non_mapping_document(project):
    write(project, ".lasagna/pipelines/x/x.yaml", "- a\n- b\n")
    assert load_project(project).issues == [
        Issue(".lasagna/pipelines/x/x.yaml", "", "must be a mapping")
    ]


def test_schema_error_excludes_pipeline(project):
    data = {
        "name": "x",
        "phases": [
            {"id": "a", "actor": "machine", "interactive": True, "timeout": "1m"}
        ],
    }
    write(project, ".lasagna/pipelines/x/x.yaml", yaml.safe_dump(data))
    p = load_project(project)
    assert "x" not in p.pipelines
    assert [i.field for i in p.issues] == ["phases[0].timeout"]
    assert p.issues[0].file == ".lasagna/pipelines/x/x.yaml"


def test_config_is_loaded(project):
    write(project, ".lasagna/config/lasagna.yaml", "limits:\n  max_depth: 1\n")
    assert load_project(project).config.max_depth == 1
