"""Decisions taken by an agent: the prompt it receives and how its answer is read.

A decision is a separate headless invocation of the agent: its `check`s, then
`run`, never `inject`, `cleanup` or `run_interactive`, with no harness and no
timeout (PROTOCOL section 6).
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from lasagna_cli.agentcycle import CycleResult
from lasagna_cli.model import Actor
from lasagna_cli.outputs import parse_output_file

_WRITE = "When you have decided, write exactly one line to the file {path}: "
_END = " Write nothing else there."

FIXED_INSTRUCTION = {
    "trigger": _WRITE + "decision=start or decision=skip." + _END,
    "route": _WRITE + "next=<phase> where <phase> is one of: {children}." + _END,
    "loop": _WRITE + "decision=stop or decision=continue." + _END,
}

_KEY = {"trigger": "decision", "route": "next", "loop": "decision"}
_VALUES = {"trigger": ("start", "skip"), "loop": ("stop", "continue")}


def build_decision_prompt(
    kind: str, prompt: str, path: str, children: Sequence[str] = ()
) -> str:
    """The resolved prompt, a blank line, then the fixed instruction of `kind`."""
    instruction = FIXED_INSTRUCTION[kind].format(
        path=path, children=", ".join(children)
    )
    return f"{prompt}\n\n{instruction}"


@dataclass(frozen=True)
class DecisionResult:
    value: str | None
    failure: CycleResult | None


def run_agent_decision(
    actor: Actor,
    kind: str,
    output: Path,
    run_command: Callable[[str], int],
    children: Sequence[str] = (),
) -> DecisionResult:
    """Run the `check`s and `run` of the agent, then read its answer from `output`.

    `run_command(command)` runs one command headless and returns its exit code.
    """
    commands = actor.commands
    assert commands is not None, f"agent '{actor.name}' has no commands"
    for number, check in enumerate(commands.check, start=1):
        code = run_command(check)
        if code != 0:
            detail = f"check {number} ({check}) exited {code}"
            return DecisionResult(
                None, CycleResult(False, "check_failed", detail, code)
            )
    code = run_command(commands.run)
    if code != 0:
        return DecisionResult(None, CycleResult(False, "exit_code", "run", code))
    key = _KEY[kind]
    allowed = tuple(children) if kind == "route" else _VALUES[kind]
    value = parse_output_file(output).get(key)
    if value not in allowed:
        detail = (
            f"{kind} decision by '{actor.name}' wrote {key}={value!r}; "
            f"expected one of: {', '.join(allowed)}"
        )
        return DecisionResult(
            None, CycleResult(False, "invalid_decision", detail, None)
        )
    return DecisionResult(value, None)
