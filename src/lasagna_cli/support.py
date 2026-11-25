"""Features the engine does not run yet; `start` refuses pipelines that use them.

Only sub-pipelines are left; M5 removes them.
"""

from lasagna_cli.model import Phase, Project


def _phase_messages(phase: Phase) -> list[str]:
    if phase.pipeline is not None:
        return ["sub-pipelines are not supported yet"]
    return []


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
            for text in _phase_messages(phase):
                messages.append(f"phase '{phase.id}' of pipeline '{name}': {text}")
            if phase.pipeline is not None:
                pending.append(phase.pipeline)
    return messages
