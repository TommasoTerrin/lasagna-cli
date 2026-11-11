"""The views of `lasagna show` (pure)."""

import json
from collections.abc import Callable, Mapping
from typing import Any

from lasagna.core.models import DirectEdge, LoopEdge, Pipeline, RouterEdge
from lasagna.core.render import (
    PipelinePathError,
    render_text,
    resolve_params,
    resolve_pipeline_ref,
)


def _render_edge(edge: DirectEdge | LoopEdge | RouterEdge, params: Mapping[str, str], inputs: Mapping[str, str]) -> dict[str, Any]:
    """Dump an edge with its placeholders rendered (`run` only gets params)."""
    data = edge.model_dump(by_alias=True)
    if isinstance(edge, LoopEdge):
        data["when"] = render_text(edge.when, params, inputs)
    elif isinstance(edge, RouterEdge):
        for route in data["routes"]:
            if route["when"] is not None:
                route["when"] = render_text(route["when"], params, inputs)
            if route["run"] is not None:
                route["run"] = render_text(route["run"], params, {})
    return data


def _optional(text: str | None, params: Mapping[str, str], inputs: Mapping[str, str]) -> str | None:
    return None if text is None else render_text(text, params, inputs)


def _node_document(
    pipeline: Pipeline,
    params: Mapping[str, str],
    inputs: Mapping[str, str],
    pipeline_dir: str,
    node_id: str,
    is_contained: Callable[[str], bool],
) -> dict[str, Any]:
    """Build the with-node JSON document: the rendered node, its outgoing edges and next nodes."""
    node = next(n for n in pipeline.nodes if n.id == node_id)
    data = node.model_dump(by_alias=True)
    data["description"] = _optional(data["description"], params, inputs)
    data["steps"] = [render_text(step, params, inputs) for step in data["steps"]]
    for resource in data["resources"]:
        resource["description"] = _optional(resource["description"], params, inputs)
        ref = render_text(resource["ref"], params, inputs)
        if ref.startswith("$pipeline/"):
            resolved = resolve_pipeline_ref(ref, pipeline_dir)
            if not is_contained(resolved):
                raise PipelinePathError(ref)
            ref = resolved
        resource["ref"] = ref
    gate = data["gate"]
    if gate is not None:
        gate["message"] = _optional(gate["message"], params, inputs)
        gate["run"] = _optional(gate["run"], params, {})
        if gate["criteria"] is not None:
            gate["criteria"] = [render_text(c, params, inputs) for c in gate["criteria"]]
    outgoing = [edge for edge in pipeline.edges if edge.from_ == node_id]
    targets: list[str] = []
    for edge in outgoing:
        if isinstance(edge, RouterEdge):
            targets.extend(route.to for route in edge.routes)
            if edge.default is not None:
                targets.append(edge.default)
        else:
            targets.append(edge.to)
    names = {n.id: n.name for n in pipeline.nodes}
    next_nodes = [{"id": t, "name": names[t]} for t in dict.fromkeys(targets) if t in names]
    return {
        "pipeline": pipeline.id,
        "node": data,
        "edges": [_render_edge(edge, params, inputs) for edge in outgoing],
        "next": next_nodes,
    }


def _compact_edge(edge: dict[str, Any]) -> str:
    """Compact text form of a rendered edge dump."""
    if edge["type"] == "router":
        text = f"{edge['from']} -> {', '.join(route['to'] for route in edge['routes'])}"
        text += f" [router decided_by: {edge['decided_by']}"
        if edge["default"] is not None:
            text += f", default: {edge['default']}"
        return text + "]"
    text = f"{edge['from']} -> {edge['to']}"
    if edge["type"] == "loop":
        text += f" [loop when: {edge['when']}, max: {edge['max_iterations']}]"
    return text


def _with_description(line: str, description: str | None) -> str:
    return line if description is None else f"{line}: {description}"


