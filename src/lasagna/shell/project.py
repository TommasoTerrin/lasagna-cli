"""Reads a lasagna project from the file system."""

from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML, YAMLError

from lasagna.core.models import Finding
from lasagna.core.validate import REGISTRY_FILE, pipeline_file


@dataclass(frozen=True)
class ProjectData:
    """Raw data loaded from a project, plus loading problems."""

    root: Path
    registry_loaded: bool
    registry: object | None
    pipelines: dict[str, object | None]
    findings: tuple[Finding, ...]


def find_project_root(start: Path) -> Path | None:
    """Return the nearest folder from start upwards that holds a `.lasagna` folder."""
    for folder in (start, *start.parents):
        if (folder / ".lasagna").is_dir():
            return folder
    return None


def _syntax_finding(file: str, error: YAMLError) -> Finding:
    """Build the V01 finding for a YAML file that cannot be parsed."""
    mark = getattr(error, "problem_mark", None)
    line = f"line {mark.line + 1}: " if mark is not None else ""
    return Finding("V01", file, "", f"malformed YAML at {line}fix the syntax.")


def _empty_finding(file: str, what: str) -> Finding:
    """Build the V01 finding for a YAML file with no content."""
    return Finding("V01", file, "", f"empty YAML file: add the {what} definition.")


def _registry_failed(root: Path, finding: Finding) -> ProjectData:
    """Return the project data of a registry that could not be loaded."""
    return ProjectData(root, False, None, {}, (finding,))


def load_project(root: Path) -> ProjectData:
    """Load the registry and the pipelines it lists."""
    yaml = YAML(typ="safe")
    registry_file = root / ".lasagna" / "pipelines.yaml"
    if not registry_file.exists():
        missing = Finding(
            "V01", REGISTRY_FILE, "", "registry file not found: create .lasagna/pipelines.yaml."
        )
        return _registry_failed(root, missing)
    try:
        registry = yaml.load(registry_file.read_text(encoding="utf-8"))
    except YAMLError as error:
        return _registry_failed(root, _syntax_finding(REGISTRY_FILE, error))
    if registry is None:
        return _registry_failed(root, _empty_finding(REGISTRY_FILE, "registry"))
    if not isinstance(registry, dict):
        return ProjectData(root, True, registry, {}, ())
    pipelines: dict[str, object | None] = {}
    findings: list[Finding] = []
    entries = registry.get("pipelines", [])
    if not isinstance(entries, list):
        entries = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            continue
        path = entry["path"]
        file = root / ".lasagna" / path / "pipeline.yaml"
        if not file.exists():
            pipelines[path] = None
            continue
        try:
            loaded = yaml.load(file.read_text(encoding="utf-8"))
            if loaded is None:
                findings.append(_empty_finding(pipeline_file(path), "pipeline"))
                continue
            pipelines[path] = loaded
        except YAMLError as error:
            findings.append(_syntax_finding(pipeline_file(path), error))
    return ProjectData(root, True, registry, pipelines, tuple(findings))
