import copy
import re

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
PF = ".lasagna/pipelines/demo/pipeline.yaml"


def D(x, y):
    return {"type": "direct", "from": x, "to": y}


def L(x, y, **k):
    return {"type": "loop", "from": x, "to": y, "max_iterations": 3, **k}


def RT(x):
    return {
        "type": "router",
        "from": x,
        "decided_by": "agent",
        "routes": [{"when": "w", "to": "b"}, {"when": "w2", "to": "a"}],
    }


def assert_message_in_f(message):
    problem, fix = message.rsplit("; ", 1)
    assert problem.strip()
    assert re.fullmatch(r"[a-z]\S*( \S+)+\.", fix)


# AC-V3-010
@pytest.mark.parametrize(
    ("edges", "path"),
    [
        pytest.param([D("a", "b"), D("a", "b")], "edges[1]", id="direct-direct"),
        pytest.param([D("a", "b"), RT("a")], "edges[1]", id="direct-router"),
        pytest.param([RT("a"), D("a", "b")], "edges[1]", id="router-direct"),
        pytest.param([RT("a"), RT("a")], "edges[1]", id="router-router"),
        pytest.param(
            [D("a", "b"), D("a", "b"), D("a", "b")], "edges[1]", id="three-direct-one-finding"
        ),
        pytest.param(
            [D("a", "b"), L("a", "a", when="pass"), D("a", "b")],
            "edges[2]",
            id="loop-between-keeps-file-index",
        ),
    ],
)
def test_node_with_two_forward_edges_is_reported_at_the_second(edges, path):
    pipeline = copy.deepcopy(P0)
    pipeline["edges"] = edges

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == [("V10", PF, path)]
    assert_message_in_f(findings[0].message)
    assert "'a'" in findings[0].message


A = {"id": "a", "description": "A"}
B = {"id": "b", "description": "B"}
C = {"id": "c", "description": "C"}


# AC-V3-010
@pytest.mark.parametrize(
    ("nodes", "edges"),
    [
        pytest.param((A, B), [D("a", "b"), L("a", "a", when="pass")], id="direct-plus-loop"),
        pytest.param(
            (A, B),
            [D("a", "b"), L("a", "a", when="pass"), L("a", "a", when="testo libero")],
            id="direct-plus-two-loops",
        ),
        pytest.param((A, B), [RT("a"), L("a", "a", when="pass")], id="router-plus-loop"),
        pytest.param((A, B, C), [D("a", "b"), D("b", "c")], id="one-forward-edge-per-node"),
        pytest.param((A, B), [], id="no-edges"),
    ],
)
def test_node_with_at_most_one_forward_edge_is_not_reported(nodes, edges):
    pipeline = copy.deepcopy(P0)
    pipeline["nodes"] = list(copy.deepcopy(nodes))
    pipeline["edges"] = edges

    assert validate_project(R0, {"pipelines/demo": pipeline}) == []


# AC-V3-010
def test_each_node_with_two_forward_edges_gets_its_own_finding():
    pipeline = copy.deepcopy(P0)
    pipeline["nodes"] = [copy.deepcopy(A), copy.deepcopy(B), copy.deepcopy(C)]
    pipeline["edges"] = [D("a", "b"), D("a", "b"), D("b", "c"), D("b", "c")]

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert sorted((f.rule, f.file, f.path) for f in findings) == [
        ("V10", PF, "edges[1]"),
        ("V10", PF, "edges[3]"),
    ]


# AC-V3-010
def test_edges_from_a_nonexistent_node_do_not_count_for_v10():
    pipeline = copy.deepcopy(P0)
    pipeline["edges"] = [D("a", "b"), D("ghost", "b"), D("ghost", "b")]

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert sorted((f.rule, f.file, f.path) for f in findings) == [
        ("V06", PF, "edges[1].from"),
        ("V06", PF, "edges[2].from"),
    ]
