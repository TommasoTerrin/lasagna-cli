from lasagna.core.validate import validate_project

REGISTRY = {"lasagna": "3.0", "pipelines": [{"id": "demo", "path": "pipelines/demo"}]}


def _pipeline(second_from: str) -> dict:
    return {
        "lasagna": "3.0",
        "id": "demo",
        "entry": "a",
        "nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}, {"id": "d"}],
        "edges": [
            {"type": "direct", "from": "a", "to": "b"},
            {"type": "direct", "from": second_from, "to": "c"},
            {"type": "direct", "from": "c", "to": "d"},
        ],
    }


# AC-V3-003
def test_edge_from_unknown_node_is_reported_once_at_its_index():
    valid = validate_project(REGISTRY, {"pipelines/demo": _pipeline("b")})
    assert valid == []

    findings = validate_project(REGISTRY, {"pipelines/demo": _pipeline("ghost")})
    assert [(f.rule, f.file, f.path) for f in findings] == [
        ("V06", ".lasagna/pipelines/demo/pipeline.yaml", "edges[1].from")
    ]
    assert findings[0].message


# AC-V3-003
def test_every_edge_to_unknown_node_is_reported_at_its_own_index():
    pipeline = _pipeline("b")
    pipeline["edges"][0]["to"] = "ghost"
    pipeline["edges"][2]["to"] = "phantom"

    findings = validate_project(REGISTRY, {"pipelines/demo": pipeline})

    assert sorted((f.rule, f.file, f.path) for f in findings) == [
        ("V06", ".lasagna/pipelines/demo/pipeline.yaml", "edges[0].to"),
        ("V06", ".lasagna/pipelines/demo/pipeline.yaml", "edges[2].to"),
    ]
    assert all(f.message for f in findings)
