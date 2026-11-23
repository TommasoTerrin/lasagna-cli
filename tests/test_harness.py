from lasagna_cli.harness import dashed_name, harness_env, main_skill_path
from lasagna_cli.model import Phase, Pipeline


def make_phase(**overrides) -> Phase:
    fields: dict = {
        "index": 0,
        "id": "red",
        "needs": (),
        "actor": "claude",
        "pipeline": None,
        "interactive": False,
        "with_": {},
        "main_skill": False,
        "skills": (),
        "mcp": (),
        "inputs": {},
        "outputs": {},
        "trigger": None,
        "route": None,
        "loop": None,
        "timeout": None,
    }
    fields.update(overrides)
    return Phase(**fields)


def make_pipeline(phase: Phase, **overrides) -> Pipeline:
    fields: dict = {
        "name": "bug-fix",
        "dir": ".lasagna/pipelines/bug-fix",
        "file": ".lasagna/pipelines/bug-fix/pipeline.yaml",
        "trigger_by": (),
        "inputs": {},
        "outputs": {},
        "skills": (),
        "mcp": (),
        "phases": (phase,),
    }
    fields.update(overrides)
    return Pipeline(**fields)


def test_dashed_name_replaces_slashes() -> None:
    assert dashed_name("bug-fix/tdd/red") == "bug-fix-tdd-red"
    assert dashed_name("p/a") == "p-a"


def test_main_skill_path() -> None:
    phase = make_phase(main_skill=True)
    assert (
        main_skill_path(make_pipeline(phase), phase)
        == ".lasagna/pipelines/bug-fix/harness/phases/red/SKILL.md"
    )


def test_the_variables_of_a_full_harness() -> None:
    phase = make_phase(main_skill=True, skills=("tdd", "lint"), mcp=("git",))
    pipeline = make_pipeline(phase, skills=("base", "tdd"), mcp=("web",))
    assert harness_env(pipeline, phase, "bug-fix/tdd/red") == {
        "LASAGNA_MAIN_SKILL_DIR": ".lasagna/pipelines/bug-fix/harness/phases/red",
        "LASAGNA_MAIN_SKILL_NAME": "bug-fix-tdd-red",
        "LASAGNA_SKILLS": "\n".join(
            [
                ".lasagna/pipelines/bug-fix/harness/skills/base",
                ".lasagna/pipelines/bug-fix/harness/skills/tdd",
                ".lasagna/pipelines/bug-fix/harness/skills/lint",
            ]
        ),
        "LASAGNA_MCP": "\n".join(
            [
                ".lasagna/pipelines/bug-fix/harness/mcp/web.json",
                ".lasagna/pipelines/bug-fix/harness/mcp/git.json",
            ]
        ),
    }


def test_a_phase_without_harness_gives_no_variables() -> None:
    phase = make_phase()
    assert harness_env(make_pipeline(phase), phase, "bug-fix/red") == {}


def test_only_the_non_empty_variables_are_present() -> None:
    phase = make_phase(skills=("tdd",))
    env = harness_env(make_pipeline(phase), phase, "bug-fix/red")
    assert list(env) == ["LASAGNA_SKILLS"]


def test_paths_use_forward_slashes() -> None:
    phase = make_phase(main_skill=True, skills=("tdd",), mcp=("git",))
    env = harness_env(make_pipeline(phase), phase, "bug-fix/red")
    assert all("\\" not in value for value in env.values())
