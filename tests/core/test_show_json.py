import copy
import json

import pytest
from ruamel.yaml import YAML

from lasagna.core.models import Pipeline
from lasagna.core.render import PipelinePathError
from lasagna.core.view import show_json, show_text

PD = ".lasagna/pipelines/demo"


def ALL(path):
    return True


S_YAML = """\
lasagna: "3.0"
id: demo
name: "Demo"
version: "1.0.0"
description: "Demo for {{ params.area }}."
params:
  area: { default: "core", description: "Area {{ params.area }}." }
  cmd: { default: "pytest" }
inputs:
  ticket: { description: "Ticket of {{ params.area }}." }
  note: { required: false }
outputs:
  line: { description: "A line." }
entry: first
nodes:
  - id: first
    name: "First"
    description: "Work on {{ inputs.ticket }} in {{ params.area }}."
    started_by: human
    steps:
      - "Read {{inputs.ticket}}."
      - "Keep {{ foo }} and ${{ github.x }}."
    resources:
      - { type: doc, ref: "$pipeline/assets/guide.md", description: "Guide for {{ inputs.ticket }}." }
      - { type: path, ref: "{{ inputs.ticket }}", access: write, required: false }
    gate:
      type: check
      run: "{{ params.cmd }} {{ inputs.ticket }}"
  - id: second
    description: "Second."
    gate: { type: human, message: "OK {{ inputs.ticket }}?" }
edges:
  - { type: direct, from: first, to: second }
  - { type: loop, from: second, to: first, when: "Redo {{ inputs.ticket }}", max_iterations: 2 }
"""

OVS = {"cmd": "pytest -q"}
INS = {"ticket": "a.md"}

G_D = """\
{
  "id": "demo",
  "name": "Demo",
  "version": "1.0.0",
  "description": "Demo for core.",
  "entry": "first",
  "params": {
    "area": {
      "value": "core",
      "source": "default",
      "description": "Area core."
    },
    "cmd": {
      "value": "pytest -q",
      "source": "registry",
      "description": null
    }
  },
  "inputs": {
    "ticket": {
      "required": true,
      "description": "Ticket of core."
    },
    "note": {
      "required": false,
      "description": null
    }
  },
  "outputs": {
    "line": {
      "description": "A line."
    }
  },
  "nodes": [
    {
      "id": "first",
      "name": "First",
      "started_by": "human",
      "gate": "check"
    },
    {
      "id": "second",
      "name": null,
      "started_by": "agent",
      "gate": "human"
    }
  ],
  "edges": [
    {
      "type": "direct",
      "from": "first",
      "to": "second"
    },
    {
      "type": "loop",
      "from": "second",
      "to": "first",
      "when": "Redo a.md",
      "max_iterations": 2
    }
  ]
}
"""

G_E = """{
  "pipeline": "demo",
  "node": {
    "id": "first",
    "description": "Work on a.md in core.",
    "name": "First",
    "started_by": "human",
    "steps": [
      "Read a.md.",
      "Keep {{ foo }} and ${{ github.x }}."
    ],
    "resources": [
      {
        "type": "doc",
        "ref": ".lasagna/pipelines/demo/assets/guide.md",
        "access": "read",
        "required": true,
        "description": "Guide for a.md."
      },
      {
        "type": "path",
        "ref": "a.md",
        "access": "write",
        "required": false,
        "description": null
      }
    ],
    "gate": {
      "type": "check",
      "at": "exit",
      "message": null,
      "run": "pytest -q {{ inputs.ticket }}",
      "criteria": null,
      "by": "self"
    }
  },
  "edges": [
    {
      "type": "direct",
      "from": "first",
      "to": "second"
    }
  ],
  "next": [
    {
      "id": "second",
      "name": null
    }
  ]
}
"""


# AC-V3-018
# AC-V3-016
def test_show_json_without_node_renders_pipeline_overview_exactly():
    S = Pipeline.model_validate(YAML(typ="safe").load(S_YAML))
    assert show_json(S, OVS, INS, PD, None, ALL) == G_D


# AC-V3-019
def test_show_json_with_node_renders_full_node_edges_and_next_exactly():
    S = Pipeline.model_validate(YAML(typ="safe").load(S_YAML))
    assert show_json(S, OVS, INS, PD, "first", ALL) == G_E


def D(x, y):
    return {"type": "direct", "from": x, "to": y}


def L(x, y, **k):
    return {"type": "loop", "from": x, "to": y, "max_iterations": 3, **k}


