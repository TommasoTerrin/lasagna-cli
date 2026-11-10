import copy

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
RF = ".lasagna/pipelines.yaml"
PF = ".lasagna/pipelines/demo/pipeline.yaml"

LOOP = {"type": "loop", "from": "b", "to": "a", "max_iterations": 3}
ROUTER = {
    "type": "router",
    "from": "a",
    "decided_by": "agent",
    "routes": [{"when": "w", "to": "b"}, {"when": "w2", "to": "a"}],
}


def _registry_root(r, p):
    return r


def _registry_entry(r, p):
    return r["pipelines"][0]


def _source(r, p):
    r["pipelines"][0]["source"] = {"from": "x"}
    return r["pipelines"][0]["source"]


def _pipeline_root(r, p):
    return p


def _param_def(r, p):
    p["params"] = {"p": {"default": "d"}}
    return p["params"]["p"]


def _input_def(r, p):
    p["inputs"] = {"i": {}}
    return p["inputs"]["i"]


def _output_def(r, p):
    p["outputs"] = {"o": {}}
    return p["outputs"]["o"]


def _node(r, p):
    return p["nodes"][0]


def _resource(r, p):
    p["nodes"][0]["resources"] = [{"type": "doc", "ref": "x"}]
    return p["nodes"][0]["resources"][0]


def _gate(r, p):
    p["nodes"][0]["gate"] = {"type": "human"}
    return p["nodes"][0]["gate"]


def _direct_edge(r, p):
    return p["edges"][0]


def _loop_edge(r, p):
    p["edges"].append(copy.deepcopy(LOOP))
    return p["edges"][1]


def _router_edge(r, p):
    p["edges"].append(copy.deepcopy(ROUTER))
    return p["edges"][1]


def _route(r, p):
    p["edges"].append(copy.deepcopy(ROUTER))
    return p["edges"][1]["routes"][0]


# AC-V3-006
@pytest.mark.parametrize(
    "locate",
    [
        pytest.param(_registry_root, id="Registry"),
        pytest.param(_registry_entry, id="RegistryEntry"),
        pytest.param(_source, id="Source"),
        pytest.param(_pipeline_root, id="Pipeline"),
        pytest.param(_param_def, id="ParamDef"),
        pytest.param(_input_def, id="InputDef"),
        pytest.param(_output_def, id="OutputDef"),
        pytest.param(_node, id="Node"),
        pytest.param(_resource, id="Resource"),
        pytest.param(_gate, id="Gate"),
        pytest.param(_direct_edge, id="DirectEdge"),
        pytest.param(_loop_edge, id="LoopEdge"),
        pytest.param(_router_edge, id="RouterEdge"),
        pytest.param(_route, id="Route"),
    ],
)
def test_extension_key_is_accepted_in_every_fixed_key_object(locate):
    registry = copy.deepcopy(R0)
    pipeline = copy.deepcopy(P0)
    locate(registry, pipeline)["x-foo"] = "v"

    findings = validate_project(registry, {"pipelines/demo": pipeline})

    assert findings == []


# AC-V3-006
@pytest.mark.parametrize(
    "value",
    [
        pytest.param("s", id="string"),
        pytest.param(3, id="int"),
        pytest.param(True, id="bool"),
        pytest.param(None, id="null"),
        pytest.param([1, "a"], id="list"),
        pytest.param({"k": {"n": [None]}}, id="nested-map"),
    ],
)
def test_extension_key_value_is_free_form(value):
    registry = copy.deepcopy(R0)
    pipeline = copy.deepcopy(P0)
    pipeline["nodes"][0]["x-foo"] = value

    findings = validate_project(registry, {"pipelines/demo": pipeline})

    assert findings == []


