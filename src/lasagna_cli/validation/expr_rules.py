"""Where `${{ }}` expressions may appear and what they may reference."""

from collections.abc import Callable

from lasagna_cli.expressions import ExpressionError, Ref, find_refs, has_expression
from lasagna_cli.issues import Issue
from lasagna_cli.model import Phase, Pipeline, Project

SHELL_MESSAGE = (
    "expressions are not allowed in shell commands; use environment variables"
)

OUTPUT_MESSAGE = (
    "lasagna.output is only allowed in the with of an agent phase"
    " and in the prompt of an agent decision"
)
OUTPUT = "lasagna.output"

_INPUTS = frozenset({"pipeline.inputs", "phases"})
_WITH = frozenset({"pipeline.inputs", "phases", "inputs", "harness.main_skill"})
_PATH = frozenset(
    {"pipeline.inputs", "phases", "inputs", "outputs", "harness.main_skill"}
)
_TRIGGER = frozenset({"pipeline.inputs", "phases", "harness.main_skill"})
_ALL = _PATH
_PIPELINE_OUTPUT = frozenset({"phases"})


def check_expressions(project: Project) -> list[Issue]:
    """Rules E1-E8, plus the ban on expressions in shell commands."""
    issues = _actor_commands(project)
    for pipeline in project.pipelines.values():
        issues.extend(_pipeline(project, pipeline))
    return issues


def _actor_commands(project: Project) -> list[Issue]:
    issues: list[Issue] = []
    for actor in project.actors.values():
        if actor.commands is None:
            continue
        fields: dict[str, str | None] = {
            f"commands.check[{j}]": c for j, c in enumerate(actor.commands.check)
        }
        fields["commands.inject"] = actor.commands.inject
        fields["commands.run"] = actor.commands.run
        fields["commands.run_interactive"] = actor.commands.run_interactive
        fields["commands.cleanup"] = actor.commands.cleanup
        for field, command in fields.items():
            if command is not None and has_expression(command):
                issues.append(Issue(actor.file, field, SHELL_MESSAGE))
    return issues


def _pipeline(project: Project, pipeline: Pipeline) -> list[Issue]:
    issues: list[Issue] = []

    def report(field: str, message: str) -> None:
        issues.append(Issue(pipeline.file, field, message))

    for name, text in pipeline.outputs.items():
        _scan(
            project, pipeline, None, f"outputs.{name}", text, _PIPELINE_OUTPUT, report
        )
    for phase in pipeline.phases:
        _phase(project, pipeline, phase, report)
    return issues


def _phase(
    project: Project,
    pipeline: Pipeline,
    phase: Phase,
    report: Callable[[str, str], None],
) -> None:
    prefix = f"phases[{phase.index}]"

    def scan(field: str, text: str | None, allowed: frozenset[str], path=False):
        if text is not None:
            _scan(
                project,
                pipeline,
                phase,
                f"{prefix}.{field}",
                text,
                allowed,
                report,
                path,
            )

    def shell(field: str, text: str | None) -> None:
        if text is not None and has_expression(text):
            report(f"{prefix}.{field}", SHELL_MESSAGE)

    with_allowed = _WITH | {OUTPUT} if _is_agent(project, phase.actor) else _WITH
    for key, text in phase.with_.items():
        if key == "command":
            shell("with.command", text)
        else:
            scan(f"with.{key}", text, with_allowed)
    for key, text in phase.inputs.items():
        scan(f"inputs.{key}", text, _INPUTS)
    for key, output in phase.outputs.items():
        scan(f"outputs.{key}.path", output.path, _PATH, path=True)
    deciders = (
        ("trigger", phase.trigger, _TRIGGER),
        ("route", phase.route, _ALL),
        ("loop.until", phase.loop.until if phase.loop else None, _ALL),
    )
    for label, decider, allowed in deciders:
        if decider is None:
            continue
        shell(f"{label}.check", decider.check)
        prompt_allowed = (
            allowed | {OUTPUT} if _is_agent(project, decider.by) else allowed
        )
        scan(f"{label}.prompt", decider.prompt, prompt_allowed)
        scan(f"{label}.instructions", decider.instructions, allowed)


def _is_agent(project: Project, actor: str | None) -> bool:
    found = project.actors.get(actor or "")
    return found is not None and found.type == "agent"


def _scan(
    project: Project,
    pipeline: Pipeline,
    phase: Phase | None,
    field: str,
    text: str,
    allowed: frozenset[str],
    report: Callable[[str, str], None],
    in_path: bool = False,
) -> None:
    try:
        refs = find_refs(text)
    except ExpressionError as error:
        report(field, f"invalid expression: {error}")
        return
    for ref in refs:
        if ref.scope == OUTPUT and OUTPUT not in allowed:
            report(field, OUTPUT_MESSAGE)
            continue
        if ref.scope not in allowed:
            suffix = "" if ref.scope == "harness.main_skill" else ".*"
            report(field, f"{ref.scope}{suffix} is not allowed here")
            continue
        message = _reference_problem(project, pipeline, phase, ref, in_path)
        if message:
            report(field, message)


def _reference_problem(
    project: Project,
    pipeline: Pipeline,
    phase: Phase | None,
    ref: Ref,
    in_path: bool,
) -> str | None:
    if ref.scope == "pipeline.inputs":
        if ref.name not in pipeline.inputs:
            return f"pipeline has no input '{ref.name}'"
    elif ref.scope == "phases":
        return _phase_reference(project, pipeline, phase, ref)
    elif phase is None:
        return None
    elif ref.scope == "inputs":
        if ref.name not in phase.inputs:
            return f"phase '{phase.id}' has no input '{ref.name}'"
    elif ref.scope == "outputs":
        output = phase.outputs.get(ref.name or "")
        if output is None:
            return f"phase '{phase.id}' has no output '{ref.name}'"
        if in_path and output.type == "file":
            return "only value outputs are allowed in a file path"
    elif ref.scope == "harness.main_skill" and not phase.main_skill:
        return "requires harness.main_skill: true"
    return None


def _phase_reference(
    project: Project, pipeline: Pipeline, phase: Phase | None, ref: Ref
) -> str | None:
    target = next((p for p in pipeline.phases if p.id == ref.phase), None)
    if phase is None:
        if target is None:
            return f"unknown phase '{ref.phase}'"
    elif ref.phase not in pipeline.ancestors(phase.id):
        return f"phase '{ref.phase}' is not an ancestor of '{phase.id}'"
    if target is None:
        return None
    if target.pipeline is not None:
        child = project.pipelines.get(target.pipeline)
        declared = set(child.outputs) if child is not None else None
    else:
        declared = set(target.outputs)
    if declared is not None and ref.name not in declared:
        return f"phase '{ref.phase}' has no output '{ref.name}'"
    return None
