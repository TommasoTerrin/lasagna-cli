import json

import pytest
from ruamel.yaml import YAML

from lasagna.core.models import Pipeline
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

G_A = """\
# Demo
id: demo
version: 1.0.0
entry: first

Demo for core.

## Params
- area = "core" (default): Area core.
- cmd = "pytest -q" (registry)

## Inputs
- ticket (required): Ticket of core.
- note (optional)

## Outputs
- line: A line.

## Nodes
- first (First) started_by=human gate=check
- second (second) started_by=agent gate=human

## Edges
- first -> second
- second -> first [loop when: Redo a.md, max: 2]
"""


# AC-V3-018
def test_show_text_without_node_renders_pipeline_overview_exactly():
    S = Pipeline.model_validate(YAML(typ="safe").load(S_YAML))
    assert show_text(S, OVS, INS, PD, None, ALL) == G_A

G_B = """\
# demo › first (First)
started_by: human

Work on a.md in core.

## Steps
1. Read a.md.
2. Keep {{ foo }} and ${{ github.x }}.

## Resources
- doc .lasagna/pipelines/demo/assets/guide.md (access: read, required): Guide for a.md.
- path a.md (access: write, optional)

## Gate
type: check
at: exit
by: self
run: pytest -q {{ inputs.ticket }}

## Outgoing edges
- first -> second

## Next nodes
- second (second)
"""

G_C = """\
# demo › first (First)
started_by: human

Work on {{ inputs.ticket }} in core.

## Steps
1. Read {{inputs.ticket}}.
2. Keep {{ foo }} and ${{ github.x }}.

## Resources
- doc .lasagna/pipelines/demo/assets/guide.md (access: read, required): Guide for {{ inputs.ticket }}.
- path {{ inputs.ticket }} (access: write, optional)

## Gate
type: check
at: exit
by: self
run: pytest -q {{ inputs.ticket }}

## Outgoing edges
- first -> second

## Next nodes
- second (second)
"""


# AC-V3-019
def test_show_text_with_node_renders_node_view_exactly():
    S = Pipeline.model_validate(YAML(typ="safe").load(S_YAML))
    assert show_text(S, OVS, INS, PD, "first", ALL) == G_B


# AC-V3-019
def test_show_text_with_node_and_no_inputs_keeps_input_placeholders():
    S = Pipeline.model_validate(YAML(typ="safe").load(S_YAML))
    assert show_text(S, OVS, {}, PD, "first", ALL) == G_C


# AC-V3-018
def test_show_text_renders_each_edge_kind_in_its_compact_form():
    def D(x, y):
        return {"type": "direct", "from": x, "to": y}

    def L(x, y, **k):
        return {"type": "loop", "from": x, "to": y, "max_iterations": 3, **k}

    data = {
        "lasagna": "3.0",
        "id": "demo",
        "entry": "a",
        "nodes": [
            {"id": "a", "description": "A"},
            {"id": "b", "description": "B"},
            {"id": "c", "description": "C"},
        ],
        "edges": [
            D("a", "b"),
            L("b", "a"),
            L("b", "a", when="pass"),
            {
                "type": "router",
                "from": "a",
                "decided_by": "agent",
                "routes": [{"to": "b", "when": "w"}, {"to": "c", "when": "w2"}],
                "default": "c",
            },
            {
                "type": "router",
                "from": "c",
                "decided_by": "check",
                "routes": [{"to": "a", "run": "r"}, {"to": "a", "run": "r2"}],
            },
        ],
    }
    S = Pipeline.model_validate(data)
    out = show_text(S, {}, {}, PD, None, ALL)
    lines = out.split("\n")
    i = lines.index("## Edges")
    assert lines[i + 1 : i + 6] == [
        "- a -> b",
        "- b -> a [loop when: fail, max: 3]",
        "- b -> a [loop when: pass, max: 3]",
        "- a -> b, c [router decided_by: agent, default: c]",
        "- c -> a, a [router decided_by: check]",
    ]


G_EMPTY_TEXT = """# demo
id: demo
entry: a

## Params
(none)

## Inputs
(none)

## Outputs
(none)

## Nodes
- a (a) started_by=agent gate=none

## Edges
(none)
"""

G_EMPTY_JSON = """{
  "id": "demo",
  "name": null,
  "version": null,
  "description": null,
  "entry": "a",
  "params": {},
  "inputs": {},
  "outputs": {},
  "nodes": [
    {
      "id": "a",
      "name": null,
      "started_by": "agent",
      "gate": null
    }
  ],
  "edges": []
}
"""


# AC-V3-018
@pytest.mark.parametrize(
    "render, expected",
    [(show_text, G_EMPTY_TEXT), (show_json, G_EMPTY_JSON)],
    ids=["text", "json"],
)
def test_show_renders_absent_fields_as_empty_values(render, expected):
    Q0 = {
        "lasagna": "3.0",
        "id": "demo",
        "entry": "a",
        "nodes": [{"id": "a", "description": "A"}],
        "edges": [],
    }
    assert render(Pipeline.model_validate(Q0), {}, {}, PD, None, ALL) == expected