# AC-V3-006
@pytest.mark.parametrize(
    "mapname, value, file, path",
    [
        pytest.param("params", {"default": "d"}, PF, "params.x-foo", id="pipeline-params"),
        pytest.param("inputs", {}, PF, "inputs.x-foo", id="pipeline-inputs"),
        pytest.param("outputs", {}, PF, "outputs.x-foo", id="pipeline-outputs"),
        pytest.param("entry-params", "v", RF, "pipelines[0].params.x-foo", id="registry-entry-params"),
    ],
)
def test_extension_key_as_a_user_chosen_name_is_rejected(mapname, value, file, path):
    registry = copy.deepcopy(R0)
    pipeline = copy.deepcopy(P0)
    if mapname == "entry-params":
        registry["pipelines"][0]["params"] = {"x-foo": value}
    else:
        pipeline[mapname] = {"x-foo": value}

    findings = validate_project(registry, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == [("V01", file, path)]


# AC-V3-006
@pytest.mark.parametrize(
    "locate, file, path",
    [
        pytest.param(_registry_root, RF, "bogus", id="Registry"),
        pytest.param(_registry_entry, RF, "pipelines[0].bogus", id="RegistryEntry"),
        pytest.param(_source, RF, "pipelines[0].source.bogus", id="Source"),
        pytest.param(_pipeline_root, PF, "bogus", id="Pipeline"),
        pytest.param(_param_def, PF, "params.p.bogus", id="ParamDef"),
        pytest.param(_input_def, PF, "inputs.i.bogus", id="InputDef"),
        pytest.param(_output_def, PF, "outputs.o.bogus", id="OutputDef"),
        pytest.param(_node, PF, "nodes[0].bogus", id="Node"),
        pytest.param(_resource, PF, "nodes[0].resources[0].bogus", id="Resource"),
        pytest.param(_gate, PF, "nodes[0].gate.bogus", id="Gate"),
        pytest.param(_direct_edge, PF, "edges[0].bogus", id="DirectEdge"),
        pytest.param(_loop_edge, PF, "edges[1].bogus", id="LoopEdge"),
        pytest.param(_router_edge, PF, "edges[1].bogus", id="RouterEdge"),
        pytest.param(_route, PF, "edges[1].routes[0].bogus", id="Route"),
    ],
)
def test_unknown_key_is_rejected_in_every_fixed_key_object(locate, file, path):
    registry = copy.deepcopy(R0)
    pipeline = copy.deepcopy(P0)
    locate(registry, pipeline)["bogus"] = "v"

    findings = validate_project(registry, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == [("V01", file, path)]


# AC-V3-006
@pytest.mark.parametrize(
    "key, expected",
    [
        pytest.param("X-foo", [("V01", PF, "X-foo")], id="uppercase-X"),
        pytest.param("x_foo", [("V01", PF, "x_foo")], id="underscore"),
        pytest.param("xfoo", [("V01", PF, "xfoo")], id="no-separator"),
        pytest.param("x", [("V01", PF, "x")], id="bare-x"),
        pytest.param("x-", [], id="prefix-only"),
    ],
)
def test_only_keys_starting_with_lowercase_x_dash_are_extensions(key, expected):
    registry = copy.deepcopy(R0)
    pipeline = copy.deepcopy(P0)
    pipeline[key] = "v"

    findings = validate_project(registry, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == expected


# AC-V3-006
def test_non_string_key_is_a_single_v01_on_the_pipeline_file_without_raising():
    registry = copy.deepcopy(R0)
    pipeline = copy.deepcopy(P0)
    pipeline[1] = "a"

    findings = validate_project(registry, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file) for f in findings] == [("V01", PF)]


def _keys_at_any_depth(value):
    if isinstance(value, dict):
        for key, inner in value.items():
            yield key
            yield from _keys_at_any_depth(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _keys_at_any_depth(inner)


# AC-V3-006
def test_extension_keys_never_enter_the_model():
    from lasagna.core.models import Pipeline, Registry

    registry = copy.deepcopy(R0)
    pipeline = copy.deepcopy(P0)
    for locate in (
        _registry_root,
        _registry_entry,
        _source,
        _pipeline_root,
        _param_def,
        _input_def,
        _output_def,
        _node,
        _resource,
        _gate,
        _direct_edge,
        _loop_edge,
    ):
        locate(registry, pipeline)["x-foo"] = {"k": [1, {"n": None}]}
    router = copy.deepcopy(ROUTER)
    router["x-foo"] = {"k": [1, {"n": None}]}
    router["routes"][0]["x-foo"] = {"k": [1, {"n": None}]}
    pipeline["edges"].append(router)

    registry_dump = Registry.model_validate(registry).model_dump()
    pipeline_dump = Pipeline.model_validate(pipeline).model_dump()

    assert registry_dump["lasagna"] == "3.0"
    assert pipeline_dump["lasagna"] == "3.0"
    assert pipeline_dump["id"] == "demo"
    for dump in (registry_dump, pipeline_dump):
        offending = [
            k for k in _keys_at_any_depth(dump) if isinstance(k, str) and k.startswith("x-")
        ]
        assert offending == []
