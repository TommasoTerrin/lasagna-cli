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


def assert_message_in_f(message):
    problem, fix = message.rsplit("; ", 1)
    assert problem.strip()
    assert re.fullmatch(r"[a-z]\S*( \S+)+\.", fix)


# AC-V3-011
@pytest.mark.parametrize(
    ("edges", "source"),
    [
        pytest.param([D("a", "b"), L("b", "a", when="fail")], "b", id="explicit-fail"),
        pytest.param([D("a", "b"), L("b", "a")], "b", id="default-when-is-fail"),
        pytest.param([D("a", "b"), L("a", "a")], "a", id="self-loop"),
    ],
)
def test_fail_loop_on_a_node_without_gate_is_reported(edges, source):
    pipeline = copy.deepcopy(P0)
    pipeline["edges"] = edges

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == [("V12", PF, "edges[1]")]
    assert_message_in_f(findings[0].message)
    assert f"'{source}'" in findings[0].message


# AC-V3-011
@pytest.mark.parametrize(
    "when",
    [
        pytest.param("pass", id="when-pass"),
        pytest.param("Tests to pass has an unchecked line.", id="free-text-when"),
        pytest.param("Fail", id="capitalised-fail"),
    ],
)
def test_loop_with_when_other_than_exact_fail_is_not_reported(when):
    pipeline = copy.deepcopy(P0)
    pipeline["edges"] = [D("a", "b"), L("b", "a", when=when)]

    assert validate_project(R0, {"pipelines/demo": pipeline}) == []


# AC-V3-011
def test_loop_with_when_fail_plus_trailing_space_is_not_reported():
    pipeline = copy.deepcopy(P0)
    pipeline["edges"] = [D("a", "b"), L("b", "a", when="fail ")]

    assert validate_project(R0, {"pipelines/demo": pipeline}) == []


G = {"type": "human", "message": "m"}


# AC-V3-011
@pytest.mark.parametrize(
    "gate",
    [
        pytest.param(G, id="human-gate"),
        pytest.param({"type": "check", "run": "r"}, id="check-gate"),
        pytest.param({"type": "agent", "criteria": ["c"]}, id="agent-gate"),
        pytest.param({**G, "at": "entry"}, id="human-gate-at-entry"),
    ],
)
def test_fail_loop_on_a_node_with_any_gate_is_not_reported(gate):
    pipeline = copy.deepcopy(P0)
    pipeline["nodes"] = [
        {"id": "a", "description": "A"},
        {"id": "b", "description": "B", "gate": gate},
    ]
    pipeline["edges"] = [D("a", "b"), L("b", "a")]

    assert validate_project(R0, {"pipelines/demo": pipeline}) == []


# AC-V3-011
@pytest.mark.parametrize(
    ("edges", "expected"),
    [
        pytest.param(
            [D("a", "b"), L("b", "a"), L("a", "a")],
            [("V12", PF, "edges[1]"), ("V12", PF, "edges[2]")],
            id="every-guilty-edge-is-reported",
        ),
        pytest.param(
            [D("a", "b"), L("ghost", "a")],
            [("V06", PF, "edges[1].from")],
            id="loop-from-missing-node-is-only-v06",
        ),
    ],
)
def test_fail_loop_rule_reports_each_edge_and_only_on_existing_nodes(edges, expected):
    pipeline = copy.deepcopy(P0)
    pipeline["edges"] = edges

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert sorted((f.rule, f.file, f.path) for f in findings) == sorted(expected)
