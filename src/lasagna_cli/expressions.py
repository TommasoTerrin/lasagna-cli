"""Parser for `${{ ... }}` expressions: finds references, never evaluates."""

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Literal

OPEN = "${{"
CLOSE = "}}"
_NAME = r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*"

# Order matters only for readability: the patterns are mutually exclusive.
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("pipeline.inputs", re.compile(rf"pipeline\.inputs\.(?P<name>{_NAME})")),
    (
        "phases",
        re.compile(rf"phases\.(?P<phase>{_NAME})\.outputs\.(?P<name>{_NAME})"),
    ),
    ("inputs", re.compile(rf"inputs\.(?P<name>{_NAME})")),
    ("outputs", re.compile(rf"outputs\.(?P<name>{_NAME})")),
    ("harness.main_skill", re.compile(r"harness\.main_skill")),
)


class ExpressionError(ValueError):
    """Raised for a malformed `${{ }}` expression."""


@dataclass(frozen=True)
class Ref:
    scope: Literal[
        "pipeline.inputs", "phases", "inputs", "outputs", "harness.main_skill"
    ]
    phase: str | None
    name: str | None


def has_expression(text: str) -> bool:
    """True if the text contains the start of an expression."""
    return OPEN in text


def _spans(text: str) -> Iterator[tuple[int, int, Ref]]:
    """Yield (start, end, ref) for each expression, `end` after the closing `}}`."""
    position = 0
    while (start := text.find(OPEN, position)) != -1:
        end = text.find(CLOSE, start + len(OPEN))
        if end == -1:
            raise ExpressionError(f"unclosed '{OPEN}'")
        ref = _parse(text[start + len(OPEN) : end].strip())
        position = end + len(CLOSE)
        yield start, position, ref


def find_refs(text: str) -> list[Ref]:
    """Return the references in order of appearance."""
    return [ref for _, _, ref in _spans(text)]


def render(text: str, lookup: Callable[[Ref], str]) -> str:
    """Replace each expression with `lookup(ref)`; values are never re-parsed."""
    pieces: list[str] = []
    last = 0
    for start, end, ref in _spans(text):
        pieces.append(text[last:start])
        pieces.append(lookup(ref))
        last = end
    pieces.append(text[last:])
    return "".join(pieces)


def _parse(body: str) -> Ref:
    if not body:
        raise ExpressionError("empty expression")
    for scope, pattern in _PATTERNS:
        match = pattern.fullmatch(body)
        if match:
            groups = match.groupdict()
            return Ref(scope, groups.get("phase"), groups.get("name"))  # type: ignore[arg-type]
    raise ExpressionError(f"unknown reference '{body}'")
