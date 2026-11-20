"""Substitute `${{ }}` expressions with values from a typed scope."""

from dataclasses import dataclass

from lasagna_cli.expressions import Ref, render


class UnresolvedError(Exception):
    """An expression whose value is not available."""

    def __init__(self, ref: Ref) -> None:
        self.ref = ref
        super().__init__(f"cannot resolve {describe(ref)}")


def describe(ref: Ref) -> str:
    """The reference as it is written inside `${{ }}`."""
    if ref.scope == "phases":
        return f"phases.{ref.phase}.outputs.{ref.name}"
    if ref.scope == "harness.main_skill":
        return ref.scope
    return f"{ref.scope}.{ref.name}"


@dataclass(frozen=True)
class Scope:
    """What an expression may see. `None` means that part is not available."""

    pipeline_inputs: dict[str, str]
    phase_outputs: dict[str, dict[str, str]]
    inputs: dict[str, str] | None = None
    outputs: dict[str, str] | None = None
    main_skill: str | None = None


def _lookup(ref: Ref, scope: Scope) -> str:
    value: str | None
    if ref.scope == "pipeline.inputs":
        value = scope.pipeline_inputs.get(ref.name or "")
    elif ref.scope == "phases":
        value = scope.phase_outputs.get(ref.phase or "", {}).get(ref.name or "")
    elif ref.scope == "inputs":
        value = None if scope.inputs is None else scope.inputs.get(ref.name or "")
    elif ref.scope == "outputs":
        value = None if scope.outputs is None else scope.outputs.get(ref.name or "")
    else:
        value = scope.main_skill
    if value is None:
        raise UnresolvedError(ref)
    return value


def resolve_text(text: str, scope: Scope) -> str:
    """Resolve every expression in `text`; `UnresolvedError` if one is missing."""
    return render(text, lambda ref: _lookup(ref, scope))
