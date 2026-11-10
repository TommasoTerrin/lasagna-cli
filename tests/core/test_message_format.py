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


def D(x, y):
    return {"type": "direct", "from": x, "to": y}


def with_pipeline(**changes):
    p = copy.deepcopy(P0)
    p.update(changes)
    return p


def assert_message_in_f(message):
    problem, fix = message.rsplit("; ", 1)
    assert problem.strip()
    assert re.fullmatch(r"[a-z]\S*( \S+)+\.", fix)


CASES = [
    pytest.param(
        {**R0, "bogus": 1}, {"pipelines/demo": P0}, id="v01-registry-unknown-key"
    ),
    pytest.param(
        R0,
        {"pipelines/demo": with_pipeline(edges=[{"type": "teleport", "from": "a", "to": "b"}])},
        id="v01-pipeline-bad-edge-type",
    ),
    pytest.param(R0, {"pipelines/demo": ["x"]}, id="v01-pipeline-root-not-mapping"),
    pytest.param(["x"], {}, id="v01-registry-root-not-mapping"),
    pytest.param(R0, {"pipelines/demo": None}, id="v05-pipeline-is-none"),
    pytest.param(R0, {"pipelines/demo": with_pipeline(id="other")}, id="v05-id-mismatch"),
    pytest.param(
        R0,
        {"pipelines/demo": with_pipeline(edges=[D("a", "ghost")])},
        id="v06-edge-to-unknown-node",
    ),
]


# AC-V3-045
@pytest.mark.parametrize(("registry", "pipelines"), CASES)
def test_every_existing_rule_message_ends_with_a_correction_phrase(registry, pipelines):
    findings = validate_project(registry, pipelines)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.level == "error"
    assert finding.file.startswith(".lasagna/")
    assert_message_in_f(finding.message)
