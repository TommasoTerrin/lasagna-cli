"""Triggers, routes and loop decisions: who decides, and the waits for humans."""

import dataclasses
from collections.abc import Mapping, Sequence

from lasagna_cli.decisions import build_decision_prompt, run_agent_decision
from lasagna_cli.gitops import drop_snapshot, head_commit, restore_to, snapshot_commit
from lasagna_cli.harness import main_skill_path
from lasagna_cli.model import Decider, Phase
from lasagna_cli.outputs import new_output_file
from lasagna_cli.params import MissingParamError, fill_params, param_env
from lasagna_cli.resolve import Scope, UnresolvedError, resolve_text
from lasagna_cli.runenv import EngineError, RunEnv
from lasagna_cli.state import PhaseState, RunState


class Deciders:
    """Decisions of a phase: `trigger`, `route` and `loop.until`."""

    def __init__(self, run: RunEnv) -> None:
        self.run = run

    def _record(self, phase_id: str, kind: str, by: str, value: str) -> None:
        self.run.writer.append(
            "decision", phase=self.run.full(phase_id), kind=kind, by=by, value=value
        )

    def trigger(
        self, phase: Phase, state: RunState, existing: PhaseState | None
    ) -> tuple[str, int | None]:
        """Returns ("start" | "skip", None), or ("", exit code) when the run stops."""
        run = self.run
        decider = phase.trigger
        if decider is None:
            return "start", None
        kind = run.decider_kind(phase.id, decider)
        recorded = [
            d for d in (existing.decisions if existing else ()) if d.kind == "trigger"
        ]
        if recorded:
            return recorded[-1].value, None
        if kind == "human":
            return "", run.wait(state, phase.id, "trigger", decider.by)
        if kind == "agent":
            value, stop = self._agent(
                phase, "trigger", decider, run.scope(state), snapshot=False
            )
            if stop is not None:
                return "", stop
        elif decider.check is None:
            return "start", None
        else:
            code, written = run.run_check(phase.id, decider.check)
            value = written.get("decision")
            if value is None:
                value = "start" if code == 0 else "skip"
            elif value not in ("start", "skip"):
                detail = (
                    f"trigger check wrote decision={value!r}; expected start or skip"
                )
                return "", run.fail(phase.id, "invalid_decision", detail)
        self._record(phase.id, "trigger", decider.by, value)
        return value, None

    def loop_until(
        self,
        phase: Phase,
        iteration: int,
        inputs: Mapping[str, str],
        state: RunState,
        outputs: Mapping[str, str] | None = None,
    ) -> tuple[str, int | None]:
        """("stop" | "continue", None), or ("", exit code) when the run stops."""
        run = self.run
        assert phase.loop is not None
        decider = phase.loop.until
        kind = run.decider_kind(phase.id, decider)
        if kind == "human":
            return "", run.wait(run.state(), phase.id, "loop", decider.by)
        extra = {"LASAGNA_ITERATION": str(iteration)}
        if kind == "agent":
            scope = run.scope(
                state,
                inputs=dict(inputs),
                outputs=dict(outputs or {}),
                main_skill=self._main_skill(phase),
            )
            value, stop = self._agent(
                phase, "loop", decider, scope, snapshot=True, inputs=inputs, extra=extra
            )
            if stop is not None:
                return "", stop
        else:
            if decider.check is None:
                raise EngineError(f"phase '{phase.id}': a machine until needs a check")
            code, written = run.run_check(phase.id, decider.check, inputs, extra)
            value = written.get("decision")
            if value is None:
                value = "stop" if code == 0 else "continue"
            elif value not in ("stop", "continue"):
                detail = (
                    f"until check wrote decision={value!r}; expected stop or continue"
                )
                return "", run.fail(phase.id, "invalid_decision", detail)
        self._record(phase.id, "loop", decider.by, value)
        return value, None

    def route(self, phase_id: str, state: RunState) -> int | None:
        run = self.run
        phase = run.ctx.pipeline.phase(phase_id)
        decider = phase.route
        if decider is None:
            raise EngineError(f"phase '{phase_id}': no route to decide")
        kind = run.decider_kind(phase_id, decider)
        if kind == "human":
            return run.wait(state, phase_id, "route", decider.by)
        existing = run.phase_state(state, phase_id)
        inputs = dict(existing.inputs) if existing else {}
        children = run.ctx.pipeline.children(phase_id)
        if kind == "agent":
            scope = run.scope(
                state,
                inputs=inputs,
                outputs=dict(existing.outputs) if existing else {},
                main_skill=self._main_skill(phase),
            )
            chosen, stop = self._agent(
                phase,
                "route",
                decider,
                scope,
                snapshot=False,
                inputs=inputs,
                children=children,
            )
            if stop is not None:
                return stop
        else:
            if decider.check is None:
                raise EngineError(f"phase '{phase_id}': a machine route needs a check")
            code, written = run.run_check(phase_id, decider.check, inputs)
            if code != 0:
                detail = f"route check exited with code {code}"
                return run.fail(phase_id, "check_failed", detail, exit_code=code)
            chosen = written.get("next")
            if chosen not in children:
                detail = (
                    f"route check wrote next={chosen!r}; "
                    f"expected one of: {', '.join(children)}"
                )
                return run.fail(phase_id, "invalid_decision", detail)
        self._record(phase_id, "route", decider.by, chosen)
        return None

    # -- decisions taken by an agent ---------------------------------------

    def _main_skill(self, phase: Phase) -> str | None:
        if not phase.main_skill:
            return None
        return main_skill_path(self.run.ctx.pipeline, phase)

    def _agent(
        self,
        phase: Phase,
        kind: str,
        decider: Decider,
        scope: Scope,
        *,
        snapshot: bool,
        inputs: Mapping[str, str] | None = None,
        extra: Mapping[str, str] | None = None,
        children: Sequence[str] = (),
    ) -> tuple[str, int | None]:
        """Ask the agent; the worktree is left as it was before (PROTOCOL section 6).

        Returns (value, None), or ("", exit code) when the phase fails.
        """
        run = self.run
        ctx = run.ctx
        actor = ctx.project.actors[decider.by]
        output = new_output_file(ctx.worktree, ctx.run_id)
        relative = output.relative_to(ctx.worktree).as_posix()
        try:
            prompt = resolve_text(
                decider.prompt or "", dataclasses.replace(scope, output=relative)
            )
            params = fill_params(
                actor,
                {"prompt": build_decision_prompt(kind, prompt, relative, children)},
            )
        except (UnresolvedError, MissingParamError) as error:
            detail = f"{kind} prompt: {error}"
            return "", run.fail(phase.id, "missing_input", detail)
        env = run.env(phase.id, output, inputs, {**param_env(params), **(extra or {})})

        base = head_commit(ctx.worktree)
        saved = snapshot_commit(ctx.worktree) if snapshot else None
        result = run_agent_decision(
            actor, kind, output, lambda command: run.run_command(command, env), children
        )
        restore_to(ctx.worktree, saved or base)
        if saved is not None:
            drop_snapshot(ctx.worktree, base)

        if result.failure is not None:
            failure = result.failure
            assert failure.reason is not None
            code = run.fail(
                phase.id, failure.reason, failure.detail, exit_code=failure.exit_code
            )
            return "", code
        assert result.value is not None
        return result.value, None
