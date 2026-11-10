import pytest

from lasagna.core.validate import validate_project

PIPELINE = {
    "lasagna": "3.0",
    "id": "demo",
    "entry": "a",
    "nodes": [{"id": "a", "description": "A"}, {"id": "b", "description": "B"}],
    "edges": [{"type": "direct", "from": "a", "to": "b"}],
}


# V01
def test_registry_entry_with_an_unknown_key_yields_a_single_v01_naming_the_key_in_its_path():
    registry = {
        "lasagna": "3.0",
        "pipelines": [{"id": "demo", "path": "pipelines/demo", "bogus": 1}],
    }

    findings = validate_project(registry, {"pipelines/demo": PIPELINE})

    assert [(f.rule, f.file, f.path) for f in findings] == [
        ("V01", ".lasagna/pipelines.yaml", "pipelines[0].bogus")
    ]
    assert findings[0].message


# V01
def test_pipeline_with_an_unknown_key_and_a_wrongly_typed_field_yields_one_v01_per_problem_and_nothing_else():
    registry = {
        "lasagna": "3.0",
        "pipelines": [{"id": "demo", "path": "pipelines/demo"}],
    }
    pipeline = {**PIPELINE, "bogus": 1, "nodes": "oops"}

    findings = validate_project(registry, {"pipelines/demo": pipeline})

    assert sorted((f.rule, f.file, f.path) for f in findings) == [
        ("V01", ".lasagna/pipelines/demo/pipeline.yaml", "bogus"),
        ("V01", ".lasagna/pipelines/demo/pipeline.yaml", "nodes"),
    ]


# V01
@pytest.mark.parametrize("root", [["x"], "hello", None], ids=["list", "string", "none"])
def test_registry_root_that_is_not_a_mapping_yields_only_a_file_level_v01_and_no_other_rule(root):
    findings = validate_project(root, {})

    assert [(f.rule, f.file, f.path) for f in findings] == [
        ("V01", ".lasagna/pipelines.yaml", "")
    ]
    assert findings[0].message

    # An invalid registry suppresses every other rule, even with pipelines
    # that would otherwise yield V05 and V06 findings.
    bad_edge = {**PIPELINE, "edges": [{"type": "direct", "from": "a", "to": "zzz"}]}
    invalid_registry = {
        "lasagna": "3.0",
        "bogus": 1,
        "pipelines": [
            {"id": "one", "path": "pipelines/one"},
            {"id": "demo", "path": "pipelines/demo"},
        ],
    }

    findings = validate_project(
        invalid_registry, {"pipelines/one": None, "pipelines/demo": bad_edge}
    )

    assert [(f.rule, f.file, f.path) for f in findings] == [
        ("V01", ".lasagna/pipelines.yaml", "bogus")
    ]
