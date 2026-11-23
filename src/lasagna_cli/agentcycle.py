"""The four commands of an agent, in order, and how their failures are reported."""

from collections.abc import Callable
from dataclasses import dataclass

from lasagna_cli.model import Actor
from lasagna_cli.runner import TimedOut


@dataclass(frozen=True)
class CycleResult:
    ok: bool
    reason: str | None
    detail: str | None
    exit_code: int | None


OK = CycleResult(True, None, None, None)


def run_agent_cycle(
    actor: Actor,
    *,
    interactive: bool,
    run_command: Callable[[str, bool], int],
    timeout_text: str | None = None,
) -> CycleResult:
    """`check`, `inject`, `run` (or `run_interactive`), `cleanup` (PROTOCOL section 7).

    `run_command(command, is_main)` runs one command and returns its exit code;
    it applies the timeout to the main command only and raises `TimedOut` when
    it expires (`timeout_text` is how the phase wrote it, for the `detail`).
    """
    commands = actor.commands
    assert commands is not None, f"agent '{actor.name}' has no commands"
    for number, check in enumerate(commands.check, start=1):
        code = run_command(check, False)
        if code != 0:
            detail = f"check {number} ({check}) exited {code}"
            return CycleResult(False, "check_failed", detail, code)

    outcome = OK
    if commands.inject is not None:
        code = run_command(commands.inject, False)
        if code != 0:
            outcome = CycleResult(False, "exit_code", "inject", code)
    if outcome.ok:
        main = commands.run_interactive if interactive else commands.run
        assert main is not None, f"agent '{actor.name}' has nothing to run"
        try:
            code = run_command(main, True)
        except TimedOut:
            outcome = CycleResult(False, "timeout", f"exceeded {timeout_text}", None)
        else:
            if code != 0:
                outcome = CycleResult(False, "exit_code", "run", code)

    if commands.cleanup is not None:
        code = run_command(commands.cleanup, False)
        if code != 0 and outcome.ok:
            outcome = CycleResult(False, "exit_code", "cleanup", code)
    return outcome
