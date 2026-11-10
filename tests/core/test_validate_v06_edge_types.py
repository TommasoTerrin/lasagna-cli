import copy

import pytest

from lasagna.core.validate import validate_project

R0 = {"lasagna": "3.0", "pipelines": [{"id": "demo", "path": "pipelines/demo"}]}
P0 = {
    "lasagna": "3.0",
    "id": "demo",
    "entry": "a",
    "nodes": [{"id": "a", "description": "A"}, {"id": "b", "description": "B"}],
    "edges": [{"type": "direct", "from": "a", "to": "b"}],
}
RF = ".lasagna/pipelines.yaml"
PF = ".lasagna/pipelines/demo/pipeline.yaml"


# AC-V3-003
def test_loop_edge_with_unknown_from_and_to_is_reported_for_both_fields():
    pipeline = copy.deepcopy(P0)
    pipeline["edges"].append({"type": "loop", "from": "ghost1", "to": "ghost2", "max_iterations": 3})

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert sorted((f.rule, f.file, f.path) for f in findings) == [
        ("V06", PF, "edges[1].from"),
        ("V06", PF, "edges[1].to"),
    ]


def _router(**changes):
    edge = {
        "type": "router",
        "from": "b",
        "decided_by": "agent",
        "routes": [{"when": "w", "to": "b"}, {"when": "w2", "to": "a"}],
    }
    edge.update(changes)
    return edge


# AC-V3-003
@pytest.mark.parametrize(
    ("edge", "expected"),
    [
        pytest.param(
            _router(**{"from": "ghost"}),
            [("V06", PF, "edges[1].from")],
            id="unknown-from",
        ),
        pytest.param(
            _router(routes=[{"when": "w", "to": "b"}, {"when": "w2", "to": "ghost"}]),
            [("V06", PF, "edges[1].routes[1].to")],
            id="unknown-route-to-at-position-1",
        ),
        pytest.param(_router(), [], id="valid-from-and-routes"),
        pytest.param(_router(default="ghost"), [], id="unknown-default-is-not-v06"),
    ],
)
def test_router_edge_references_are_checked_for_from_and_each_route_to(edge, expected):
    pipeline = copy.deepcopy(P0)
    pipeline["edges"].append(edge)

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert sorted((f.rule, f.file, f.path) for f in findings) == expected
