import json

import pytest

from lasagna.core.schema import render_schema


# AC-V3-014
@pytest.mark.parametrize(
    "kind, title",
    [
        pytest.param("registry", "Registry", id="registry"),
        pytest.param("pipeline", "Pipeline", id="pipeline"),
    ],
)
def test_rendered_schema_is_canonical_json_with_a_single_trailing_newline(kind, title):
    text = render_schema(kind)

    assert isinstance(text, str)
    assert text.endswith("\n")
    assert not text.endswith("\n\n")
    assert "\r" not in text
    assert json.loads(text)["title"] == title
    assert text == json.dumps(json.loads(text), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _objects_with_properties(node):
    if isinstance(node, dict):
        if isinstance(node.get("properties"), dict):
            yield node
        for value in node.values():
            yield from _objects_with_properties(value)
    elif isinstance(node, list):
        for value in node:
            yield from _objects_with_properties(value)


# AC-V3-014
def test_schemas_name_the_edge_and_source_origin_from_never_from_underscore():
    pipeline = json.loads(render_schema("pipeline"))
    registry = json.loads(render_schema("registry"))

    for name in ("DirectEdge", "LoopEdge", "RouterEdge"):
        definition = pipeline["$defs"][name]
        assert "from" in definition["properties"], name
        assert "from" in definition["required"], name
    source = registry["$defs"]["Source"]
    assert "from" in source["properties"]
    assert "from" in source["required"]

    for schema in (pipeline, registry):
        for obj in _objects_with_properties(schema):
            assert "from_" not in obj["properties"]


def _schema_object(kind, name):
    schema = json.loads(render_schema(kind))
    if name == schema["title"]:
        return schema
    return schema["$defs"][name]


# AC-V3-014
@pytest.mark.parametrize(
    "kind, name",
    [
        pytest.param("registry", "Registry", id="Registry"),
        pytest.param("registry", "RegistryEntry", id="RegistryEntry"),
        pytest.param("registry", "Source", id="Source"),
        pytest.param("pipeline", "Pipeline", id="Pipeline"),
        pytest.param("pipeline", "ParamDef", id="ParamDef"),
        pytest.param("pipeline", "InputDef", id="InputDef"),
        pytest.param("pipeline", "OutputDef", id="OutputDef"),
        pytest.param("pipeline", "Node", id="Node"),
        pytest.param("pipeline", "Resource", id="Resource"),
        pytest.param("pipeline", "Gate", id="Gate"),
        pytest.param("pipeline", "DirectEdge", id="DirectEdge"),
        pytest.param("pipeline", "LoopEdge", id="LoopEdge"),
        pytest.param("pipeline", "RouterEdge", id="RouterEdge"),
        pytest.param("pipeline", "Route", id="Route"),
    ],
)
def test_fixed_key_object_admits_x_keys_and_rejects_other_unknown_keys_in_the_schema(kind, name):
    definition = _schema_object(kind, name)

    assert definition["patternProperties"] == {"^x-": {}}
    assert definition["additionalProperties"] is False


# AC-V3-014
@pytest.mark.parametrize(
    "kind, name, field",
    [
        pytest.param("pipeline", "Pipeline", "params", id="pipeline-params"),
        pytest.param("pipeline", "Pipeline", "inputs", id="pipeline-inputs"),
        pytest.param("pipeline", "Pipeline", "outputs", id="pipeline-outputs"),
        pytest.param("registry", "RegistryEntry", "params", id="registry-entry-params"),
    ],
)
def test_user_named_maps_forbid_x_keys_as_names_in_the_schema(kind, name, field):
    definition = _schema_object(kind, name)

    assert definition["properties"][field]["propertyNames"] == {"not": {"pattern": "^x-"}}
