"""Typed, immutable view of a `.lasagna/` folder."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from lasagna_cli.config import Config
from lasagna_cli.issues import Issue


@dataclass(frozen=True)
class Param:
    required: bool
    default: str | None


@dataclass(frozen=True)
class AgentCommands:
    check: tuple[str, ...]
    inject: str | None
    run: str
    run_interactive: str | None
    cleanup: str | None


@dataclass(frozen=True)
class Actor:
    name: str
    type: Literal["human", "machine", "agent"]
    file: str
    params: dict[str, Param]
    models: dict[str, str]
    commands: AgentCommands | None


@dataclass(frozen=True)
class Decider:
    by: str
    check: str | None
    prompt: str | None
    instructions: str | None


@dataclass(frozen=True)
class Output:
    type: Literal["file", "value"]
    path: str | None


@dataclass(frozen=True)
class Loop:
    max_iterations: int
    until: Decider


@dataclass(frozen=True)
class Phase:
    index: int
    id: str
    needs: tuple[str, ...]
    actor: str | None
    pipeline: str | None
    interactive: bool
    with_: dict[str, str]
    main_skill: bool
    skills: tuple[str, ...]
    mcp: tuple[str, ...]
    inputs: dict[str, str]
    outputs: dict[str, Output]
    trigger: Decider | None
    route: Decider | None
    loop: Loop | None
    timeout: str | None
    has_harness: bool = False


@dataclass(frozen=True)
class PipelineInput:
    required: bool
    default: str | None


@dataclass(frozen=True)
class Pipeline:
    name: str
    dir: str
    file: str
    trigger_by: tuple[str, ...]
    inputs: dict[str, PipelineInput]
    outputs: dict[str, str]
    skills: tuple[str, ...]
    mcp: tuple[str, ...]
    phases: tuple[Phase, ...]

    def phase(self, id: str) -> Phase:
        for phase in self.phases:
            if phase.id == id:
                return phase
        raise KeyError(id)

    def children(self, id: str) -> list[str]:
        """Ids of the phases that list `id` in their `needs`, in file order."""
        return [p.id for p in self.phases if id in p.needs]

    def ancestors(self, id: str) -> set[str]:
        """Ids reachable through `needs`, transitively."""
        needs = {p.id: p.needs for p in self.phases}
        found: set[str] = set()
        pending = list(needs.get(id, ()))
        while pending:
            current = pending.pop()
            if current in found:
                continue
            found.add(current)
            pending.extend(needs.get(current, ()))
        return found


@dataclass
class Project:
    root: Path
    config: Config
    actors: dict[str, Actor] = field(default_factory=dict)
    pipelines: dict[str, Pipeline] = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)
