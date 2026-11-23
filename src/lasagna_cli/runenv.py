"""What the engine modules share while driving one run.

Everything here reads the state, builds environments, runs user commands and
records failures. Nothing here decides what to run next. `RunContext`,
`EngineError`, `Runner` and the exit codes live here (and are re-exported by
`engine`) so that no module has to import `engine`.
"""

import os
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from lasagna_cli.eventlog import EventWriter, read_events
from lasagna_cli.gitops import local_git_env_vars
from lasagna_cli.model import Actor, Decider, Phase, Pipeline, Project
from lasagna_cli.outputs import new_output_file, parse_output_file
from lasagna_cli.resolve import Scope
from lasagna_cli.runner import build_env
from lasagna_cli.shell import to_bash_path
from lasagna_cli.state import PhaseState, RunState, derive_state

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_WAITING = 3
EXIT_INTERRUPTED = 130


class EngineError(Exception):
    """A situation the engine cannot handle; `start` refuses these up front."""


@dataclass
class RunContext:
    root: Path
    run_id: str
    pipeline: Pipeline
    project: Project
    worktree: Path
    inputs: dict[str, str]
    base_commit: str
    bind: dict[str, str] = field(default_factory=dict)


Runner = Callable[..., int]


class RunEnv:
    """The run being driven: its context, its log and the way commands are run."""

    def __init__(
        self,
        ctx: RunContext,
        writer: EventWriter,
        runner: Runner,
        platform: str = sys.platform,
    ) -> None:
        self.ctx = ctx
        self.writer = writer
        self.runner = runner
        self.platform = platform

    def state(self) -> RunState:
        return derive_state(read_events(self.writer.path))

    def full(self, phase_id: str) -> str:
        return f"{self.ctx.pipeline.name}/{phase_id}"

    def actor_name(self, phase: Phase) -> str | None:
        """The actor that runs the phase, after `--bind`."""
        return self.ctx.bind.get(phase.id, phase.actor)

    def actor(self, phase: Phase) -> Actor | None:
        name = self.actor_name(phase)
        return self.ctx.project.actors.get(name) if name else None

    def phase_state(self, state: RunState, phase_id: str) -> PhaseState | None:
        full = self.full(phase_id)
        return next((p for p in state.phases if p.phase == full), None)

    def done_outputs(self, state: RunState) -> dict[str, dict[str, str]]:
        prefix = f"{self.ctx.pipeline.name}/"
        return {
            p.phase.removeprefix(prefix): dict(p.outputs)
            for p in state.phases
            if p.state == "done"
        }

    def scope(self, state: RunState, **parts: dict[str, str] | None) -> Scope:
        return Scope(
            pipeline_inputs=self.ctx.inputs,
            phase_outputs=self.done_outputs(state),
            **parts,
        )

    def fail(
        self,
        phase_id: str,
        reason: str,
        detail: str | None = None,
        exit_code: int | None = None,
    ) -> int:
        fields: dict[str, object] = {"phase": self.full(phase_id), "reason": reason}
        if detail is not None:
            fields["detail"] = detail
        if exit_code is not None:
            fields["exit_code"] = exit_code
        self.writer.append("phase_failed", **fields)
        self.writer.append("run_completed", status="failed")
        return EXIT_FAILED

    def decider_kind(self, phase_id: str, decider: Decider) -> str:
        """ "human" or "machine"; agent deciders are refused at `start`."""
        actor = self.ctx.project.actors.get(decider.by)
        if actor is None or actor.type not in ("human", "machine"):
            raise EngineError(
                f"phase '{phase_id}': agent deciders are not supported yet"
            )
        return actor.type

    def wait(self, state: RunState, phase_id: str, kind: str, by: str) -> int:
        """Record that a human is awaited, once per wait, and return the exit code."""
        full = self.full(phase_id)
        if not any(w.phase == full and w.for_ == kind for w in state.waiting):
            self.writer.append("phase_waiting", phase=full, **{"for": kind}, by=by)
        return EXIT_WAITING

    def env(
        self,
        phase_id: str,
        output: Path,
        inputs: Mapping[str, str] | None = None,
        extra: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        ctx = self.ctx
        variables = {
            "LASAGNA_RUN_ID": ctx.run_id,
            "LASAGNA_PIPELINE": ctx.pipeline.name,
            "LASAGNA_PHASE": self.full(phase_id),
            "LASAGNA_ITERATION": "1",
            "LASAGNA_WORKTREE": to_bash_path(ctx.worktree.resolve()),
            "LASAGNA_OUTPUT": to_bash_path(output.resolve()),
            "LASAGNA_STATE": to_bash_path(self.writer.path.resolve()),
        }
        for name, value in (inputs or {}).items():
            variables[f"LASAGNA_INPUT_{name.upper().replace('-', '_')}"] = value
        variables.update(extra or {})
        return build_env(
            os.environ,
            variables,
            self.platform,
            drop=local_git_env_vars(),
        )

    def run_command(
        self,
        command: str,
        env: Mapping[str, str],
        *,
        inherit_stdin: bool = False,
        timeout: float | None = None,
    ) -> int:
        options: dict[str, object] = {}
        if timeout is not None:
            options["timeout"] = timeout
        return self.runner(
            command,
            cwd=self.ctx.worktree,
            env=env,
            inherit_stdin=inherit_stdin,
            bash_setting=self.ctx.project.config.shell,
            **options,
        )

    def run_check(
        self,
        phase_id: str,
        check: str,
        inputs: Mapping[str, str] | None = None,
    ) -> tuple[int, dict[str, str]]:
        output = new_output_file(self.ctx.worktree, self.ctx.run_id)
        code = self.run_command(check, self.env(phase_id, output, inputs))
        return code, parse_output_file(output)