A = {"id": "a", "description": "A"}
B = {"id": "b", "description": "B"}
Q0 = {
    "lasagna": "3.0",
    "id": "demo",
    "entry": "a",
    "nodes": [A, B],
    "edges": [D("a", "b")],
}
X = "<{{ params.p }}|{{ inputs.i }}>"


def _q(top=None, node_a=None, edges=None):
    q = copy.deepcopy(Q0)
    q["params"] = {"p": {"default": "d"}}
    q["inputs"] = {"i": {}}
    q["outputs"] = {"o": {}}
    q.update(copy.deepcopy(top or {}))
    if node_a:
        q["nodes"][0].update(copy.deepcopy(node_a))
    if edges is not None:
        q["edges"] = copy.deepcopy(edges)
    return q


def _dig(obj, path):
    for k in path:
        obj = obj[k]
    return obj


_CASES = [
    ("description", None, {"description": X}, None, None, ["description"]),
    ("param_desc", None, {"params": {"p": {"default": "d", "description": X}}}, None, None, ["params", "p", "description"]),
    ("input_desc", None, {"inputs": {"i": {"description": X}}}, None, None, ["inputs", "i", "description"]),
    ("output_desc", None, {"outputs": {"o": {"description": X}}}, None, None, ["outputs", "o", "description"]),
    ("node_desc", "a", None, {"description": X}, None, ["node", "description"]),
    ("step", "a", None, {"steps": ["s0", X]}, None, ["node", "steps", 1]),
    ("res_desc", "a", None, {"resources": [{"type": "doc", "ref": "r.md", "description": X}]}, None, ["node", "resources", 0, "description"]),
    ("res_ref", "a", None, {"resources": [{"type": "doc", "ref": X}]}, None, ["node", "resources", 0, "ref"]),
    ("gate_message", "a", None, {"gate": {"type": "human", "message": X}}, None, ["node", "gate", "message"]),
    ("gate_criteria", "a", None, {"gate": {"type": "agent", "criteria": ["c0", X]}}, None, ["node", "gate", "criteria", 1]),
    ("loop_when_node", "a", None, None, [L("a", "a", when=X)], ["edges", 0, "when"]),
    ("loop_when_overview", None, None, None, [D("a", "b"), L("a", "a", when=X)], ["edges", 1, "when"]),
    (
        "route_when",
        "a",
        None,
        None,
        [{"type": "router", "from": "a", "decided_by": "agent", "routes": [{"to": "b", "when": X}, {"to": "a", "when": "w"}]}],
        ["edges", 0, "routes", 0, "when"],
    ),
]


# AC-V3-015
@pytest.mark.parametrize(
    "node,top,node_a,edges,path",
    [c[1:3] + c[3:4] + c[4:] for c in _CASES],
    ids=[c[0] for c in _CASES],
)
def test_show_json_substitutes_templates_in_every_text_field(node, top, node_a, edges, path):
    Q = _q(top, node_a, edges)
    out = json.loads(
        show_json(Pipeline.model_validate(Q), {"p": "P"}, {"i": "I"}, PD, node, ALL)
    )
    assert _dig(out, path) == "<P|I>"


Y0 = "{{ params.p }}"
PL = "$pipeline/x"
_P = {"p": {"default": "d"}}
_ROUTER = {
    "type": "router",
    "from": "a",
    "decided_by": "agent",
    "routes": [{"to": Y0, "when": "w"}, {"to": "a", "when": "w2"}],
    "default": Y0,
}