# AC-V3-018
@pytest.mark.parametrize("with_key", [False, True], ids=["key-absent", "entry-none"])
def test_show_renders_absent_entry_as_none(with_key):
    Q0 = {
        "lasagna": "3.0",
        "id": "demo",
        "nodes": [{"id": "a", "description": "A"}, {"id": "b", "description": "B"}],
        "edges": [{"type": "direct", "from": "a", "to": "b"}],
    }
    if with_key:
        Q0["entry"] = None
    S = Pipeline.model_validate(Q0)
    assert json.loads(show_json(S, {}, {}, PD, None, ALL))["entry"] is None
    assert "\nentry: (none)\n" in show_text(S, {}, {}, PD, None, ALL)


# AC-V3-018
def test_show_lists_gate_type_and_started_by_per_node():
    A = {"id": "a", "description": "A"}
    B = {"id": "b", "description": "B"}
    C = {"id": "c", "description": "C"}
    nodes = [
        A,
        {**B, "gate": {"type": "human", "message": "m"}},
        {**C, "gate": {"type": "check", "run": "r"}},
        {"id": "d", "description": "D", "started_by": "human", "gate": {"type": "agent", "criteria": ["c"]}},
    ]
    Q0 = {"lasagna": "3.0", "id": "demo", "entry": "a", "nodes": nodes, "edges": []}
    S = Pipeline.model_validate(Q0)
    lines = show_text(S, {}, {}, PD, None, ALL).split("\n")
    i = lines.index("## Nodes")
    assert lines[i + 1 : i + 5] == [
        "- a (a) started_by=agent gate=none",
        "- b (b) started_by=agent gate=human",
        "- c (c) started_by=agent gate=check",
        "- d (d) started_by=human gate=agent",
    ]
    out = json.loads(show_json(S, {}, {}, PD, None, ALL))["nodes"]
    assert [n["gate"] for n in out] == [None, "human", "check", "agent"]
    assert [n["started_by"] for n in out] == ["agent", "agent", "agent", "human"]


# AC-V3-018
# AC-V3-019
@pytest.mark.parametrize("target", ["pipeline", "node"])
def test_description_block_is_stripped_in_text_but_not_in_json(target):
    raw = "  L1\n  L2\n"
    Q0 = {
        "lasagna": "3.0",
        "id": "demo",
        "entry": "a",
        "nodes": [{"id": "a", "description": "A"}, {"id": "b", "description": "B"}],
        "edges": [{"type": "direct", "from": "a", "to": "b"}],
    }
    if target == "pipeline":
        Q0["description"] = raw
        node = None
    else:
        Q0["nodes"][0]["description"] = raw
        node = "a"
    S = Pipeline.model_validate(Q0)
    assert "\n\nL1\n  L2\n\n" in show_text(S, {}, {}, PD, node, ALL)
    doc = json.loads(show_json(S, {}, {}, PD, node, ALL))
    got = doc["description"] if target == "pipeline" else doc["node"]["description"]
    assert got == raw


G_N = """\
# demo › b (Beta)
started_by: agent

B

## Steps
1. s1

## Resources
(none)

## Gate
type: agent
at: entry
by: subagent
criteria:
- c1
- c2

## Outgoing edges
- b -> c, a [router decided_by: agent, default: ghost]
- b -> a [loop when: pass, max: 3]

## Next nodes
- c (c)
- a (a)
"""


# AC-V3-019
def test_show_text_node_view_with_router_loop_and_missing_default_target_exactly():
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
    assert show_text(Pipeline.model_validate(N), {}, {}, PD, "b", ALL) == G_N


_P = {"lasagna": "3.0", "id": "demo", "nodes": [{"id": "a", "description": "A"}], "edges": []}


# AC-V3-015
def test_show_text_without_node_keeps_a_placeholder_in_entry_literal():
    q = {**_P, "entry": "{{ params.p }}", "params": {"p": {"default": "d"}}}
    text = show_text(Pipeline.model_validate(q), {"p": "P"}, {}, PD, None, ALL)
    assert "\nentry: {{ params.p }}\n" in text


# AC-V3-015
def test_show_text_without_node_substitutes_a_placeholder_in_an_output_description():
    q = {**_P, "params": {"p": {"default": "d"}}, "outputs": {"o": {"description": "Out {{ params.p }}"}}}
    text = show_text(Pipeline.model_validate(q), {"p": "P"}, {}, PD, None, ALL)
    assert "\n## Outputs\n- o: Out P\n" in text


# AC-V3-017
def test_show_text_does_not_resolve_pipeline_prefix_in_a_node_description():
    q = {**_P, "nodes": [{"id": "a", "description": "See $pipeline/x"}]}
    text = show_text(Pipeline.model_validate(q), {}, {}, PD, "a", ALL)
    assert "\n\nSee $pipeline/x\n\n" in text


# AC-V3-018
def test_show_text_node_view_shows_none_for_empty_sections():
    text = show_text(Pipeline.model_validate(_P), {}, {}, PD, "a", ALL)
    blocks = text.split("\n\n")
    for title in ("Steps", "Gate", "Outgoing edges", "Next nodes"):
        assert f"## {title}\n(none)" in blocks or f"## {title}\n(none)\n" in blocks