def _node_text(document: dict[str, Any]) -> str:
    """Render the with-node document as markdown text."""
    node = document["node"]
    blocks = [
        "\n".join([f"# {document['pipeline']} › {node['id']} ({node['name'] or node['id']})", f"started_by: {node['started_by']}"]),
        (node["description"] or "").strip(),
        "\n".join(["## Steps", *(f"{i}. {step}" for i, step in enumerate(node["steps"], 1))] if node["steps"] else ["## Steps", "(none)"]),
    ]
    resource_lines = [
        _with_description(
            f"- {r['type']} {r['ref']} (access: {r['access']}, {'required' if r['required'] else 'optional'})",
            r["description"],
        )
        for r in node["resources"]
    ]
    blocks.append("\n".join(["## Resources", *(resource_lines or ["(none)"])]))
    gate = node["gate"]
    gate_lines = ["(none)"]
    if gate is not None:
        gate_lines = [f"type: {gate['type']}", f"at: {gate['at']}", f"by: {gate['by']}"]
        if gate["message"] is not None:
            gate_lines.append(f"message: {gate['message']}")
        if gate["run"] is not None:
            gate_lines.append(f"run: {gate['run']}")
        if gate["criteria"]:
            gate_lines.append("criteria:")
            gate_lines.extend(f"- {c}" for c in gate["criteria"])
    blocks.append("\n".join(["## Gate", *gate_lines]))
    edge_lines = [f"- {_compact_edge(edge)}" for edge in document["edges"]]
    blocks.append("\n".join(["## Outgoing edges", *(edge_lines or ["(none)"])]))
    next_lines = [f"- {n['id']} ({n['name'] or n['id']})" for n in document["next"]]
    blocks.append("\n".join(["## Next nodes", *(next_lines or ["(none)"])]))
    return "\n\n".join(blocks) + "\n"


def show_text(
    pipeline: Pipeline,
    overrides: Mapping[str, str],
    inputs: Mapping[str, str],
    pipeline_dir: str,
    node_id: str | None,
    is_contained: Callable[[str], bool],
) -> str:
    """Render the pipeline overview as the markdown text of `lasagna show`."""
    resolved = resolve_params(pipeline, overrides)
    params = {name: param.value for name, param in resolved.items()}
    if node_id is not None:
        return _node_text(_node_document(pipeline, params, inputs, pipeline_dir, node_id, is_contained))
    head = [f"# {pipeline.name or pipeline.id}", f"id: {pipeline.id}"]
    if pipeline.version is not None:
        head.append(f"version: {pipeline.version}")
    head.append(f"entry: {pipeline.entry or '(none)'}")
    blocks = ["\n".join(head)]
    if pipeline.description is not None:
        blocks.append(render_text(pipeline.description, params, inputs).strip())
    param_lines = [
        _with_description(
            f"- {name} = {json.dumps(param.value, ensure_ascii=False)} ({param.source})",
            _optional(pipeline.params[name].description, params, inputs),
        )
        for name, param in resolved.items()
    ]
    input_lines = [
        _with_description(
            f"- {name} ({'required' if definition.required else 'optional'})",
            _optional(definition.description, params, inputs),
        )
        for name, definition in pipeline.inputs.items()
    ]
    output_lines = [
        _with_description(f"- {name}", _optional(definition.description, params, inputs))
        for name, definition in pipeline.outputs.items()
    ]
    node_lines = [
        f"- {node.id} ({node.name or node.id}) started_by={node.started_by} "
        f"gate={node.gate.type if node.gate else 'none'}"
        for node in pipeline.nodes
    ]
    edge_lines = [f"- {_compact_edge(_render_edge(edge, params, inputs))}" for edge in pipeline.edges]
    for title, lines in (
        ("Params", param_lines),
        ("Inputs", input_lines),
        ("Outputs", output_lines),
        ("Nodes", node_lines),
        ("Edges", edge_lines),
    ):
        blocks.append("\n".join([f"## {title}", *(lines or ["(none)"])]))
    return "\n\n".join(blocks) + "\n"


def show_json(
    pipeline: Pipeline,
    overrides: Mapping[str, str],
    inputs: Mapping[str, str],
    pipeline_dir: str,
    node_id: str | None,
    is_contained: Callable[[str], bool],
) -> str:
    """Render the pipeline overview as the JSON document of `lasagna show --json`."""
    resolved = resolve_params(pipeline, overrides)
    params = {name: param.value for name, param in resolved.items()}
    if node_id is not None:
        node_document = _node_document(pipeline, params, inputs, pipeline_dir, node_id, is_contained)
        return json.dumps(node_document, indent=2, ensure_ascii=False) + "\n"
    document = {
        "id": pipeline.id,
        "name": pipeline.name,
        "version": pipeline.version,
        "description": _optional(pipeline.description, params, inputs),
        "entry": pipeline.entry,
        "params": {
            name: {
                "value": param.value,
                "source": param.source,
                "description": _optional(pipeline.params[name].description, params, inputs),
            }
            for name, param in resolved.items()
        },
        "inputs": {
            name: {
                "required": definition.required,
                "description": _optional(definition.description, params, inputs),
            }
            for name, definition in pipeline.inputs.items()
        },
        "outputs": {
            name: {"description": _optional(definition.description, params, inputs)}
            for name, definition in pipeline.outputs.items()
        },
        "nodes": [
            {
                "id": node.id,
                "name": node.name,
                "started_by": node.started_by,
                "gate": node.gate.type if node.gate else None,
            }
            for node in pipeline.nodes
        ],
        "edges": [_render_edge(edge, params, inputs) for edge in pipeline.edges],
    }
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"
