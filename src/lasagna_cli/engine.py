"""The engine: derive the state, ask `flow`, run the step, append the events.

Every step starts from the state replayed out of the log, never from memory
(PROTOCOL section 9). User commands run with `bash -c` and receive their data
only as environment variables, never interpolated into the shell string.
"""

import os
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from lasagna_cli.eventlog import EventWriter, read_events
from lasagna_cli.flow import DecideRoute, Execute, Finish, Prune, next_step
from lasagna_cli.gitops import commit_all, local_git_env_vars
from lasagna_cli.model import Decider, Phase, Pipeline, Project
from lasagna_cli.outputs import collect_outputs, new_output_file, parse_output_file
from lasagna_cli.resolve import Scope, UnresolvedError, resolve_text
from lasagna_cli.runner import Interrupted, build_env, run_shell
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


Runner = Callable[..., int]


class Engine:
    """Drives one run in the foreground until its end (or, from M3b, a human wait)."""

    def __init__(
        self,
        ctx: RunContext,
        writer: EventWriter,
        *,
        runner: Runner = run_shell,
        platform: str = sys.platform,
    ) -> None:
        self.ctx = ctx
        self.writer = writer
        self.runner = runner
        self.platform = platform

    # -- main loop ---------------------------------------------------------

    def drive(self) -> int:
        """Advance the run; the return value is the exit code of the command."""
        while True:
            state = self._state()
            step = next_step(self.ctx.pipeline, state)
            if isinstance(step, Finish):
                self._finish(state)
                return EXIT_OK
            phase_id = step.phase_id
            full = self._full(phase_id)
            if isinstance(step, Prune):
                self.writer.append("phase_skipped", phase=full, reason="pruned")
                continue
            try:
                if isinstance(step, DecideRoute):
                    code = self._route(phase_id, state)
                else:
                    assert isinstance(step, Execute)
                    code = self._execute(phase_id, state)
            except Interrupted:
                return self._interrupted(full)
            if code is not None:
                return code

    # -- helpers -----------------------------------------------------------

    def _state(self) -> RunState:
        return derive_state(read_events(self.writer.path))

    def _full(self, phase_id: str) -> str:
        return f"{self.ctx.pipeline.name}/{phase_id}"

    def _phase_state(self, state: RunState, phase_id: str) -> PhaseState | None:
        full = self._full(phase_id)
        return next((p for p in state.phases if p.phase == full), None)

    def _done_outputs(self, state: RunState) -> dict[str, dict[str, str]]:
        prefix = f"{self.ctx.pipeline.name}/"
        return {
            p.phase.removeprefix(prefix): dict(p.outputs)
            for p in state.phases
            if p.state == "done"
        }

    def _scope(self, state: RunState, **parts: dict[str, str] | None) -> Scope:
        return Scope(
            pipeline_inputs=self.ctx.inputs,
            phase_outputs=self._done_outputs(state),
            **parts,
        )

    def _fail(
        self,
        phase_id: str,
        reason: str,
        detail: str | None = None,
        exit_code: int | None = None,
    ) -> int:
        fields: dict[str, object] = {"phase": self._full(phase_id), "reason": reason}
        if detail is not None:
            fields["detail"] = detail
        if exit_code is not None:
            fields["exit_code"] = exit_code
        self.writer.append("phase_failed", **fields)
        self.writer.append("run_completed", status="failed")
        return EXIT_FAILED

    def _interrupted(self, full: str) -> int:
        self.writer.append("phase_failed", phase=full, reason="interrupted")
        self.writer.append("run_completed", status="failed")
        return EXIT_INTERRUPTED

    def _decider_kind(self, phase_id: str, decider: Decider) -> str:
        """ "human" or "machine"; agent deciders are refused at `start`."""
        actor = self.ctx.project.actors.get(decider.by)
        if actor is None or actor.type not in ("human", "machine"):
            raise EngineError(
                f"phase '{phase_id}': agent deciders are not supported yet"
            )
        return actor.type

    def _wait(self, state: RunState, phase_id: str, kind: str, by: str) -> int:
        """Record that a human is awaited, once per wait, and return the exit code."""
        full = self._full(phase_id)
        if not any(w.phase == full and w.for_ == kind for w in state.waiting):
            self.writer.append("phase_waiting", phase=full, **{"for": kind}, by=by)
        return EXIT_WAITING

    def _env(
        self,
        phase_id: str,
        output: Path,
        inputs: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        ctx = self.ctx
        variables = {
            "LASAGNA_RUN_ID": ctx.run_id,
            "LASAGNA_PIPELINE": ctx.pipeline.name,
            "LASAGNA_PHASE": self._full(phase_id),
            "LASAGNA_ITERATION": "1",
            "LASAGNA_WORKTREE": to_bash_path(ctx.worktree.resolve()),
            "LASAGNA_OUTPUT": to_bash_path(output.resolve()),
            "LASAGNA_STATE": to_bash_path(self.writer.path.resolve()),
        }
        for name, value in (inputs or {}).items():
            variables[f"LASAGNA_INPUT_{name.upper().replace('-', '_')}"] = value
        return build_env(
            os.environ,
            variables,
            self.platform,
            drop=local_git_env_vars(),
        )

    def _run_command(self, command: str, env: Mapping[str, str]) -> int:
        return self.runner(
            command,
            cwd=self.ctx.worktree,
            env=env,
            bash_setting=self.ctx.project.config.shell,
        )

    def _run_check(
        self,
        phase_id: str,
        check: str,
        inputs: Mapping[str, str] | None = None,
    ) -> tuple[int, dict[str, str]]:
        output = new_output_file(self.ctx.worktree, self.ctx.run_id)
        code = self._run_command(check, self._env(phase_id, output, inputs))
        return code, parse_output_file(output)

    # -- steps -------------------------------------------------------------

    def _finish(self, state: RunState) -> None:
        scope = self._scope(state)
        outputs: dict[str, str] = {}
        for name, text in self.ctx.pipeline.outputs.items():
            try:
                outputs[name] = resolve_text(text, scope)
            except UnresolvedError:
                continue  # omitted in a root run (PROTOCOL section 6)
        self.writer.append("run_completed", status="done", outputs=outputs)

    def _trigger(
        self, phase: Phase, state: RunState, existing: PhaseState | None
    ) -> tuple[str, int | None]:
        """Returns ("start" | "skip", None), or ("", exit code) when the run stops."""
        decider = phase.trigger
        if decider is None:
            return "start", None
        kind = self._decider_kind(phase.id, decider)
        recorded = [
            d for d in (existing.decisions if existing else ()) if d.kind == "trigger"
        ]
        if recorded:
            return recorded[-1].value, None
        if kind == "human":
            return "", self._wait(state, phase.id, "trigger", decider.by)
        if decider.check is None:
            return "start", None
        code, written = self._run_check(phase.id, decider.check)
        value = written.get("decision")
        if value is None:
            value = "start" if code == 0 else "skip"
        elif value not in ("start", "skip"):
            detail = f"trigger check wrote decision={value!r}; expected start or skip"
            return "", self._fail(phase.id, "invalid_decision", detail)
        self.writer.append(
            "decision",
            phase=self._full(phase.id),
            kind="trigger",
            by=decider.by,
            value=value,
        )
        return value, None

    def _execute(self, phase_id: str, state: RunState) -> int | None:
        ctx = self.ctx
        phase = ctx.pipeline.phase(phase_id)
        actor = ctx.project.actors.get(phase.actor) if phase.actor else None
        if phase.pipeline is not None or actor is None or actor.type == "agent":
            raise EngineError(f"phase '{phase_id}': only machine and human phases run")
        existing = self._phase_state(state, phase_id)
        if existing is not None and existing.state == "running":
            if existing.mode == "manual":
                return EXIT_WAITING
            raise EngineError(f"phase '{phase_id}' is already running")
        full = self._full(phase_id)

        decision, stop = self._trigger(phase, state, existing)
        if stop is not None:
            return stop
        if decision == "skip":
            self.writer.append("phase_skipped", phase=full, reason="trigger")
            return None

        inputs: dict[str, str] = {}
        scope = self._scope(state)
        for name, text in phase.inputs.items():
            try:
                inputs[name] = resolve_text(text, scope)
            except UnresolvedError as error:
                return self._fail(phase_id, "missing_input", f"{name}: {error}")

        if actor.type == "human":
            return self._open_manual(phase, full, inputs, state)
        self.writer.append(
            "phase_started",
            phase=full,
            actor=phase.actor,
            mode="headless",
            iteration=1,
            inputs=inputs,
        )
        output = new_output_file(ctx.worktree, ctx.run_id)
        started = time.monotonic()
        code = self._run_command(
            phase.with_["command"], self._env(phase_id, output, inputs)
        )
        if code != 0:
            return self._fail(phase_id, "exit_code", exit_code=code)

        def resolve_path(template: str, values: dict[str, str]) -> str:
            return resolve_text(
                template, self._scope(state, inputs=inputs, outputs=values)
            )

        result = collect_outputs(
            phase.outputs, parse_output_file(output), ctx.worktree, resolve_path
        )
        if result.missing:
            return self._fail(phase_id, "missing_output", "; ".join(result.errors))

        sha = commit_all(ctx.worktree, f"lasagna({ctx.run_id}): {full}")
        self.writer.append(
            "phase_completed",
            phase=full,
            exit_code=0,
            outputs=result.outputs,
            commit=sha,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        return None

    def _open_manual(
        self, phase: Phase, full: str, inputs: dict[str, str], state: RunState
    ) -> int:
        """Open a human phase: record `phase_started` (manual) and wait."""
        params: dict[str, str] = {}
        text = phase.with_.get("instructions")
        if text is not None:
            scope = self._scope(state, inputs=inputs)
            try:
                params["instructions"] = resolve_text(text, scope)
            except UnresolvedError as error:
                return self._fail(phase.id, "missing_input", f"instructions: {error}")
        fields: dict[str, object] = {}
        if params:
            fields["params"] = params
        self.writer.append(
            "phase_started",
            phase=full,
            actor=phase.actor,
            mode="manual",
            iteration=1,
            inputs=inputs,
            **fields,
        )
        return EXIT_WAITING

    def _route(self, phase_id: str, state: RunState) -> int | None:
        phase = self.ctx.pipeline.phase(phase_id)
        decider = phase.route
        if decider is None:
            raise EngineError(f"phase '{phase_id}': no route to decide")
        if self._decider_kind(phase_id, decider) == "human":
            return self._wait(state, phase_id, "route", decider.by)
        if decider.check is None:
            raise EngineError(f"phase '{phase_id}': a machine route needs a check")
        existing = self._phase_state(state, phase_id)
        inputs = existing.inputs if existing else {}
        code, written = self._run_check(phase_id, decider.check, inputs)
        if code != 0:
            detail = f"route check exited with code {code}"
            return self._fail(phase_id, "check_failed", detail, exit_code=code)
        children = self.ctx.pipeline.children(phase_id)
        chosen = written.get("next")
        if chosen not in children:
            detail = (
                f"route check wrote next={chosen!r}; "
                f"expected one of: {', '.join(children)}"
            )
            return self._fail(phase_id, "invalid_decision", detail)
        self.writer.append(
            "decision",
            phase=self._full(phase_id),
            kind="route",
            by=decider.by,
            value=chosen,
        )
        return None
