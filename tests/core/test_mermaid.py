from pathlib import Path

from ruamel.yaml import YAML

from lasagna.core.mermaid import pipeline_mermaid
from lasagna.core.models import Pipeline

SNAPSHOTS = Path(__file__).parent.parent / "snapshots"


# AC-V3-021
def test_demo_pipeline_diagram_equals_the_committed_snapshot():
    source = (SNAPSHOTS / "graph_demo.pipeline.yaml").read_text(encoding="utf-8")
    pipeline = Pipeline.model_validate(YAML(typ="safe").load(source))
    expected = (SNAPSHOTS / "graph_demo.mmd").read_text(encoding="utf-8")
    assert pipeline_mermaid(pipeline, {}) == expected


# AC-V3-021
def test_nodes_get_positional_ids_in_file_order_even_for_reserved_looking_ids():
    pipeline = Pipeline.model_validate(
        {
            "lasagna": "3.0",
            "id": "ids",
            "name": "Ids",
            "description": "Ids that are dangerous as Mermaid identifiers.",
            "entry": "end",
            "nodes": [
                {"id": "end", "description": "First."},
                {"id": "a--b", "description": "Second."},
                {"id": "subgraph", "description": "Third."},
                {"id": "last", "description": "Fourth."},
            ],
            "edges": [
                {"type": "direct", "from": "end", "to": "a--b"},
                {"type": "direct", "from": "a--b", "to": "subgraph"},
                {"type": "direct", "from": "subgraph", "to": "last"},
                {"type": "loop", "from": "last", "to": "end", "max_iterations": 2},
                {
                    "type": "router",
                    "from": "a--b",
                    "decided_by": "agent",
                    "routes": [{"to": "last"}],
                    "default": "end",
                },
            ],
        }
    )
    expected = (
        "flowchart TD\n"
        '    n1["end"]\n'
        '    n2["a--b"]\n'
        '    n3["subgraph"]\n'
        '    n4["last"]\n'
        "    n1 --> n2\n"
        "    n2 --> n3\n"
        "    n3 --> n4\n"
        '    n4 -.->|"fail, max 2"| n1\n'
        "    n2 --> n4\n"
        '    n2 -->|"default"| n1\n'
    )
    assert pipeline_mermaid(pipeline, {}) == expected


# AC-V3-021
def test_edges_towards_or_from_missing_nodes_are_skipped_and_duplicates_use_the_first():
    dangling = Pipeline.model_validate(
        {
            "lasagna": "3.0",
            "id": "dangling",
            "name": "Dangling",
            "description": "Edges that point at nodes that do not exist.",
            "entry": "a",
            "nodes": [
                {"id": "a", "description": "First."},
                {"id": "b", "description": "Second."},
                {"id": "c", "description": "No edges at all."},
            ],
            "edges": [
                {"type": "direct", "from": "a", "to": "ghost"},
                {"type": "loop", "from": "b", "to": "ghost", "max_iterations": 2},
                {"type": "direct", "from": "ghost", "to": "a"},
                {"type": "direct", "from": "a", "to": "b"},
            ],
        }
    )
    assert pipeline_mermaid(dangling, {}) == (
        "flowchart TD\n"
        '    n1["a"]\n'
        '    n2["b"]\n'
        '    n3["c"]\n'
        "    n1 --> n2\n"
    )

    duplicated = Pipeline.model_validate(
        {
            "lasagna": "3.0",
            "id": "duplicated",
            "name": "Duplicated",
            "description": "Two nodes share the id d.",
            "entry": "a",
            "nodes": [
                {"id": "a", "description": "First."},
                {"id": "d", "description": "First d."},
                {"id": "d", "description": "Second d."},
            ],
            "edges": [
                {"type": "direct", "from": "d", "to": "a"},
                {"type": "direct", "from": "a", "to": "d"},
                {"type": "loop", "from": "d", "to": "a", "max_iterations": 3},
                {"type": "loop", "from": "ghost", "to": "d", "max_iterations": 3},
            ],
        }
    )
    assert pipeline_mermaid(duplicated, {}) == (
        "flowchart TD\n"
        '    n1["a"]\n'
        '    n2["d"]\n'
        '    n3["d"]\n'
        "    n2 --> n1\n"
        "    n1 --> n2\n"
        '    n2 -.->|"fail, max 3"| n1\n'
    )


