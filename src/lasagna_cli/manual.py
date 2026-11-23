"""Manual phases: `phase run`, `phase done`, `phase fail` on the open phase."""

from collections.abc import Mapping
from datetime import datetime

from lasagna_cli.eventlog import read_events, utc_now
from lasagna_cli.model import Phase
from lasagna_cli.outputs import new_output_file, parse_output_file
from lasagna_cli.phases import PhaseExecutor
from lasagna_cli.runenv import EngineError, RunEnv
from lasagna_cli.state import PhaseState, RunState


class ManualPhases:
    """What a human does on the manual phase that is open."""

    def __init__(self, run: RunEnv, executor: PhaseExecutor) -> None:
        self.run = run
        self.executor = executor

    def _open(self, phase_id: str) -> tuple[Phase, RunState, PhaseState]:
        state = self.run.state()
        current = self.run.phase_state(state, phase_id)
        if current is None or current.state != "running" or current.mode != "manual":
            raise EngineError(f"phase '{phase_id}' is not a running manual phase")
        return self.run.ctx.pipeline.phase(phase_id), state, current

    def _since_started(self, full: str) -> int:
        started = [
            e
            for e in read_events(self.run.writer.path)
            if e["event"] == "phase_started" and e["phase"] == full
        ]
        begin = datetime.fromisoformat(started[-1]["ts"].replace("Z", "+00:00"))
        return max(0, int((utc_now() - begin).total_seconds() * 1000))

    def run_command(self, phase_id: str) -> int | None:
        """Run the command of the open manual phase in the foreground.

        Returns an exit code when the run stops, or None when the phase is
        completed and the caller should `drive()` on.
        """
        run = self.run
        phase, state, current = self._open(phase_id)
        command = phase.with_.get("command")
        if command is None:
            raise EngineError(f"phase '{phase_id}' has no command")
        output = new_output_file(run.ctx.worktree, run.ctx.run_id)
        env = run.env(phase_id, output, current.inputs)
        code = run.run_command(command, env, inherit_stdin=True)
        if code != 0:
            return run.fail(phase_id, "exit_code", exit_code=code)
        return self.executor.complete(
            phase,
            state,
            dict(current.inputs),
            parse_output_file(output),
            self._since_started(run.full(phase_id)),
            exit_code=0,
        )

    def done(self, phase_id: str, written: Mapping[str, str]) -> int | None:
        """The human declares the phase done; same verification and commit."""
        phase, state, current = self._open(phase_id)
        return self.executor.complete(
            phase,
            state,
            dict(current.inputs),
            written,
            self._since_started(self.run.full(phase_id)),
            exit_code=None,
        )

    def fail(self, phase_id: str, reason: str | None) -> int:
        """The human declares the phase failed; the run fails with it."""
        self._open(phase_id)
        return self.run.fail(phase_id, "manual", reason)
