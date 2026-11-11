"""Placeholder rendering for `lasagna show` (pure)."""

import posixpath
import re
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from lasagna.core.models import Pipeline

_PLACEHOLDER = re.compile(r"\{\{[ \t]*(params|inputs)\.([A-Za-z0-9_-]+)[ \t]*\}\}")


def find_placeholders(text: str) -> list[tuple[str, str]]:
    """List `(kind, name)` of every placeholder, in order of appearance, repetitions kept."""
    return [(m.group(1), m.group(2)) for m in _PLACEHOLDER.finditer(text)]


def render_text(text: str, params: Mapping[str, str], inputs: Mapping[str, str]) -> str:
    """Replace known `{{ params.x }}` / `{{ inputs.x }}` placeholders, once and literally."""
    maps = {"params": params, "inputs": inputs}

    def replace(match: re.Match[str]) -> str:
        values = maps[match.group(1)]
        name = match.group(2)
        return values[name] if name in values else match.group(0)

    return _PLACEHOLDER.sub(replace, text)


_PIPELINE_PREFIX = "$pipeline/"


class PipelinePathError(ValueError):
    """A `$pipeline/` resource ref resolves outside the pipeline folder."""

    def __init__(self, ref: str) -> None:
        super().__init__(ref)
        self.ref = ref


def resolve_pipeline_ref(ref: str, pipeline_dir: str) -> str:
    """Resolve a `$pipeline/...` ref into the pipeline folder; other refs stay as they are."""
    if not ref.startswith(_PIPELINE_PREFIX):
        return ref
    resolved = posixpath.normpath(pipeline_dir + "/" + ref[len(_PIPELINE_PREFIX) :])
    if resolved != pipeline_dir and not resolved.startswith(pipeline_dir + "/"):
        raise PipelinePathError(ref)
    return resolved


@dataclass(frozen=True)
class ResolvedParam:
    """A pipeline parameter value and where it came from."""

    value: str
    source: Literal["registry", "default"]


def resolve_params(pipeline: Pipeline, overrides: Mapping[str, str]) -> dict[str, ResolvedParam]:
    """Resolve each declared param: registry override if present, else its default."""
    return {
        name: (
            ResolvedParam(overrides[name], "registry")
            if name in overrides
            else ResolvedParam(definition.default, "default")
        )
        for name, definition in pipeline.params.items()
    }


class InputError(ValueError):
    """A `--input` argument is malformed or names an undeclared input."""


def parse_input_args(args: Sequence[str], declared: Collection[str]) -> dict[str, str]:
    """Split each `key=value` argument on the first `=`; the last repeated key wins."""
    result: dict[str, str] = {}
    for arg in args:
        key, sep, value = arg.partition("=")
        if not sep or not key:
            raise InputError(f"input argument '{arg}' is not in key=value form; write it as key=value.")
        if key not in declared:
            raise InputError(f"input '{key}' is not declared by the pipeline; use a declared input name.")
        result[key] = value
    return result
