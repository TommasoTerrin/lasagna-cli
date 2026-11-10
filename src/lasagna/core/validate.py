"""Validation rules for a lasagna project, as pure functions."""

import json
from collections.abc import Mapping, Sequence

from pydantic import ValidationError

from lasagna.core.graph import is_forward, outgoing_edges
from lasagna.core.models import Finding, LoopEdge, Pipeline, Registry, RouterEdge

REGISTRY_FILE: str = ".lasagna/pipelines.yaml"


def pipeline_file(entry_path: str) -> str:
    """Return the project-relative file of the pipeline registered at entry_path."""
    return f".lasagna/{entry_path}/pipeline.yaml"


def _yaml_path(loc: tuple[int | str, ...]) -> str:
    """Convert a pydantic error loc to a YAML path such as 'edges[0].to'."""
    path = ""
    for i, part in enumerate(loc):
        if (
            i >= 2
            and loc[i - 2] == "edges"
            and isinstance(loc[i - 1], int)
            and part in ("direct", "loop", "router")
        ):
            continue
        if part == "[key]":
            continue
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}" if path else str(part)
    return path


def _v01_findings(file: str, error: ValidationError) -> list[Finding]:
    """Return one V01 finding per pydantic error of a file."""
    return [
        Finding(
            "V01",
            file,
            _yaml_path(
                item["loc"] + ("type",)
                if item["type"] in ("union_tag_invalid", "union_tag_not_found")
                and len(item["loc"]) == 2
                and item["loc"][0] == "edges"
                else item["loc"]
            ),
            f"{item['msg']}; fix or remove this value.",
        )
        for item in error.errors()
    ]


def validate_project(
    registry: object,
    pipelines: Mapping[str, object | None],
) -> list[Finding]:
    """Validate loaded project data and return the findings (none if valid)."""
    try:
        reg = Registry.model_validate(registry)
    except ValidationError as error:
        return _v01_findings(REGISTRY_FILE, error)
    findings: list[Finding] = []
    for i, entry in enumerate(reg.pipelines):
        if entry.path not in pipelines:
            continue
        raw = pipelines[entry.path]
        if raw is None:
            findings.append(
                Finding(
                    "V05",
                    REGISTRY_FILE,
                    f"pipelines[{i}].path",
                    f"pipeline file '{pipeline_file(entry.path)}' is missing; "
                    "create it or fix the registry path.",
                )
            )
            continue
        try:
            pipeline = Pipeline.model_validate(raw)
        except ValidationError as error:
            findings.extend(_v01_findings(pipeline_file(entry.path), error))
            continue
        if pipeline.id != entry.id:
            findings.append(
                Finding(
                    "V05",
                    REGISTRY_FILE,
                    f"pipelines[{i}].id",
                    f"registry id '{entry.id}' differs from pipeline id "
                    f"'{pipeline.id}'; make both ids the same.",
                )
            )
        ids = {node.id for node in pipeline.nodes}
        for j, edge in enumerate(pipeline.edges):
            if isinstance(edge, RouterEdge):
                refs = [("from", f"edges[{j}].from", edge.from_)] + [
                    ("to", f"edges[{j}].routes[{k}].to", route.to)
                    for k, route in enumerate(edge.routes)
                ]
            else:
                refs = [
                    ("from", f"edges[{j}].from", edge.from_),
                    ("to", f"edges[{j}].to", edge.to),
                ]
            for key, path, value in refs:
                if value not in ids:
                    findings.append(
                        Finding(
                            "V06",
                            pipeline_file(entry.path),
                            path,
                            f"edge {key} '{value}' is not a node id; "
                            "use the id of a node of this pipeline.",
                        )
                    )
        if pipeline.entry is None:
            findings.append(
                Finding(
                    "V07",
                    pipeline_file(entry.path),
                    "entry",
                    "entry is missing; set it to the id of a node of this pipeline.",
                )
            )
        elif pipeline.entry not in ids:
            findings.append(
                Finding(
                    "V07",
                    pipeline_file(entry.path),
                    "entry",
                    f"entry '{pipeline.entry}' is not a node id; "
                    "use the id of a node of this pipeline.",
                )
            )
        for node_id, outgoing in outgoing_edges(pipeline).items():
            forward = [j for j, edge in outgoing if is_forward(edge)]
            if len(forward) >= 2:
                findings.append(
                    Finding(
                        "V10",
                        pipeline_file(entry.path),
                        f"edges[{forward[1]}]",
                        f"node '{node_id}' has more than one forward edge; "
                        "keep one forward edge or use a router.",
                    )
                )
        gated = {node.id for node in pipeline.nodes if node.gate is not None}
        ungated = {node.id for node in pipeline.nodes if node.gate is None}
        for j, edge in enumerate(pipeline.edges):
            if (
                isinstance(edge, LoopEdge)
                and edge.when == "fail"
                and edge.from_ in ungated - gated
            ):
                findings.append(
                    Finding(
                        "V12",
                        pipeline_file(entry.path),
                        f"edges[{j}]",
                        f"loop edge leaves node '{edge.from_}' which has no gate; "
                        "add a gate to the node.",
                    )
                )
    return findings


def format_finding(finding: Finding) -> str:
    """Render a finding as one plain-text line."""
    where = f"{finding.file} {finding.path}".rstrip()
    return f"{finding.level} {finding.rule} {where}: {finding.message}"


def render_json(findings: Sequence[Finding]) -> str:
    """Render findings as the JSON document of `validate --json`."""

    def entry(f: Finding) -> dict[str, str]:
        return {"rule": f.rule, "file": f.file, "path": f.path, "message": f.message}

    doc = {
        "errors": [entry(f) for f in findings if f.level == "error"],
        "warnings": [entry(f) for f in findings if f.level == "warning"],
    }
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