_LITERAL_CASES = [
    ("id", None, {"id": Y0}, None, None, ["id"], Y0),
    ("name", None, {"name": Y0}, None, None, ["name"], Y0),
    ("entry", None, {"entry": Y0}, None, None, ["entry"], Y0),
    ("node_id", None, {"nodes": [{"id": Y0, "name": Y0, "description": "A"}, B]}, None, None, ["nodes", 0, "id"], Y0),
    ("node_name", None, {"nodes": [{"id": Y0, "name": Y0, "description": "A"}, B]}, None, None, ["nodes", 0, "name"], Y0),
    ("direct_from", None, None, None, [D(Y0, "b")], ["edges", 0, "from"], Y0),
    ("direct_to", None, None, None, [D("a", Y0)], ["edges", 0, "to"], Y0),
    ("loop_from", None, None, None, [L(Y0, "a")], ["edges", 0, "from"], Y0),
    ("loop_to", None, None, None, [L("a", Y0)], ["edges", 0, "to"], Y0),
    ("route_to", None, None, None, [_ROUTER], ["edges", 0, "routes", 0, "to"], Y0),
    ("router_default", None, None, None, [_ROUTER], ["edges", 0, "default"], Y0),
    ("param_default_value", None, {"params": {"p": {"default": "d"}, "q": {"default": Y0}}}, None, None, ["params", "q", "value"], Y0),
    ("registry_value", None, {"params": {"p": {"default": "d"}, "q": {"default": "dq"}}}, None, None, ["params", "q", "value"], Y0),
    ("res_type", "a", None, None, None, None, None),
    ("node_name_with_node", "a", None, {"name": Y0}, None, ["node", "name"], Y0),
    ("pipeline_id_with_node", "a", {"id": Y0, "nodes": [A, B]}, None, None, ["pipeline"], Y0),
    ("pipeline_step", "a", None, {"steps": [PL]}, None, ["node", "steps", 0], PL),
    ("pipeline_gate_run", "a", None, {"gate": {"type": "check", "run": PL}}, None, ["node", "gate", "run"], PL),
    ("pipeline_res_desc", "a", None, {"resources": [{"type": "doc", "ref": "r", "description": PL}]}, None, ["node", "resources", 0, "description"], PL),
    ("pipeline_criteria", "a", None, {"gate": {"type": "agent", "criteria": [PL]}}, None, ["node", "gate", "criteria", 0], PL),
]
# resource type is a closed enum in the models, but the contract asks for it
_LITERAL_CASES[13] = (
    "res_type", "a", None, {"resources": [{"type": Y0, "ref": "r", "description": "d"}]}, None,
    ["node", "resources", 0, "type"], Y0,
)


# AC-V3-015
@pytest.mark.parametrize(
    "node,top,node_a,edges,path,expected",
    [c[1:] for c in _LITERAL_CASES],
    ids=[c[0] for c in _LITERAL_CASES],
)
def test_show_json_keeps_non_text_fields_literal(node, top, node_a, edges, path, expected):
    q = _q(top, node_a, edges)
    ov = {"p": "P"}
    if path[:2] == ["params", "q"]:
        ov = {"p": "P", "q": Y0} if top["params"]["q"]["default"] == "dq" else ov
    out = json.loads(show_json(Pipeline.model_validate(q), ov, {"i": "I"}, PD, node, ALL))
    assert _dig(out, path) == expected


_Q1 = {"params": {"p": {"default": "d"}, "d": {"default": "dd"}}, "inputs": {"i": {}, "f": {}}}
_RUN = "{{ params.p }} {{ inputs.i }}"
_RUN_EDGES = [
    {
        "type": "router",
        "from": "a",
        "decided_by": "check",
        "routes": [{"to": "b", "run": _RUN}, {"to": "a", "run": "r"}],
    }
]


# AC-V3-015
@pytest.mark.parametrize(
    "node_a,edges,path",
    [
        ({"gate": {"type": "check", "run": _RUN}}, None, ["node", "gate", "run"]),
        (None, _RUN_EDGES, ["edges", 0, "routes", 0, "run"]),
    ],
    ids=["gate_run", "route_run"],
)
def test_show_json_run_substitutes_only_params_never_inputs(node_a, edges, path):
    q = _q(_Q1, node_a, edges)
    out = json.loads(show_json(Pipeline.model_validate(q), {"p": "P"}, {"i": "I"}, PD, "a", ALL))
    assert _dig(out, path) == "P {{ inputs.i }}"


# AC-V3-015
@pytest.mark.parametrize(
    "inp,expected",
    [
        ({}, "{{ params.zz }} {{ inputs.zz }} {{ inputs.i }} d"),
        ({"i": "I"}, "{{ params.zz }} {{ inputs.zz }} I d"),
    ],
    ids=["input_not_provided", "input_provided"],
)
def test_show_json_leaves_undeclared_and_unprovided_references_as_written(inp, expected):
    q = _q(None, {"description": "{{ params.zz }} {{ inputs.zz }} {{ inputs.i }} {{ params.p }}"}, None)
    out = json.loads(show_json(Pipeline.model_validate(q), {}, inp, PD, "a", ALL))
    assert out["node"]["description"] == expected


# AC-V3-015
# AC-V3-016
@pytest.mark.parametrize(
    "ov,inp,desc,expected",
    [
        ({"p": "{{ inputs.i }}"}, {"i": "I"}, "{{ params.p }}", "{{ inputs.i }}"),
        ({}, {"i": "{{ params.p }}"}, "{{ inputs.i }}", "{{ params.p }}"),
    ],
    ids=["param_value_not_rescanned", "input_value_not_rescanned"],
)
def test_show_json_substitutes_in_a_single_pass(ov, inp, desc, expected):
    q = _q(_Q1, {"description": desc}, None)
    out = json.loads(show_json(Pipeline.model_validate(q), ov, inp, PD, "a", ALL))
    assert out["node"]["description"] == expected


