"""Graph helpers over a validated pipeline (pure)."""

from lasagna.core.models import Edge, LoopEdge, Pipeline


def is_forward(edge: Edge) -> bool:
    """Tell whether an edge moves forward (direct or router) rather than loops."""
    return not isinstance(edge, LoopEdge)


def outgoing_edges(pipeline: Pipeline) -> dict[str, list[tuple[int, Edge]]]:
    """Group the edges of a pipeline by source node, keeping file order."""
    result: dict[str, list[tuple[int, Edge]]] = {}
    for node in pipeline.nodes:
        result.setdefault(node.id, [])
    for index, edge in enumerate(pipeline.edges):
        if edge.from_ in result:
            result[edge.from_].append((index, edge))
    return result
