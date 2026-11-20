import json
from pathlib import Path

import pytest
import yaml

from lasagna_cli.issues import Issue
from lasagna_cli.schemas import bundled_primitives_dir, schema_errors

FIXTURES = Path("tests/fixtures")


@pytest.mark.parametrize(
    "path",
    sorted(FIXTURES.glob("pipelines/*/*.yaml"))
    + [Path("examples/pipelines/spec-to-code/spec-to-code.yaml")],
)
def test_fixture_pipelines_match_schema(path):
    assert schema_errors("pipeline", yaml.safe_load(path.read_text("utf-8"))) == []


def test_template_actors_match_schema():
    actors = bundled_primitives_dir().parent.parent / "actors"
    paths = sorted(actors.glob("*.yaml"))
    assert paths
    for path in paths:
        data = yaml.safe_load(path.read_text("utf-8"))
        assert schema_errors(data["type"], data) == []


def test_fixture_run_events_match_schema():
    paths = sorted(FIXTURES.glob("runs/*.jsonl"))
    assert paths
    for path in paths:
        for line in path.read_text("utf-8").splitlines():
            assert schema_errors("run", json.loads(line)) == []


def test_invalid_timestamp_is_rejected():
    event = {
        "v": 1,
        "seq": 1,
        "ts": "yesterday",
        "run": "r",
        "event": "run_resumed",
        "by": "human",
    }
    assert [p for p, _ in schema_errors("run", event)] == ["ts"]


def test_timestamp_without_timezone_is_rejected():
    event = {
        "v": 1,
        "seq": 1,
        "ts": "2026-01-01T00:00:00",
        "run": "r",
        "event": "run_resumed",
        "by": "human",
    }
    assert [p for p, _ in schema_errors("run", event)] == ["ts"]


def test_error_paths_are_dotted_with_indexes():
    pipeline = {
        "name": "p",
        "phases": [
            {"id": "a", "actor": "machine"},
            {"id": "b", "actor": "x", "interactive": True, "timeout": "1m"},
        ],
    }
    assert "phases[1].timeout" in [p for p, _ in schema_errors("pipeline", pipeline)]


def test_issue_str():
    assert (
        str(Issue("a.yaml", "phases[0].id", "bad"))
        == "error: a.yaml: phases[0].id: bad"
    )
    assert str(Issue("a.yaml", "", "bad", "warning")) == "warning: a.yaml: bad"
