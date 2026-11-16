"""Mermaid flowchart of a pipeline for `lasagna graph` (pure)."""

from collections.abc import Mapping

from lasagna.core.models import DirectEdge, LoopEdge, Pipeline, RouterEdge
from lasagna.core.render import render_text, resolve_params

_GATE_SUFFIX = {"human": " [H]", "check": " [C]", "agent": " [A]"}


def _clean(text: str) -> str:
    return " ".join(text.split()).replace('"', "#quot;")


def pipeline_mermaid(pipeline: Pipeline, overrides: Mapping[str, str]) -> str:
    """Render the pipeline as a Mermaid `flowchart TD`, one line per node and per edge."""
    params = {name: p.value for name, p in resolve_params(pipeline, overrides).items()}
    lines = ["flowchart TD"]
    ids: dict[str, str] = {}
    for index, node in enumerate(pipeline.nodes, start=1):
        short = f"n{index}"
        ids.setdefault(node.id, short)
        label = _clean((node.name or node.id) + (_GATE_SUFFIX[node.gate.type] if node.gate else ""))
        opening, closing = ('["', '"]') if node.started_by == "agent" else ('("', '")')
        lines.append(f"    {short}{opening}{label}{closing}")

    def text(value: str) -> str:
        return _clean(render_text(value, params, {}))

    for edge in pipeline.edges:
        if edge.from_ not in ids:
            continue
        source = ids[edge.from_]
        if isinstance(edge, DirectEdge):
            if edge.to in ids:
                lines.append(f"    {source} --> {ids[edge.to]}")
        elif isinstance(edge, LoopEdge):
            if edge.to in ids:
                label = text(f"{edge.when}, max {edge.max_iterations}")
                lines.append(f'    {source} -.->|"{label}"| {ids[edge.to]}')
        elif isinstance(edge, RouterEdge):
            for route in edge.routes:
                if route.to not in ids:
                    continue
                chosen = route.when if route.when is not None else route.run
                arrow = "-->" if chosen is None else f'-->|"{text(chosen)}"|'
                lines.append(f"    {source} {arrow} {ids[route.to]}")
            if edge.default is not None and edge.default in ids:
                lines.append(f'    {source} -->|"default"| {ids[edge.default]}')
    return "\n".join(lines) + "\n"
