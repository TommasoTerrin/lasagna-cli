"""Phase execution: inputs, command or agent cycle, loop, verification, commit."""

import time
from collections.abc import Mapping
from pathlib import Path

from lasagna_cli.agentcycle import run_agent_cycle
from lasagna_cli.deciders import Deciders
from lasagna_cli.gitops import commit_all
from lasagna_cli.harness import harness_env, main_skill_path
from lasagna_cli.model import Actor, Phase
from lasagna_cli.outputs import (
    OutputResult,
    collect_outputs,
    iteration_output_file,
    iteration_output_path,
    new_output_file,
    parse_output_file,
)
from lasagna_cli.params import (
    MissingParamError,
    UnknownParamError,
    param_env,
    resolve_params,
)
from lasagna_cli.resolve import UnresolvedError, resolve_text
from lasagna_cli.runenv import EXIT_WAITING, EngineError, RunEnv
from lasagna_cli.runner import TimedOut, parse_duration
from lasagna_cli.state import PhaseState, RunState


class PhaseExecutor:
    """Runs the machine, agent and human phases of the pipeline."""

    def __init__(self, run: RunEnv, deciders: Deciders | None = None) -> None:
        self.run = run
        self.deciders = deciders or Deciders(run)

    def execute(self, phase_id: str, state: RunState) -> int | None:
        run = self.run
        ctx = run.ctx
        phase = ctx.pipeline.phase(phase_id)
        actor = run.actor(phase)
        if phase.pipeline is not None or actor is None:
            raise EngineError(f"phase '{phase_id}': sub-pipelines do not run yet")
        existing = run.phase_state(state, phase_id)
        if (
            phase.loop is not None
            and existing is not None
            and existing.iteration is not None
            and existing.mode != "manual"
        ):
            return self._resume_loop(phase, actor, existing, state)
        if existing is not None and existing.state == "running":
            if existing.mode == "manual":
                return EXIT_WAITING
            raise EngineError(f"phase '{phase_id}' is already running")
        full = run.full(phase_id)

        decision, stop = self.deciders.trigger(phase, state, existing)
        if stop is not None:
            return stop
        if decision == "skip":
            run.writer.append("phase_skipped", phase=full, reason="trigger")
            return None

        inputs: dict[str, str] = {}
        scope = run.scope(state)
        for name, text in phase.inputs.items():
            try:
                inputs[name] = resolve_text(text, scope)
            except UnresolvedError as error:
                return run.fail(phase_id, "missing_input", f"{name}: {error}")

        if actor.type == "human":
            return self.open_manual(phase, full, inputs, state)
        return self._run_iterations(phase, actor, inputs, state, 1)

    # -- machine and agent phases, with or without `loop` ------------------

    def _run_iterations(
        self,
        phase: Phase,
        actor: Actor,
        inputs: dict[str, str],
        state: RunState,
        iteration: int,
    ) -> int | None:
        """Run iteration after iteration until the phase ends or a human is awaited."""
        run = self.run
        while True:
            code, written, duration_ms = self._iteration(
                phase, actor, inputs, state, iteration
            )
            if code is not None:
                return code
            if phase.loop is None:
                return self.complete(
                    phase, state, inputs, written, duration_ms, exit_code=0
                )
            checked = self.verify(phase, state, inputs, written)
            if checked.missing:
                return run.fail(phase.id, "missing_output", "; ".join(checked.errors))
            value, stop = self.deciders.loop_until(phase, iteration, inputs, state)
            if stop is not None:
                return stop
            finished, code = self._after_decision(
                phase, state, inputs, iteration, value, written
            )
            if finished:
                return code
            iteration += 1

    def _after_decision(
        self,
        phase: Phase,
        state: RunState,
        inputs: dict[str, str],
        iteration: int,
        value: str,
        written: Mapping[str, str],
    ) -> tuple[bool, int | None]:
        """(True, exit code or None) when the phase ends, (False, None) to go on."""
        run = self.run
        assert phase.loop is not None
        if value == "stop":
            duration_ms = run.since_started(run.full(phase.id), first=True)
            code = self.complete(
                phase, state, inputs, written, duration_ms, exit_code=0
            )
            return True, code
        if iteration >= phase.loop.max_iterations:
            detail = f"still not stopped after {phase.loop.max_iterations} iterations"
            return True, run.fail(phase.id, "max_iterations", detail)
        return False, None

    def _resume_loop(
        self, phase: Phase, actor: Actor, existing: PhaseState, state: RunState
    ) -> int | None:
        """Re-enter a loop after a human decision (PROTOCOL section 7)."""
        run = self.run
        ctx = run.ctx
        full = run.full(phase.id)
        iteration = existing.iteration
        assert iteration is not None
        if any(w.phase == full and w.for_ == "loop" for w in state.waiting):
            return EXIT_WAITING
        decided = [d for d in existing.decisions if d.kind == "loop"]
        if existing.state != "running" or len(decided) != iteration:
            raise EngineError(f"phase '{phase.id}' is already running")
        inputs = dict(existing.inputs)
        written = parse_output_file(
            iteration_output_path(ctx.worktree, ctx.run_id, full, iteration)
        )
        finished, code = self._after_decision(
            phase, state, inputs, iteration, decided[-1].value, written
        )
        if finished:
            return code
        return self._run_iterations(phase, actor, inputs, state, iteration + 1)

    def _timeout(self, phase: Phase) -> float | None:
        return parse_duration(phase.timeout) if phase.timeout is not None else None

    def _output_file(self, phase: Phase, iteration: int) -> Path:
        ctx = self.run.ctx
        if phase.loop is None:
            return new_output_file(ctx.worktree, ctx.run_id)
        full = self.run.full(phase.id)
        return iteration_output_file(ctx.worktree, ctx.run_id, full, iteration)

    def _iteration(
        self,
        phase: Phase,
        actor: Actor,
        inputs: dict[str, str],
        state: RunState,
        iteration: int,
    ) -> tuple[int | None, dict[str, str], int]:
        """One run of the phase: (exit code if it stops the run, outputs, ms)."""
        run = self.run
        ctx = run.ctx
        full = run.full(phase.id)
        extra = {"LASAGNA_ITERATION": str(iteration)}
        started: dict[str, object] = {
            "phase": full,
            "actor": actor.name,
            "mode": "headless",
            "iteration": iteration,
            "inputs": inputs,
        }
        timeout = self._timeout(phase)
        if actor.type == "agent":
            main = main_skill_path(ctx.pipeline, phase) if phase.main_skill else None
            scope = run.scope(state, inputs=inputs, main_skill=main)
            try:
                params = resolve_params(actor, phase.with_, scope)
            except UnresolvedError as error:
                return run.fail(phase.id, "missing_input", f"param: {error}"), {}, 0
            except (MissingParamError, UnknownParamError) as error:
                return run.fail(phase.id, "missing_input", str(error)), {}, 0
            started["params"] = params
            extra = {
                **param_env(params),
                **harness_env(ctx.pipeline, phase, full),
                **extra,
            }
        run.writer.append("phase_started", **started)
        output = self._output_file(phase, iteration)
        env = run.env(phase.id, output, inputs, extra)
        clock = time.monotonic()

        if actor.type == "agent":

            def run_one(command: str, is_main: bool) -> int:
                return run.run_command(
                    command, env, timeout=timeout if is_main else None
                )

            result = run_agent_cycle(
                actor,
                interactive=False,
                run_command=run_one,
                timeout_text=phase.timeout,
            )
            if not result.ok:
                assert result.reason is not None
                code = run.fail(
                    phase.id, result.reason, result.detail, exit_code=result.exit_code
                )
                return code, {}, 0
        else:
            try:
                exit_code = run.run_command(
                    phase.with_["command"], env, timeout=timeout
                )
            except TimedOut:
                code = run.fail(phase.id, "timeout", f"exceeded {phase.timeout}")
                return code, {}, 0
            if exit_code != 0:
                return run.fail(phase.id, "exit_code", exit_code=exit_code), {}, 0
        duration_ms = int((time.monotonic() - clock) * 1000)
        return None, parse_output_file(output), duration_ms

    def verify(
        self,
        phase: Phase,
        state: RunState,
        inputs: dict[str, str],
        written: Mapping[str, str],
    ) -> OutputResult:
        """Check the declared outputs of the phase against what was written."""
        run = self.run

        def resolve_path(template: str, values: dict[str, str]) -> str:
            return resolve_text(
                template, run.scope(state, inputs=inputs, outputs=values)
            )

        return collect_outputs(phase.outputs, written, run.ctx.worktree, resolve_path)

    def complete(
        self,
        phase: Phase,
        state: RunState,
        inputs: dict[str, str],
        written: Mapping[str, str],
        duration_ms: int,
        exit_code: int | None,
    ) -> int | None:
        """Verify the declared outputs, commit, record `phase_completed`."""
        run = self.run
        ctx = run.ctx
        full = run.full(phase.id)
        result = self.verify(phase, state, inputs, written)
        if result.missing:
            return run.fail(phase.id, "missing_output", "; ".join(result.errors))
        sha = commit_all(ctx.worktree, f"lasagna({ctx.run_id}): {full}")
        fields: dict[str, object] = {
            "outputs": result.outputs,
            "commit": sha,
            "duration_ms": duration_ms,
        }
        if exit_code is not None:
            fields["exit_code"] = exit_code
        run.writer.append("phase_completed", phase=full, **fields)
        return None

    def open_manual(
        self, phase: Phase, full: str, inputs: dict[str, str], state: RunState
    ) -> int:
        """Open a human phase: record `phase_started` (manual) and wait."""
        run = self.run
        params: dict[str, str] = {}
        text = phase.with_.get("instructions")
        if text is not None:
            scope = run.scope(state, inputs=inputs)
            try:
                params["instructions"] = resolve_text(text, scope)
            except UnresolvedError as error:
                return run.fail(phase.id, "missing_input", f"instructions: {error}")
        fields: dict[str, object] = {}
        if params:
            fields["params"] = params
        run.writer.append(
            "phase_started",
            phase=full,
            actor=run.actor_name(phase),
            mode="manual",
            iteration=1,
            inputs=inputs,
            **fields,
        )
        return EXIT_WAITING
