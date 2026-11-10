from pathlib import Path

import pytest
from ruamel.yaml import YAML

from lasagna.core.validate import validate_project

SPEC = Path(__file__).parents[2] / "docs" / "specs" / "v3.0.0.md"


def spec_yaml_block(number: str):
    lines = SPEC.read_text(encoding="utf-8").splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith(f"### {number} "):
            start = i + 1
            break
    assert start is not None, f"section {number} not found in the spec"
    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("##"):
            end = i
            break
    blocks = []
    current = None
    for line in lines[start:end]:
        if current is None:
            if line.strip() == "```yaml":
                current = []
        elif line.strip().startswith("```"):
            blocks.append("\n".join(current))
            current = None
        else:
            current.append(line)
    assert len(blocks) == 1, f"section {number}: expected 1 yaml block, found {len(blocks)}"
    return YAML(typ="safe").load(blocks[0])


# AC-V3-005
def test_spec_registry_example_with_spec_pipeline_example_validates_clean():
    registry = spec_yaml_block("4.3")
    pipeline = spec_yaml_block("10.1")

    findings = validate_project(registry, {"pipelines/project-manager": pipeline})

    assert findings == [], f"findings: {findings}"


# AC-V3-005
def test_spec_registry_example_with_all_three_spec_pipelines_validates_clean():
    registry = spec_yaml_block("11.1")
    pipelines = {
        "pipelines/project-manager": spec_yaml_block("10.1"),
        "pipelines/implementation": spec_yaml_block("10.2"),
        "pipelines/quick-fix": spec_yaml_block("10.3"),
    }

    findings = validate_project(registry, pipelines)

    assert findings == [], f"findings: {findings}"


# AC-V3-005
def test_spec_pipeline_header_fragment_validates_clean_with_placeholder_graph():
    fragment = dict(spec_yaml_block("4.4"))
    for field in ("name", "version", "description", "params", "inputs", "outputs"):
        assert field in fragment, f"the spec fragment lost the field {field!r}"
    fragment["nodes"] = [{"id": "a", "description": "A"}]
    fragment["edges"] = []
    fragment["entry"] = "a"
    fragment["id"] = "demo"
    registry = {"lasagna": "3.0", "pipelines": [{"id": "demo", "path": "pipelines/demo"}]}

    findings = validate_project(registry, {"pipelines/demo": fragment})

    assert findings == [], f"findings: {findings}"


# AC-V3-005
def test_spec_node_list_fragment_validates_clean_as_single_node_pipeline():
    fragment = spec_yaml_block("4.5")
    assert isinstance(fragment, list) and len(fragment) == 1, f"fragment: {fragment}"
    node = fragment[0]
    for field in ("id", "name", "description", "started_by", "steps", "resources", "gate"):
        assert field in node, f"the spec fragment lost the field {field!r}"
    pipeline = {"lasagna": "3.0", "id": "demo", "entry": node["id"], "nodes": [node]}
    registry = {"lasagna": "3.0", "pipelines": [{"id": "demo", "path": "pipelines/demo"}]}

    findings = validate_project(registry, {"pipelines/demo": pipeline})

    assert findings == [], f"findings: {findings}"


# AC-V3-005
def test_spec_edges_fragment_validates_clean_with_nodes_for_every_cited_id():
    fragment = spec_yaml_block("4.6")
    edges = fragment["edges"]
    by_type = {edge["type"]: edge for edge in edges}
    for edge_type in ("direct", "loop", "router"):
        assert edge_type in by_type, f"the spec fragment lost the {edge_type!r} edge"
    assert "default" in by_type["router"], "the spec router lost its default"

    ids = []
    for edge in edges:
        cited = [edge["from"], edge.get("to")]
        cited += [route["to"] for route in edge.get("routes", [])]
        cited.append(edge.get("default"))
        for node_id in cited:
            if node_id is not None and node_id not in ids:
                ids.append(node_id)

    # V12: a loop that is taken on `when: fail` leaves from a node that has a gate.
    gated = {
        edge["from"]
        for edge in edges
        if edge["type"] == "loop" and edge.get("when", "fail") == "fail"
    }
    gate = {"type": "human", "message": "m"}
    pipeline = {
        "lasagna": "3.0",
        "id": "demo",
        "entry": ids[0],
        "nodes": [
            {"id": node_id, "description": node_id.upper()}
            | ({"gate": gate} if node_id in gated else {})
            for node_id in ids
        ],
        "edges": edges,
    }
    registry = {"lasagna": "3.0", "pipelines": [{"id": "demo", "path": "pipelines/demo"}]}

    findings = validate_project(registry, {"pipelines/demo": pipeline})

    assert findings == [], f"findings: {findings}"


# AC-V3-005
def test_spec_resources_fragment_validates_clean_inside_a_node():
    fragment = spec_yaml_block("4.7")
    assert isinstance(fragment, list) and len(fragment) == 1, f"fragment: {fragment}"
    resource = fragment[0]
    for field in ("type", "ref", "access", "required", "description"):
        assert field in resource, f"the spec fragment lost the field {field!r}"
    node = {"id": "a", "description": "A", "resources": [resource]}
    pipeline = {"lasagna": "3.0", "id": "demo", "entry": "a", "nodes": [node]}
    registry = {"lasagna": "3.0", "pipelines": [{"id": "demo", "path": "pipelines/demo"}]}

    findings = validate_project(registry, {"pipelines/demo": pipeline})

    assert findings == [], f"findings: {findings}"


# AC-V3-005
@pytest.mark.parametrize("gate_type", ["human", "check", "agent"])
def test_spec_gate_fragment_validates_clean_for_each_gate_type(gate_type):
    fragment = spec_yaml_block("4.8")
    assert "gate" in fragment, f"fragment: {fragment}"
    gate = dict(fragment["gate"])
    for field in ("at", "type", "message", "run", "criteria", "by"):
        assert field in gate, f"the spec fragment lost the field {field!r}"
    gate["type"] = gate_type
    node = {"id": "a", "description": "A", "gate": gate}
    pipeline = {"lasagna": "3.0", "id": "demo", "entry": "a", "nodes": [node]}
    registry = {"lasagna": "3.0", "pipelines": [{"id": "demo", "path": "pipelines/demo"}]}

    findings = validate_project(registry, {"pipelines/demo": pipeline})

    assert findings == [], f"findings: {findings}"