# AC-V3-021
def test_params_in_when_and_run_are_rendered_with_overrides_but_inputs_and_name_are_not():
    pipeline = Pipeline.model_validate(
        {
            "lasagna": "3.0",
            "id": "tpl",
            "name": "Tpl",
            "description": "Templating in labels.",
            "params": {"x": {"default": "dflt"}, "y": {"default": "why"}},
            "entry": "a",
            "nodes": [
                {"id": "a", "name": "Node {{ params.x }}", "description": "First."},
                {"id": "b", "description": "Second."},
                {"id": "c", "description": "Third."},
            ],
            "edges": [
                {
                    "type": "loop",
                    "from": "b",
                    "to": "a",
                    "when": "again {{ params.x }} / {{ inputs.t }}",
                    "max_iterations": 4,
                },
                {
                    "type": "router",
                    "from": "a",
                    "decided_by": "agent",
                    "routes": [{"to": "b", "when": "{{ params.x }}"}],
                },
                {
                    "type": "router",
                    "from": "b",
                    "decided_by": "check",
                    "routes": [{"to": "c", "run": "cmd {{ params.y }}"}],
                },
            ],
        }
    )
    assert pipeline_mermaid(pipeline, {"x": "over"}) == (
        "flowchart TD\n"
        '    n1["Node {{ params.x }}"]\n'
        '    n2["b"]\n'
        '    n3["c"]\n'
        '    n2 -.->|"again over / {{ inputs.t }}, max 4"| n1\n'
        '    n1 -->|"over"| n2\n'
        '    n2 -->|"cmd why"| n3\n'
    )
    assert pipeline_mermaid(pipeline, {"x": "over", "y": "other"}).splitlines()[-1] == (
        '    n2 -->|"cmd other"| n3'
    )
    assert pipeline_mermaid(pipeline, {}).splitlines()[-3:] == [
        '    n2 -.->|"again dflt / {{ inputs.t }}, max 4"| n1',
        '    n1 -->|"dflt"| n2',
        '    n2 -->|"cmd why"| n3',
    ]


# AC-V3-021
def test_router_skips_only_the_routes_and_default_that_point_at_missing_nodes():
    def build(routes, default):
        return Pipeline.model_validate(
            {
                "lasagna": "3.0",
                "id": "router-ghosts",
                "name": "Router ghosts",
                "description": "A router with some destinations that do not exist.",
                "entry": "a",
                "nodes": [
                    {"id": "a", "description": "First."},
                    {"id": "b", "description": "Second."},
                    {"id": "c", "description": "Third."},
                ],
                "edges": [
                    {
                        "type": "router",
                        "from": "a",
                        "decided_by": "agent",
                        "routes": routes,
                        "default": default,
                    }
                ],
            }
        )

    nodes = (
        "flowchart TD\n"
        '    n1["a"]\n'
        '    n2["b"]\n'
        '    n3["c"]\n'
    )

    ghost_default = build(
        [
            {"to": "b", "when": "x"},
            {"to": "ghost", "when": "y"},
            {"to": "c", "run": "cmd"},
        ],
        "ghost2",
    )
    assert pipeline_mermaid(ghost_default, {}) == (
        nodes + '    n1 -->|"x"| n2\n' + '    n1 -->|"cmd"| n3\n'
    )

    valid_default = build(
        [{"to": "ghost", "when": "y"}, {"to": "b", "when": "x"}],
        "c",
    )
    assert pipeline_mermaid(valid_default, {}) == (
        nodes + '    n1 -->|"x"| n2\n' + '    n1 -->|"default"| n3\n'
    )

    all_ghosts = build([{"to": "ghost"}, {"to": "ghost3", "when": "z"}], "ghost2")
    assert pipeline_mermaid(all_ghosts, {}) == nodes

    bare_route_then_ghost_default = build([{"to": "c"}, {"to": "ghost"}], "ghost2")
    assert pipeline_mermaid(bare_route_then_ghost_default, {}) == nodes + "    n1 --> n3\n"


# AC-V3-021
def test_empty_name_falls_back_to_the_id_and_empty_when_counts_as_present():
    pipeline = Pipeline.model_validate(
        {
            "lasagna": "3.0",
            "id": "empties",
            "name": "Empties",
            "description": "Empty strings in name and when.",
            "entry": "n1",
            "nodes": [
                {"id": "first", "name": "", "description": "First."},
                {"id": "second", "description": "Second."},
            ],
            "edges": [
                {
                    "type": "router",
                    "from": "first",
                    "decided_by": "check",
                    "routes": [{"to": "second", "when": "", "run": "cmd"}],
                }
            ],
        }
    )
    assert pipeline_mermaid(pipeline, {}) == (
        "flowchart TD\n"
        '    n1["first"]\n'
        '    n2["second"]\n'
        '    n1 -->|""| n2\n'
    )
