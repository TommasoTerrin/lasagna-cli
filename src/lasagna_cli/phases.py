"""Phase execution: inputs, command, verification, commit."""

import time
from collections.abc import Mapping

from lasagna_cli.agentcycle import run_agent_cycle
from lasagna_cli.deciders import Deciders
from lasagna_cli.gitops import commit_all
from lasagna_cli.harness import harness_env, main_skill_path
from lasagna_cli.model import Actor, Phase
from lasagna_cli.outputs import collect_outputs, new_output_file, parse_output_file
from lasagna_cli.params import (
    MissingParamError,
    UnknownParamError,
    param_env,
    resolve_params,
)
from lasagna_cli.resolve import UnresolvedError, resolve_text
from lasagna_cli.runenv import EXIT_WAITING, EngineError, RunEnv
from lasagna_cli.runner import TimedOut, parse_duration
from lasagna_cli.state import RunState


class PhaseExecutor:
    """Runs the machine and human phases of the pipeline."""

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
        if actor.type == "agent":
            return self._run_agent(phase, actor, inputs, state)
        return self._run_machine(phase, inputs, state)

    def _timeout(self, phase: Phase) -> float | None:
        return parse_duration(phase.timeout) if phase.timeout is not None else None

    def _run_machine(
        self, phase: Phase, inputs: dict[str, str], state: RunState
    ) -> int | None:
        run = self.run
        ctx = run.ctx
        run.writer.append(
            "phase_started",
            phase=run.full(phase.id),
            actor=run.actor_name(phase),
            mode="headless",
            iteration=1,
            inputs=inputs,
        )
        output = new_output_file(ctx.worktree, ctx.run_id)
        started = time.monotonic()
        try:
            code = run.run_command(
                phase.with_["command"],
                run.env(phase.id, output, inputs),
                timeout=self._timeout(phase),
            )
        except TimedOut:
            return run.fail(phase.id, "timeout", f"exceeded {phase.timeout}")
        if code != 0:
            return run.fail(phase.id, "exit_code", exit_code=code)
        return self.complete(
            phase,
            state,
            inputs,
            parse_output_file(output),
            int((time.monotonic() - started) * 1000),
            exit_code=0,
        )

    def _run_agent(
        self, phase: Phase, actor: Actor, inputs: dict[str, str], state: RunState
    ) -> int | None:
        run = self.run
        ctx = run.ctx
        main_skill = main_skill_path(ctx.pipeline, phase) if phase.main_skill else None
        scope = run.scope(state, inputs=inputs, main_skill=main_skill)
        try:
            params = resolve_params(actor, phase.with_, scope)
        except UnresolvedError as error:
            return run.fail(phase.id, "missing_input", f"param: {error}")
        except (MissingParamError, UnknownParamError) as error:
            return run.fail(phase.id, "missing_input", str(error))
        full = run.full(phase.id)
        run.writer.append(
            "phase_started",
            phase=full,
            actor=actor.name,
            mode="headless",
            iteration=1,
            inputs=inputs,
            params=params,
        )
        output = new_output_file(ctx.worktree, ctx.run_id)
        extra = {**param_env(params), **harness_env(ctx.pipeline, phase, full)}
        env = run.env(phase.id, output, inputs, extra)
        timeout = self._timeout(phase)

        def run_one(command: str, is_main: bool) -> int:
            return run.run_command(command, env, timeout=timeout if is_main else None)

        started = time.monotonic()
        result = run_agent_cycle(
            actor,
            interactive=False,
            run_command=run_one,
            timeout_text=phase.timeout,
        )
        if not result.ok:
            assert result.reason is not None
            return run.fail(
                phase.id, result.reason, result.detail, exit_code=result.exit_code
            )
        return self.complete(
            phase,
            state,
            inputs,
            parse_output_file(output),
            int((time.monotonic() - started) * 1000),
            exit_code=0,
        )

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

        def resolve_path(template: str, values: dict[str, str]) -> str:
            return resolve_text(
                template, run.scope(state, inputs=inputs, outputs=values)
            )

        result = collect_outputs(phase.outputs, written, ctx.worktree, resolve_path)
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
