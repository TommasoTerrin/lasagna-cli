from lasagna.core.validate import validate_project

REGISTRY = {
    "lasagna": "3.0",
    "pipelines": [
        {"id": "demo", "path": "pipelines/demo"},
        {"id": "other", "path": "pipelines/other"},
    ],
}

PIPELINE = {
    "lasagna": "3.0",
    "id": "demo",
    "entry": "a",
    "nodes": [{"id": "a"}, {"id": "b"}],
    "edges": [{"type": "direct", "from": "a", "to": "b"}],
}


# V05
def test_registry_entry_whose_pipeline_file_is_missing_is_reported_once_at_its_path():
    findings = validate_project(
        REGISTRY, {"pipelines/demo": PIPELINE, "pipelines/other": None}
    )

    assert [(f.rule, f.file, f.path) for f in findings] == [
        ("V05", ".lasagna/pipelines.yaml", "pipelines[1].path")
    ]
    assert findings[0].message


# V05
def test_registry_entry_with_no_key_in_pipelines_is_skipped_silently_unlike_a_none_value():
    registry = {
        "lasagna": "3.0",
        "pipelines": [
            {"id": "demo", "path": "pipelines/demo"},
            {"id": "broken", "path": "pipelines/broken"},
        ],
    }

    findings = validate_project(registry, {"pipelines/demo": PIPELINE})

    assert findings == []


# V05
def test_pipeline_whose_id_differs_from_its_registry_entry_is_reported_once_naming_both_ids():
    registry = {"lasagna": "3.0", "pipelines": [{"id": "demo", "path": "pipelines/demo"}]}
    pipeline = {**PIPELINE, "id": "other"}

    findings = validate_project(registry, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == [
        ("V05", ".lasagna/pipelines.yaml", "pipelines[0].id")
    ]
    assert "demo" in findings[0].message
    assert "other" in findings[0].message