# AC-V3-017
@pytest.mark.parametrize(
    "res,ov,inp,expected",
    [
        ({"type": "doc", "ref": "$pipeline/assets/x.md"}, {}, {}, ".lasagna/pipelines/demo/assets/x.md"),
        ({"type": "doc", "ref": "$pipeline/{{ inputs.f }}"}, {}, {"f": "assets/x.md"}, ".lasagna/pipelines/demo/assets/x.md"),
        ({"type": "doc", "ref": "{{ params.d }}/x.md"}, {"d": "$pipeline/assets"}, {}, ".lasagna/pipelines/demo/assets/x.md"),
        ({"type": "doc", "ref": "{{ inputs.f }}"}, {}, {"f": "docs/a.md"}, "docs/a.md"),
        ({"type": "doc", "ref": "docs/$pipeline/a.md"}, {}, {}, "docs/$pipeline/a.md"),
        ({"type": "url", "ref": "$pipeline/u"}, {}, {}, ".lasagna/pipelines/demo/u"),
    ],
    ids=["plain", "input_after", "param_after", "input_not_prefix", "not_leading", "url_type"],
)
def test_show_json_resolves_pipeline_prefix_in_ref_after_substitution(res, ov, inp, expected):
    q = _q(_Q1, {"resources": [res]}, None)
    out = json.loads(show_json(Pipeline.model_validate(q), ov, inp, PD, "a", ALL))
    assert out["node"]["resources"][0]["ref"] == expected


def NONE(path):
    return False


# AC-V3-017
@pytest.mark.parametrize(
    "ref,ov,inp,pred,expected",
    [
        ("$pipeline/../x.md", {}, {}, ALL, "$pipeline/../x.md"),
        ("$pipeline/{{ inputs.f }}", {}, {"f": "../../x"}, ALL, "$pipeline/../../x"),
        ("{{ inputs.f }}", {}, {"f": "$pipeline/../x"}, ALL, "$pipeline/../x"),
        ("{{ params.d }}/x", {"d": "$pipeline/.."}, {}, ALL, "$pipeline/../x"),
        ("$pipeline/assets/link/s.md", {}, {}, NONE, "$pipeline/assets/link/s.md"),
    ],
    ids=["dotdot", "input_climbs", "input_is_prefix", "param_climbs", "not_contained"],
)
@pytest.mark.parametrize("fn", [show_json, show_text], ids=["json", "text"])
def test_show_raises_path_error_with_substituted_ref_when_ref_leaves_folder(fn, ref, ov, inp, pred, expected):
    Q = _q(_Q1, {"resources": [{"type": "doc", "ref": ref}]}, None)
    with pytest.raises(PipelinePathError) as ei:
        fn(Pipeline.model_validate(Q), ov, inp, PD, "a", pred)
    assert ei.value.ref == expected


# AC-V3-017
@pytest.mark.parametrize("fn", [show_json, show_text], ids=["json", "text"])
def test_show_does_not_raise_when_contained_predicate_accepts_the_ref(fn):
    Q = _q(_Q1, {"resources": [{"type": "doc", "ref": "$pipeline/assets/link/s.md"}]}, None)
    fn(Pipeline.model_validate(Q), {}, {}, PD, "a", ALL)


# AC-V3-017
@pytest.mark.parametrize("fn", [show_json, show_text], ids=["json", "text"])
def test_show_asks_containment_only_for_pipeline_refs_with_resolved_paths_in_order(fn):
    calls = []

    def inside(path):
        calls.append(path)
        return True

    resources = [
        {"type": "doc", "ref": "$pipeline/assets/x.md"},
        {"type": "doc", "ref": "docs/a.md"},
        {"type": "doc", "ref": "$pipeline/{{ inputs.f }}"},
    ]
    Q = _q(_Q1, {"resources": resources}, None)
    fn(Pipeline.model_validate(Q), {}, {"f": "y.md"}, PD, "a", inside)
    assert calls == [".lasagna/pipelines/demo/assets/x.md", ".lasagna/pipelines/demo/y.md"]


# AC-V3-017
@pytest.mark.parametrize("fn", [show_json, show_text], ids=["json", "text"])
def test_show_reads_only_the_refs_of_the_requested_node(fn):
    nodes = [{**A, "resources": [{"type": "doc", "ref": "$pipeline/../x"}]}, B]
    Q = copy.deepcopy(Q0)
    Q["nodes"] = nodes

    def run(node, inside):
        return fn(Pipeline.model_validate(Q), {}, {}, PD, node, inside)

    def OUT(path):
        return False

    run(None, ALL)
    run("b", ALL)
    with pytest.raises(PipelinePathError):
        run("a", ALL)
    run(None, OUT)
    run("b", OUT)


