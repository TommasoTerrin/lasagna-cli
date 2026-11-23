from lasagna_cli.agentcycle import CycleResult, run_agent_cycle
from lasagna_cli.model import Actor, AgentCommands
from lasagna_cli.runner import TimedOut


def actor(
    *,
    check: tuple[str, ...] = (),
    inject: str | None = None,
    run: str = "RUN",
    run_interactive: str | None = None,
    cleanup: str | None = None,
) -> Actor:
    return Actor(
        name="fake",
        type="agent",
        file=".lasagna/actors/fake.yaml",
        params={},
        models={},
        commands=AgentCommands(check, inject, run, run_interactive, cleanup),
    )


class Recorder:
    """A `run_command` that records its calls and fails the commands named."""

    def __init__(self, codes: dict[str, int] | None = None, raises=None) -> None:
        self.codes = codes or {}
        self.raises = raises or {}
        self.calls: list[tuple[str, bool]] = []

    def __call__(self, command: str, is_main: bool) -> int:
        self.calls.append((command, is_main))
        if command in self.raises:
            raise self.raises[command]
        return self.codes.get(command, 0)

    @property
    def commands(self) -> list[str]:
        return [command for command, _ in self.calls]


FULL = actor(check=("C1", "C2"), inject="INJECT", cleanup="CLEANUP")


def test_the_steps_run_in_order() -> None:
    recorder = Recorder()
    result = run_agent_cycle(FULL, interactive=False, run_command=recorder)
    assert result == CycleResult(True, None, None, None)
    assert recorder.commands == ["C1", "C2", "INJECT", "RUN", "CLEANUP"]


def test_only_the_main_command_is_marked_main() -> None:
    recorder = Recorder()
    run_agent_cycle(FULL, interactive=False, run_command=recorder)
    assert [command for command, main in recorder.calls if main] == ["RUN"]


def test_a_failing_check_stops_everything_without_cleanup() -> None:
    recorder = Recorder({"C2": 4})
    result = run_agent_cycle(FULL, interactive=False, run_command=recorder)
    assert result == CycleResult(False, "check_failed", "check 2 (C2) exited 4", 4)
    assert recorder.commands == ["C1", "C2"]


def test_a_failing_inject_skips_run_but_runs_cleanup() -> None:
    recorder = Recorder({"INJECT": 5})
    result = run_agent_cycle(FULL, interactive=False, run_command=recorder)
    assert result == CycleResult(False, "exit_code", "inject", 5)
    assert recorder.commands == ["C1", "C2", "INJECT", "CLEANUP"]


def test_a_failing_run_still_runs_cleanup() -> None:
    recorder = Recorder({"RUN": 2})
    result = run_agent_cycle(FULL, interactive=False, run_command=recorder)
    assert result == CycleResult(False, "exit_code", "run", 2)
    assert recorder.commands[-1] == "CLEANUP"


def test_cleanup_failing_after_a_good_run_fails_the_phase() -> None:
    recorder = Recorder({"CLEANUP": 6})
    result = run_agent_cycle(FULL, interactive=False, run_command=recorder)
    assert result == CycleResult(False, "exit_code", "cleanup", 6)


def test_cleanup_failing_after_a_failed_run_keeps_the_run_failure() -> None:
    recorder = Recorder({"RUN": 2, "CLEANUP": 6})
    result = run_agent_cycle(FULL, interactive=False, run_command=recorder)
    assert result == CycleResult(False, "exit_code", "run", 2)


def test_interactive_uses_run_interactive() -> None:
    both = actor(run_interactive="TALK")
    recorder = Recorder()
    result = run_agent_cycle(both, interactive=True, run_command=recorder)
    assert result.ok
    assert recorder.commands == ["TALK"]


def test_no_inject_and_no_cleanup_is_fine() -> None:
    recorder = Recorder()
    assert run_agent_cycle(actor(), interactive=False, run_command=recorder).ok
    assert recorder.commands == ["RUN"]


def test_a_timeout_in_run_still_runs_cleanup() -> None:
    recorder = Recorder(raises={"RUN": TimedOut()})
    result = run_agent_cycle(
        FULL, interactive=False, run_command=recorder, timeout_text="2s"
    )
    assert result == CycleResult(False, "timeout", "exceeded 2s", None)
    assert recorder.commands[-1] == "CLEANUP"
