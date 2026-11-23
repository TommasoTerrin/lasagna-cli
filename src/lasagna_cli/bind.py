"""`--bind phase=actor`: replace the actor of a phase when a run starts."""

from collections.abc import Mapping
from dataclasses import replace

from lasagna_cli.model import Pipeline, Project
from lasagna_cli.validation.actors import check_with


class BindError(Exception):
    """A `--bind` item that is not `phase=actor`, or is given twice."""


def parse_bind(items: list[str]) -> dict[str, str]:
    """`phase=actor` items split on the first `=`."""
    bind: dict[str, str] = {}
    for item in items:
        phase, separator, actor = item.partition("=")
        if not separator or not phase or not actor:
            raise BindError(f"invalid --bind '{item}': expected phase=actor")
        if phase in bind:
            raise BindError(f"invalid --bind: phase '{phase}' is bound twice")
        bind[phase] = actor
    return bind


def check_bind(
    project: Project, pipeline: Pipeline, bind: Mapping[str, str]
) -> list[str]:
    """Why the binding is not allowed; an empty list when it is."""
    errors: list[str] = []
    ids = {phase.id for phase in pipeline.phases}
    for phase_id, actor_name in bind.items():
        label = f"--bind {phase_id}={actor_name}"
        if phase_id not in ids:
            errors.append(f"{label}: unknown phase '{phase_id}' in '{pipeline.name}'")
            continue
        actor = project.actors.get(actor_name)
        if actor is None:
            errors.append(f"{label}: unknown actor '{actor_name}'")
            continue
        phase = pipeline.phase(phase_id)
        original = project.actors.get(phase.actor) if phase.actor else None
        if original is None:
            errors.append(f"{label}: phase '{phase_id}' has no actor to replace")
            continue
        if actor.type != original.type:
            errors.append(
                f"{label}: actor '{actor_name}' is {_article(actor.type)}, "
                f"but phase '{phase_id}' is run by '{original.name}' "
                f"({_article(original.type)}); the type must be the same"
            )
            continue
        for field, message in check_with(
            actor, replace(phase, actor=actor_name), defaults_satisfy=True
        ):
            errors.append(f"{label}: {field}: {message}")
        if phase.interactive and not (
            actor.commands and actor.commands.run_interactive
        ):
            errors.append(
                f"{label}: phase '{phase_id}' is interactive and "
                f"'{actor_name}' has no commands.run_interactive"
            )
    return errors


def _article(kind: str) -> str:
    return f"a {kind}" if kind != "agent" else "an agent"
