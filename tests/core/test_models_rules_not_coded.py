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

_ONE_ROUTE_ROUTER = {
    "type": "router",
    "from": "a",
    "decided_by": "agent",
    "routes": [{"when": "w", "to": "b"}],
}


# AC-V3-005
@pytest.mark.parametrize(
    "pipeline",
    [
        pytest.param({**P0, "lasagna": "9.9"}, id="incompatible-lasagna-version-v02"),
        pytest.param(
            {
                **P0,
                "nodes": [
                    {"id": "a", "description": "A"},
                    {"id": "Bad_ID", "description": "B"},
                ],
                "edges": [{"type": "direct", "from": "a", "to": "Bad_ID"}],
            },
            id="malformed-node-id-v03",
        ),
        pytest.param({**P0, "version": "banana"}, id="non-semver-version-v04"),
        pytest.param(
            {**P0, "edges": [_ONE_ROUTE_ROUTER]},
            id="router-with-one-route-v13",
        ),
    ],
)
def test_the_model_does_not_judge_what_belongs_to_the_id_rules(pipeline):
    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert findings == []
