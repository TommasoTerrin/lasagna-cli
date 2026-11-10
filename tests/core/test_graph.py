import pytest

from lasagna.core.graph import is_forward, outgoing_edges
from lasagna.core.models import Pipeline

A = {"id": "a", "description": "A"}
B = {"id": "b", "description": "B"}
C = {"id": "c", "description": "C"}


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


def _pipeline(nodes, edges):
    return Pipeline.model_validate(
        {"lasagna": "3.0", "id": "demo", "entry": "a", "nodes": list(nodes), "edges": edges}
    )


# AC-V3-010
@pytest.mark.parametrize(
    ("nodes", "edges", "expected"),
    [
        pytest.param((A, B), [D("a", "b")], {"a": [0], "b": []}, id="p0"),
        pytest.param(
            (A, B, C),
            [D("a", "b"), L("b", "a"), RT("b"), D("c", "a")],
            {"a": [0], "b": [1, 2], "c": [3]},
            id="grouped-by-from-in-file-order",
        ),
        pytest.param(
            (A, B),
            [D("a", "b"), D("ghost", "b")],
            {"a": [0], "b": []},
            id="edge-from-unknown-node-is-left-out",
        ),
        pytest.param((A, A, B), [D("a", "b")], {"a": [0], "b": []}, id="duplicate-node-id-one-key"),
    ],
)
def test_outgoing_edges_groups_file_indexed_edges_by_source_node(nodes, edges, expected):
    pipeline = _pipeline(nodes, edges)

    result = outgoing_edges(pipeline)

    assert set(result) == set(expected)
    assert {k: [i for i, _ in v] for k, v in result.items()} == expected
    for pairs in result.values():
        for index, edge in pairs:
            assert edge is pipeline.edges[index]


# AC-V3-010
def test_is_forward_is_true_for_direct_and_router_edges_and_false_for_loop_edges():
    edges = [D("a", "b"), RT("a"), L("b", "a"), L("b", "a", when="pass"), L("b", "a", when="testo libero")]
    pipeline = _pipeline((A, B), edges)

    result = [is_forward(edge) for edge in pipeline.edges]

    assert result == [True, True, False, False, False]


# AC-V3-010
def test_outgoing_edges_keys_follow_first_appearance_order_in_nodes_not_sorted_order():
    pipeline = _pipeline((B, A), [D("a", "b")])

    result = outgoing_edges(pipeline)

    assert list(result) == ["b", "a"]
