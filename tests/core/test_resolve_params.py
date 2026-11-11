import pytest

from lasagna.core.models import Pipeline
from lasagna.core.render import ResolvedParam, resolve_params

A = {"id": "a", "description": "A"}
B = {"id": "b", "description": "B"}
Q0 = {
    "lasagna": "3.0",
    "id": "demo",
    "entry": "a",
    "nodes": [A, B],
    "edges": [{"type": "direct", "from": "a", "to": "b"}],
}


# AC-V3-016
@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        (
            {"a": "ra"},
            {"b": ResolvedParam("db", "default"), "a": ResolvedParam("ra", "registry")},
        ),
        (
            {},
            {"b": ResolvedParam("db", "default"), "a": ResolvedParam("da", "default")},
        ),
        (
            {"a": "da"},
            {"b": ResolvedParam("db", "default"), "a": ResolvedParam("da", "registry")},
        ),
    ],
)
def test_registry_override_wins_over_default_in_declaration_order(overrides, expected):
    pipeline = Pipeline.model_validate(
        {**Q0, "params": {"b": {"default": "db"}, "a": {"default": "da"}}}
    )

    result = resolve_params(pipeline, overrides)

    assert result == expected
    assert list(result) == ["b", "a"]


# AC-V3-016
@pytest.mark.parametrize(
    ("params", "overrides", "expected"),
    [
        (
            {"b": {"default": "db"}, "a": {"default": "da"}},
            {"a": ""},
            {"b": ResolvedParam("db", "default"), "a": ResolvedParam("", "registry")},
        ),
        (
            {"b": {"default": "db"}, "a": {"default": "da"}},
            {"zzz": "v"},
            {"b": ResolvedParam("db", "default"), "a": ResolvedParam("da", "default")},
        ),
        (None, {"a": "v"}, {}),
    ],
)
def test_empty_override_counts_undeclared_override_is_ignored(params, overrides, expected):
    data = dict(Q0) if params is None else {**Q0, "params": params}
    pipeline = Pipeline.model_validate(data)

    result = resolve_params(pipeline, overrides)

    assert result == expected
    assert list(result) == list(expected)
