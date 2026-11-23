"""The harness of a phase: main skill path and the variables agents read."""

from lasagna_cli.model import Phase, Pipeline


def dashed_name(full_phase: str) -> str:
    """The full phase name with `/` replaced by `-` (`bug-fix/tdd/red`)."""
    return full_phase.replace("/", "-")


def _harness_dir(pipeline: Pipeline) -> str:
    return f".lasagna/pipelines/{pipeline.name}/harness"


def _phase_dir(pipeline: Pipeline, phase: Phase) -> str:
    return f"{_harness_dir(pipeline)}/phases/{phase.id}"


def main_skill_path(pipeline: Pipeline, phase: Phase) -> str:
    """Path of the phase's `SKILL.md`, relative to the worktree."""
    return f"{_phase_dir(pipeline, phase)}/SKILL.md"


def harness_env(pipeline: Pipeline, phase: Phase, full_phase: str) -> dict[str, str]:
    """`LASAGNA_MAIN_SKILL_*`, `LASAGNA_SKILLS` and `LASAGNA_MCP`.

    Variables with no value are absent, so `[ -z "$VAR" ]` works.
    """
    env: dict[str, str] = {}
    if phase.main_skill:
        env["LASAGNA_MAIN_SKILL_DIR"] = _phase_dir(pipeline, phase)
        env["LASAGNA_MAIN_SKILL_NAME"] = dashed_name(full_phase)
    base = _harness_dir(pipeline)
    skills = dict.fromkeys((*pipeline.skills, *phase.skills))
    mcp = dict.fromkeys((*pipeline.mcp, *phase.mcp))
    if skills:
        env["LASAGNA_SKILLS"] = "\n".join(f"{base}/skills/{name}" for name in skills)
    if mcp:
        env["LASAGNA_MCP"] = "\n".join(f"{base}/mcp/{name}.json" for name in mcp)
    return env
