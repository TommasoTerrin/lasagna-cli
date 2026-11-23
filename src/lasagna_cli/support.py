"""Features the engine does not run yet; `start` refuses pipelines that use them.

Each later milestone removes its entries from `unsupported_features`:
M4 agents, loops, timeouts and interactive
phases, M5 sub-pipelines.
"""

from lasagna_cli.model import Decider, Phase, Project


def _decider_messages(project: Project, decider: Decider | None) -> list[str]:
    if decider is None:
        return []
    actor = project.actors.get(decider.by)
    if actor is None:
        return []
    if actor.type == "agent":
        return ["agent deciders are not supported yet"]
    return []


def _phase_messages(project: Project, phase: Phase) -> list[str]:
    messages: list[str] = []
    if phase.pipeline is not None:
        messages.append("sub-pipelines are not supported yet")
    if phase.interactive:
        messages.append("interactive phases are not supported yet")
    if phase.loop is not None:
        actor = project.actors.get(phase.actor) if phase.actor else None
        if actor is not None and actor.type == "human":
            messages.append("loop on a phase run by a human is not supported yet")
        messages.extend(_decider_messages(project, phase.loop.until))
    messages.extend(_decider_messages(project, phase.trigger))
    messages.extend(_decider_messages(project, phase.route))
    return list(dict.fromkeys(messages))


def unsupported_features(project: Project, pipeline: str) -> list[str]:
    """Messages for every refused feature in the pipeline and those it references."""
    messages: list[str] = []
    seen: set[str] = set()
    pending = [pipeline]
    while pending:
        name = pending.pop(0)
        if name in seen or name not in project.pipelines:
            continue
        seen.add(name)
        for phase in project.pipelines[name].phases:
            for text in _phase_messages(project, phase):
                messages.append(f"phase '{phase.id}' of pipeline '{name}': {text}")
            if phase.pipeline is not None:
                pending.append(phase.pipeline)
    return messages
