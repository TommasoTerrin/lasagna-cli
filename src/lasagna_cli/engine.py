"""The engine: derive the state, ask `flow`, run the step, append the events.

Every step starts from the state replayed out of the log, never from memory
(PROTOCOL section 9). User commands run with `bash -c` and receive their data
only as environment variables, never interpolated into the shell string.

The work itself lives in `runenv` (shared helpers), `deciders`, `phases` and
`manual`; this module keeps the loop, the interruption handling and the
public API.
"""

import sys
from collections.abc import Callable, Mapping

from lasagna_cli.deciders import Deciders
from lasagna_cli.eventlog import EventWriter
from lasagna_cli.flow import DecideRoute, Execute, Finish, Prune, next_step
from lasagna_cli.manual import ManualPhases
from lasagna_cli.phases import PhaseExecutor
from lasagna_cli.resolve import UnresolvedError, resolve_text
from lasagna_cli.runenv import (
    EXIT_FAILED,
    EXIT_INTERRUPTED,
    EXIT_OK,
    EXIT_WAITING,
    EngineError,
    RunContext,
    RunEnv,
    Runner,
)
from lasagna_cli.runner import Interrupted, run_shell
from lasagna_cli.state import RunState

__all__ = [
    "EXIT_FAILED",
    "EXIT_INTERRUPTED",
    "EXIT_OK",
    "EXIT_WAITING",
    "Engine",
    "EngineError",
    "RunContext",
    "Runner",
]


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
        self.run = RunEnv(ctx, writer, runner, platform)
        self.deciders = Deciders(self.run)
        self.executor = PhaseExecutor(self.run, self.deciders)
        self.manual = ManualPhases(self.run, self.executor)
        self._current: str | None = None

    # -- main loop ---------------------------------------------------------

    def drive(self) -> int:
        """Advance the run; the return value is the exit code of the command.

        A Ctrl+C anywhere in here closes the phase in progress with
        `phase_failed` (`interrupted`) and the run with `run_completed`
        (`failed`), and the exit code is 130.
        """
        try:
            return self._drive()
        except (Interrupted, KeyboardInterrupt):
            return self._close_interrupted()

    def _drive(self) -> int:
        while True:
            self._current = None
            state = self.run.state()
            step = next_step(self.ctx.pipeline, state)
            if isinstance(step, Finish):
                self._finish(state)
                return EXIT_OK
            phase_id = step.phase_id
            full = self.run.full(phase_id)
            self._current = full
            if isinstance(step, Prune):
                self.writer.append("phase_skipped", phase=full, reason="pruned")
                continue
            if isinstance(step, DecideRoute):
                code = self.deciders.route(phase_id, state)
            else:
                assert isinstance(step, Execute)
                code = self.executor.execute(phase_id, state)
            if code is not None:
                return code

    # -- interruption ------------------------------------------------------

    def _close_interrupted(self) -> int:
        """Write the events of an interruption; the log stays valid.

        The interrupt may have hit inside a write, so the writer resyncs first;
        if the run was already closed, nothing is added.
        """
        full = self._current
        self.writer.resync()
        state = self.run.state()
        if state.status in ("done", "failed", "cancelled"):
            return EXIT_INTERRUPTED
        current = next((p for p in state.phases if p.phase == full), None)
        if full is not None and not (current and current.state == "failed"):
            self.writer.append("phase_failed", phase=full, reason="interrupted")
        self.writer.append("run_completed", status="failed")
        return EXIT_INTERRUPTED

    def _guarded(self, phase_id: str, action: Callable[[], int | None]) -> int | None:
        self._current = self.run.full(phase_id)
        try:
            return action()
        except (Interrupted, KeyboardInterrupt):
            return self._close_interrupted()

    def _finish(self, state: RunState) -> None:
        scope = self.run.scope(state)
        outputs: dict[str, str] = {}
        for name, text in self.ctx.pipeline.outputs.items():
            try:
                outputs[name] = resolve_text(text, scope)
            except UnresolvedError:
                continue  # omitted in a root run (PROTOCOL section 6)
        self.writer.append("run_completed", status="done", outputs=outputs)

    # -- manual phases (`phase run`, `phase done`, `phase fail`) -----------

    def manual_run(self, phase_id: str) -> int | None:
        """Run the command of the open manual phase in the foreground.

        Returns an exit code when the run stops, or None when the phase is
        completed and the caller should `drive()` on.
        """
        return self._guarded(phase_id, lambda: self.manual.run_command(phase_id))

    def manual_done(self, phase_id: str, written: Mapping[str, str]) -> int | None:
        """The human declares the phase done; same verification and commit."""
        return self._guarded(phase_id, lambda: self.manual.done(phase_id, written))

    def manual_fail(self, phase_id: str, reason: str | None) -> int:
        """The human declares the phase failed; the run fails with it."""
        return self.manual.fail(phase_id, reason)
