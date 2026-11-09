"""Validation rules for a lasagna project, as pure functions."""

from collections.abc import Mapping

from pydantic import ValidationError

from lasagna.core.models import Finding, Pipeline, Registry

REGISTRY_FILE: str = ".lasagna/pipelines.yaml"


def pipeline_file(entry_path: str) -> str:
    """Return the project-relative file of the pipeline registered at entry_path."""
    return f".lasagna/{entry_path}/pipeline.yaml"


def _yaml_path(loc: tuple[int | str, ...]) -> str:
    """Convert a pydantic error loc to a YAML path such as 'edges[0].to'."""
    path = ""
    for part in loc:
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
            _yaml_path(item["loc"]),
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
            for key, value in (("from", edge.from_), ("to", edge.to)):
                if value not in ids:
                    findings.append(
                        Finding(
                            "V06",
                            pipeline_file(entry.path),
                            f"edges[{j}].{key}",
                            f"edge {key} '{value}' is not a node id; "
                            "use the id of a node of this pipeline.",
                        )
                    )
    return findings


def format_finding(finding: Finding) -> str:
    """Render a finding as one plain-text line."""
    where = f"{finding.file} {finding.path}".rstrip()
    return f"{finding.level} {finding.rule} {where}: {finding.message}"
