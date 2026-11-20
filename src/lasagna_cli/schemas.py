"""Bundled primitive schemas and instance validation."""

from collections.abc import Iterable
from datetime import datetime
from functools import cache
from importlib import resources
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError, best_match
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from lasagna_cli import __version__
from lasagna_cli.issues import Issue

PRIMITIVE_KINDS = ("human", "machine", "agent", "pipeline", "phase", "run")


def bundled_primitives_dir() -> Path:
    """Directory holding the schemas shipped with the package."""
    return Path(
        str(resources.files("lasagna_cli") / "templates/lasagna/config/primitives")
    )


def _is_date_time(value: object) -> bool:
    if not isinstance(value, str):
        return True
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


_FORMATS = FormatChecker(formats=())
_FORMATS.checks("date-time")(_is_date_time)


_FORBIDDEN = {"not": {}}


def _forbid_false_properties(node: object) -> object:
    """Rewrite `property: false` as `not: {}`.

    jsonschema drops the property name from the path of a `false` subschema
    error; `not: {}` keeps it, so issues point at the offending field.
    """
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if key == "properties" and isinstance(value, dict):
                out[key] = {
                    name: _FORBIDDEN if sub is False else _forbid_false_properties(sub)
                    for name, sub in value.items()
                }
            else:
                out[key] = _forbid_false_properties(value)
        return out
    if isinstance(node, list):
        return [_forbid_false_properties(item) for item in node]
    return node


@cache
def _registry() -> Registry:
    registry: Registry = Registry()
    for path in sorted(bundled_primitives_dir().glob("*.schema.yaml")):
        contents = _forbid_false_properties(yaml.safe_load(path.read_text("utf-8")))
        resource = Resource.from_contents(contents, default_specification=DRAFT202012)
        registry = registry.with_resource(contents["$id"], resource)
    return registry


@cache
def _validator(kind: str) -> Draft202012Validator:
    if kind not in PRIMITIVE_KINDS:
        raise ValueError(f"unknown primitive kind '{kind}'")
    schema = _registry().get_or_retrieve(f"lasagna:primitives/{kind}").value.contents
    return Draft202012Validator(schema, registry=_registry(), format_checker=_FORMATS)


def _dotted(path: Iterable[object]) -> str:
    out = ""
    for part in path:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += f".{part}" if out else str(part)
    return out


def schema_errors(kind: str, instance: object) -> list[tuple[str, str]]:
    """Return `(field path, message)` pairs for an instance, sorted by path."""
    found: set[tuple[str, str]] = set()
    for error in _validator(kind).iter_errors(instance):
        chosen: ValidationError = error
        if error.context:
            chosen = best_match(error.context) or error
        path = _dotted(error.absolute_path) or _dotted(chosen.absolute_path)
        message = chosen.message
        if chosen.validator == "not" and chosen.validator_value == _FORBIDDEN["not"]:
            message = "not allowed here"
        found.add((path, message))
    return sorted(found)


def primitive_copy_warnings(root: Path) -> list[Issue]:
    """Warn when `.lasagna/config/primitives/` differs from the bundled schemas."""
    warnings: list[Issue] = []
    for bundled in sorted(bundled_primitives_dir().glob("*.schema.yaml")):
        label = f".lasagna/config/primitives/{bundled.name}"
        copy = root / label
        if not copy.is_file():
            message = "missing (bundled schemas are used)"
        elif _lf(copy.read_bytes()) != _lf(bundled.read_bytes()):
            message = f"differs from the schema bundled with lasagna {__version__}"
        else:
            continue
        warnings.append(Issue(label, "", message, "warning"))
    return warnings


def _lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")
