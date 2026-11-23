"""Triggers and routes: who decides, and the waits for humans."""

from collections.abc import Mapping

from lasagna_cli.model import Phase
from lasagna_cli.runenv import EngineError, RunEnv
from lasagna_cli.state import PhaseState, RunState


class Deciders:
    """Decisions of a phase: `trigger` (start or skip) and `route` (which child)."""

    def __init__(self, run: RunEnv) -> None:
        self.run = run

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
        if decider.check is None:
            return "start", None
        code, written = run.run_check(phase.id, decider.check)
        value = written.get("decision")
        if value is None:
            value = "start" if code == 0 else "skip"
        elif value not in ("start", "skip"):
            detail = f"trigger check wrote decision={value!r}; expected start or skip"
            return "", run.fail(phase.id, "invalid_decision", detail)
        run.writer.append(
            "decision",
            phase=run.full(phase.id),
            kind="trigger",
            by=decider.by,
            value=value,
        )
        return value, None

    def loop_until(
        self,
        phase: Phase,
        iteration: int,
        inputs: Mapping[str, str],
        state: RunState,
    ) -> tuple[str, int | None]:
        """("stop" | "continue", None), or ("", exit code) when the run stops."""
        run = self.run
        assert phase.loop is not None
        decider = phase.loop.until
        if run.decider_kind(phase.id, decider) == "human":
            return "", run.wait(run.state(), phase.id, "loop", decider.by)
        if decider.check is None:
            raise EngineError(f"phase '{phase.id}': a machine until needs a check")
        code, written = run.run_check(
            phase.id, decider.check, inputs, {"LASAGNA_ITERATION": str(iteration)}
        )
        value = written.get("decision")
        if value is None:
            value = "stop" if code == 0 else "continue"
        elif value not in ("stop", "continue"):
            detail = f"until check wrote decision={value!r}; expected stop or continue"
            return "", run.fail(phase.id, "invalid_decision", detail)
        run.writer.append(
            "decision",
            phase=run.full(phase.id),
            kind="loop",
            by=decider.by,
            value=value,
        )
        return value, None

    def route(self, phase_id: str, state: RunState) -> int | None:
        run = self.run
        phase = run.ctx.pipeline.phase(phase_id)
        decider = phase.route
        if decider is None:
            raise EngineError(f"phase '{phase_id}': no route to decide")
        if run.decider_kind(phase_id, decider) == "human":
            return run.wait(state, phase_id, "route", decider.by)
        if decider.check is None:
            raise EngineError(f"phase '{phase_id}': a machine route needs a check")
        existing = run.phase_state(state, phase_id)
        inputs = existing.inputs if existing else {}
        code, written = run.run_check(phase_id, decider.check, inputs)
        if code != 0:
            detail = f"route check exited with code {code}"
            return run.fail(phase_id, "check_failed", detail, exit_code=code)
        children = run.ctx.pipeline.children(phase_id)
        chosen = written.get("next")
        if chosen not in children:
            detail = (
                f"route check wrote next={chosen!r}; "
                f"expected one of: {', '.join(children)}"
            )
            return run.fail(phase_id, "invalid_decision", detail)
        run.writer.append(
            "decision",
            phase=run.full(phase_id),
            kind="route",
            by=decider.by,
            value=chosen,
        )
        return None