N = {
    "lasagna": "3.0",
    "id": "demo",
    "entry": "a",
    "nodes": [
        {"id": "a", "description": "A"},
        {
            "id": "b",
            "name": "Beta",
            "description": "B",
            "steps": ["s1"],
            "gate": {"type": "agent", "at": "entry", "criteria": ["c1", "c2"], "by": "subagent"},
        },
        {"id": "c", "description": "C"},
    ],
    "edges": [
        {"type": "direct", "from": "a", "to": "b"},
        {
            "type": "router",
            "from": "b",
            "decided_by": "agent",
            "routes": [{"to": "c", "when": "w"}, {"to": "a", "when": "w2"}],
            "default": "ghost",
        },
        {"type": "loop", "from": "b", "to": "a", "when": "pass", "max_iterations": 3},
        {"type": "direct", "from": "c", "to": "a"},
    ],
}


def _n_named_c():
    n = copy.deepcopy(N)
    n["nodes"][2]["name"] = "Gamma"
    return n


_Q_NO_EDGES = {**copy.deepcopy(Q0), "edges": []}


# AC-V3-019
@pytest.mark.parametrize(
    "src,node,edge_keys,next_",
    [
        (N, "b", [("router", "b"), ("loop", "b")], [{"id": "c", "name": None}, {"id": "a", "name": None}]),
        (N, "c", [("direct", "c")], [{"id": "a", "name": None}]),
        (_Q_NO_EDGES, "a", [], []),
        (_n_named_c(), "b", [("router", "b"), ("loop", "b")], [{"id": "c", "name": "Gamma"}, {"id": "a", "name": None}]),
    ],
    ids=["b_router_and_loop", "c_single_edge", "no_edges", "destination_name_shown"],
)
def test_show_json_node_lists_only_its_outgoing_edges_and_destination_nodes(src, node, edge_keys, next_):
    out = json.loads(show_json(Pipeline.model_validate(copy.deepcopy(src)), {}, {}, PD, node, ALL))
    assert [(e["type"], e["from"]) for e in out["edges"]] == edge_keys
    assert out["next"] == next_


def _shape_cases():
    S = Pipeline.model_validate(YAML(typ="safe").load(S_YAML))
    q = copy.deepcopy(Q0)
    q["nodes"] = [A]
    q["edges"] = []
    return [
        show_json(S, OVS, INS, PD, None, ALL),
        show_json(S, OVS, INS, PD, "first", ALL),
        show_json(Pipeline.model_validate(q), {}, {}, PD, None, ALL),
    ]


# AC-V3-018
# AC-V3-019
@pytest.mark.parametrize("idx", [0, 1, 2], ids=["overview", "node", "empty"])
def test_show_json_is_two_space_indented_unsorted_with_single_final_newline(idx):
    text = _shape_cases()[idx]
    assert text == json.dumps(json.loads(text), indent=2, ensure_ascii=False) + "\n"
    assert text.endswith("\n") and not text.endswith("\n\n")
    assert "\r" not in text


# AC-V3-018
# AC-V3-019
def test_show_json_keeps_non_ascii_characters_unescaped():
    q = copy.deepcopy(Q0)
    q["description"] = "è✓"
    text = show_json(Pipeline.model_validate(q), {}, {}, PD, None, ALL)
    assert "è✓" in text
    assert "\\u00e8" not in text


# AC-V3-015
def test_show_json_keeps_a_node_id_containing_a_placeholder_literal():
    nid = "n-{{ params.p }}"
    q = copy.deepcopy(Q0)
    q["params"] = {"p": {"default": "d"}}
    q["entry"] = nid
    q["nodes"] = [{"id": nid, "description": "A"}, B]
    q["edges"] = []
    doc = json.loads(show_json(Pipeline.model_validate(q), {"p": "P"}, {}, PD, nid, ALL))
    assert doc["node"]["id"] == nid


# AC-V3-017
def test_show_json_does_not_resolve_pipeline_prefix_in_a_node_description():
    q = copy.deepcopy(Q0)
    q["nodes"] = [{"id": "a", "description": "See $pipeline/x"}, B]
    doc = json.loads(show_json(Pipeline.model_validate(q), {}, {}, PD, "a", ALL))
    assert doc["node"]["description"] == "See $pipeline/x"
