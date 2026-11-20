"""Turn `.lasagna/` into the typed model, collecting issues instead of raising."""

from pathlib import Path

import yaml

from lasagna_cli.config import load_config
from lasagna_cli.issues import Issue
from lasagna_cli.model import (
    Actor,
    AgentCommands,
    Decider,
    Loop,
    Output,
    Param,
    Phase,
    Pipeline,
    PipelineInput,
    Project,
)
from lasagna_cli.schemas import schema_errors

ACTOR_TYPES = ("human", "machine", "agent")
CONFIG_LABEL = ".lasagna/config/lasagna.yaml"


def load_project(root: Path) -> Project:
    """Read `root/.lasagna`; every problem becomes an issue."""
    base = root / ".lasagna"
    config, issues = load_config(base / "config" / "lasagna.yaml", CONFIG_LABEL)
    project = Project(root=root, config=config, issues=issues)
    _load_actors(base, project)
    _load_pipelines(base, project)
    return project


def _read_mapping(path: Path, label: str, issues: list[Issue]) -> dict | None:
    try:
        data = yaml.safe_load(path.read_text("utf-8"))
    except yaml.YAMLError as error:
        reason = " ".join(str(error).split())
        issues.append(Issue(label, "", f"invalid YAML: {reason}"))
        return None
    if not isinstance(data, dict):
        issues.append(Issue(label, "", "must be a mapping"))
        return None
    return data


def _check_schema(kind: str, data: dict, label: str, issues: list[Issue]) -> bool:
    errors = schema_errors(kind, data)
    issues.extend(Issue(label, field, message) for field, message in errors)
    return not errors


def _load_actors(base: Path, project: Project) -> None:
    folder = base / "actors"
    if not folder.is_dir():
        return
    for path in sorted(folder.glob("*.yaml")):
        label = f".lasagna/actors/{path.name}"
        data = _read_mapping(path, label, project.issues)
        if data is None:
            continue
        kind = data.get("type")
        if kind not in ACTOR_TYPES:
            shown = f"'{kind}'" if isinstance(kind, str) else repr(kind)
            message = (
                f"unknown actor type {shown} (extensions are not active in the MVP)"
            )
            project.issues.append(Issue(label, "type", message))
            continue
        if not _check_schema(kind, data, label, project.issues):
            continue
        name = data["name"]
        if name in project.actors:
            other = project.actors[name].file
            message = f"duplicate actor name '{name}' (also in {other})"
            project.issues.append(Issue(label, "name", message))
            continue
        project.actors[name] = _build_actor(data, label)


def _build_actor(data: dict, label: str) -> Actor:
    commands = None
    params: dict[str, Param] = {}
    models: dict[str, str] = {}
    if data["type"] == "agent":
        raw = data["commands"]
        commands = AgentCommands(
            check=tuple(raw.get("check", ())),
            inject=raw.get("inject"),
            run=raw["run"],
            run_interactive=raw.get("run_interactive"),
            cleanup=raw.get("cleanup"),
        )
        params = {
            key: Param(bool(value.get("required", False)), value.get("default"))
            for key, value in data["params"].items()
        }
        models = dict(data.get("models", {}))
    return Actor(
        name=data["name"],
        type=data["type"],
        file=label,
        params=params,
        models=models,
        commands=commands,
    )


def _load_pipelines(base: Path, project: Project) -> None:
    folder = base / "pipelines"
    if not folder.is_dir():
        return
    for directory in sorted(p for p in folder.iterdir() if p.is_dir()):
        dir_label = f".lasagna/pipelines/{directory.name}"
        path = directory / f"{directory.name}.yaml"
        if not path.is_file():
            message = f"missing pipeline file {directory.name}.yaml"
            project.issues.append(Issue(dir_label, "", message))
            continue
        label = f"{dir_label}/{path.name}"
        data = _read_mapping(path, label, project.issues)
        if data is None or not _check_schema("pipeline", data, label, project.issues):
            continue
        if data["name"] != directory.name:
            message = f"must match the folder name '{directory.name}'"
            project.issues.append(Issue(label, "name", message))
            continue
        project.pipelines[data["name"]] = _build_pipeline(data, dir_label, label)


def _decider(raw: dict) -> Decider:
    return Decider(
        by=raw["by"],
        check=raw.get("check"),
        prompt=raw.get("prompt"),
        instructions=raw.get("instructions"),
    )


def _optional_decider(raw: dict | None) -> Decider | None:
    return None if raw is None else _decider(raw)


def _build_phase(index: int, raw: dict) -> Phase:
    harness = raw.get("harness") or {}
    loop = raw.get("loop")
    return Phase(
        index=index,
        id=raw["id"],
        needs=tuple(raw.get("needs", ())),
        actor=raw.get("actor"),
        pipeline=raw.get("pipeline"),
        interactive=bool(raw.get("interactive", False)),
        with_=dict(raw.get("with", {})),
        main_skill=bool(harness.get("main_skill", False)),
        skills=tuple(harness.get("skills", ())),
        mcp=tuple(harness.get("mcp", ())),
        inputs=dict(raw.get("inputs", {})),
        outputs={
            key: Output(type=value["type"], path=value.get("path"))
            for key, value in raw.get("outputs", {}).items()
        },
        trigger=_optional_decider(raw.get("trigger")),
        route=_optional_decider(raw.get("route")),
        loop=Loop(loop["max_iterations"], _decider(loop["until"])) if loop else None,
        timeout=raw.get("timeout"),
        has_harness="harness" in raw,
    )


def _build_pipeline(data: dict, dir_label: str, label: str) -> Pipeline:
    harness = data.get("harness") or {}
    return Pipeline(
        name=data["name"],
        dir=dir_label,
        file=label,
        trigger_by=tuple(data.get("trigger", {}).get("by", ("human",))),
        inputs={
            key: PipelineInput(bool(value.get("required", True)), value.get("default"))
            for key, value in data.get("inputs", {}).items()
        },
        outputs=dict(data.get("outputs", {})),
        skills=tuple(harness.get("skills", ())),
        mcp=tuple(harness.get("mcp", ())),
        phases=tuple(_build_phase(i, raw) for i, raw in enumerate(data["phases"])),
    )
