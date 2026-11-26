"""Actor params, sub-pipeline inputs and decider shapes."""

from lasagna_cli.issues import Issue
from lasagna_cli.model import Actor, Decider, Phase, Pipeline, Project


def check_actors(project: Project) -> list[Issue]:
    """Rules A1-A7 and D1-D3. Unknown actors and pipelines are skipped."""
    issues: list[Issue] = []
    for pipeline in project.pipelines.values():
        for phase in pipeline.phases:
            issues.extend(_phase(project, pipeline, phase))
    return issues


def _phase(project: Project, pipeline: Pipeline, phase: Phase) -> list[Issue]:
    prefix = f"phases[{phase.index}]"
    issues: list[Issue] = []

    def add(field: str, message: str) -> None:
        issues.append(Issue(pipeline.file, f"{prefix}.{field}", message))

    actor = project.actors.get(phase.actor) if phase.actor else None
    if actor is not None:
        for field, message in check_with(actor, phase):
            add(field, message)
        if phase.interactive and not (
            actor.commands is not None and actor.commands.run_interactive
        ):
            add("interactive", "requires an agent with commands.run_interactive")
        if phase.loop is not None and actor.type == "human":
            add(
                "loop",
                "not allowed on a phase run by a human: the phase is closed only "
                "when the person is done",
            )
        if phase.has_harness and actor.type != "agent":
            add("harness", "only allowed on phases run by an agent")
    child = project.pipelines.get(phase.pipeline) if phase.pipeline else None
    if child is not None:
        _check_sub_pipeline(child, phase, add)

    deciders = (
        ("trigger", phase.trigger),
        ("route", phase.route),
        ("loop.until", phase.loop.until if phase.loop else None),
    )
    for label, decider in deciders:
        if decider is not None and decider.by in project.actors:
            _check_decider(project.actors[decider.by], label, decider, add)
    return issues


def check_with(
    actor: Actor, phase: Phase, *, defaults_satisfy: bool = False
) -> list[tuple[str, str]]:
    """(field, message) for every `with` key the actor refuses or still needs.

    With `defaults_satisfy`, a required param that has a default may be omitted
    (the rule of `--bind`); validation of pipelines keeps the strict reading.
    """
    found: list[tuple[str, str]] = []
    keys = phase.with_
    if actor.type == "machine":
        if "command" not in keys:
            found.append(("with.command", "required for a machine actor"))
        for key in keys:
            if key != "command":
                found.append((f"with.{key}", "not allowed for a machine actor"))
    elif actor.type == "human":
        for key in keys:
            if key not in ("instructions", "command"):
                found.append((f"with.{key}", "not allowed for a human actor"))
    else:
        for key in keys:
            if key not in actor.params:
                found.append(
                    (f"with.{key}", f"agent '{actor.name}' has no param '{key}'")
                )
        for name, param in actor.params.items():
            if not param.required or name in keys:
                continue
            if not (defaults_satisfy and param.default is not None):
                found.append(
                    (
                        "with",
                        f"missing required param '{name}' for agent '{actor.name}'",
                    )
                )
    return found


def _check_sub_pipeline(child: Pipeline, phase: Phase, add) -> None:
    for name, declared in child.inputs.items():
        if declared.required and declared.default is None and name not in phase.inputs:
            add("inputs", f"missing input '{name}' required by pipeline '{child.name}'")
    for name in phase.inputs:
        if name not in child.inputs:
            add(f"inputs.{name}", f"pipeline '{child.name}' has no input '{name}'")


def _check_decider(actor: Actor, label: str, decider: Decider, add) -> None:
    def forbid(field: str, who: str) -> None:
        if getattr(decider, field) is not None:
            add(f"{label}.{field}", f"not allowed when {who} decides")

    if actor.type == "machine":
        forbid("prompt", "a machine")
        forbid("instructions", "a machine")
        if label in ("route", "loop.until") and decider.check is None:
            kind = "route" if label == "route" else "loop"
            add(f"{label}.check", f"required when a machine decides a {kind}")
    elif actor.type == "agent":
        if decider.prompt is None:
            add(f"{label}.prompt", "required when an agent decides")
        forbid("check", "an agent")
        forbid("instructions", "an agent")
    else:
        forbid("check", "a human")
        forbid("prompt", "a human")
