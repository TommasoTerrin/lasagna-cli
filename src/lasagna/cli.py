"""Command line interface of lasagna."""

import sys
from pathlib import Path

import typer

from lasagna import PROTOCOL_VERSION, __version__
from lasagna.core.mermaid import pipeline_mermaid
from lasagna.core.models import Finding, Pipeline, Registry
from lasagna.core.render import InputError, PipelinePathError, parse_input_args
from lasagna.core.validate import (
    REGISTRY_FILE,
    format_finding,
    pipeline_file,
    render_json,
    validate_project,
)
from lasagna.core.view import list_item, list_json, list_text, show_json, show_text
from lasagna.shell.builtin import builtin_ids, load_builtin
from lasagna.shell.project import (
    ProjectData,
    containment_check,
    find_project_root,
    load_project,
    pipeline_for_show,
)

app = typer.Typer(add_completion=False)
_INPUT_OPTION = typer.Option([], "--input")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"lasagna {__version__} (protocol {PROTOCOL_VERSION})")
        raise typer.Exit(0)


def _force_utf8_stdout() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")


def _require_root() -> Path:
    root = find_project_root(Path.cwd())
    if root is None:
        typer.echo("error: no .lasagna/ folder found here or in any parent folder", err=True)
        raise typer.Exit(2)
    return root


def _unreadable(data: ProjectData, pipeline_id: str) -> list[Finding]:
    """Return the findings that make the registry or the selected pipeline unreadable."""
    found = [f for f in data.findings if f.file == REGISTRY_FILE]
    if not data.registry_loaded:
        return found
    validated = validate_project(data.registry, data.pipelines)
    found += [f for f in validated if f.rule == "V01" and f.file == REGISTRY_FILE]
    if found:
        return found
    registry = Registry.model_validate(data.registry)
    for i, entry in enumerate(registry.pipelines):
        if entry.id == pipeline_id:
            file = pipeline_file(entry.path)
            found += [f for f in data.findings if f.file == file]
            found += [
                f
                for f in validated
                if (f.rule == "V01" and f.file == file)
                or (f.rule == "V05" and f.file == REGISTRY_FILE and f.path == f"pipelines[{i}].path")
            ]
            break
    return found


def _unreadable_to_list(data: ProjectData, index: int, pipeline_id: str) -> list[Finding]:
    """Return the findings that make the registry entry at index unusable, without duplicates."""
    found = _unreadable(data, pipeline_id)
    registry = Registry.model_validate(data.registry)
    file = pipeline_file(registry.pipelines[index].path)
    for f in data.findings:
        if f.file == file and f not in found:
            found.append(f)
    for f in validate_project(data.registry, data.pipelines):
        is_mine = (
            (f.rule == "V05" and f.path.startswith(f"pipelines[{index}]"))
            or (f.rule == "V01" and f.file == file)
            or (f.rule == "V07" and f.file == file)
        )
        if is_mine and f not in found:
            found.append(f)
    return found


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    """lasagna: a protocol for work processes of coding agents."""


@app.command()
def validate(json_output: bool = typer.Option(False, "--json")) -> None:
    """Validate the `.lasagna/` registry and pipelines."""
    _force_utf8_stdout()
    root = _require_root()
    data = load_project(root)
    findings = list(data.findings)
    if data.registry_loaded:
        findings += validate_project(data.registry, data.pipelines)
    has_errors = any(f.level == "error" for f in findings)
    if json_output:
        typer.echo(render_json(findings), nl=False)
        raise typer.Exit(1 if has_errors else 0)
    for finding in findings:
        typer.echo(format_finding(finding))
    if has_errors:
        raise typer.Exit(1)
    typer.echo("ok: no problems found")


@app.command("list")
def list_pipelines(
    all_entries: bool = typer.Option(False, "--all"),
    builtin: bool = typer.Option(False, "--builtin"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List the pipelines of the registry."""
    _force_utf8_stdout()
    if builtin:
        _require_root()
        found = [list_item(load_builtin(i), {}, None) for i in builtin_ids()]
        typer.echo(list_json(found) if json_output else list_text(found, True), nl=False)
        return
    root = _require_root()
    data = load_project(root)
    broken = _unreadable(data, "")
    if broken:
        for finding in broken:
            typer.echo(format_finding(finding), err=True)
        raise typer.Exit(1)
    registry = Registry.model_validate(data.registry)
    shown = [(i, e) for i, e in enumerate(registry.pipelines) if e.enabled or all_entries]
    unreadable = []
    for i, entry in shown:
        unreadable += [f for f in _unreadable_to_list(data, i, entry.id) if f not in unreadable]
    if unreadable:
        for finding in unreadable:
            typer.echo(format_finding(finding), err=True)
        raise typer.Exit(1)
    items = []
    for entry in registry.pipelines:
        if entry.enabled or all_entries:
            pipeline = Pipeline.model_validate(data.pipelines[entry.path])
            items.append(list_item(pipeline, dict(entry.params), entry.enabled))
    typer.echo(list_json(items) if json_output else list_text(items, False), nl=False)


@app.command()
def graph(
    pipeline_id: str = typer.Argument(...),
    output: str | None = typer.Option(None, "--output"),
) -> None:
    """Print the Mermaid graph of a pipeline."""
    _force_utf8_stdout()
    root = _require_root()
    data = load_project(root)
    broken = _unreadable(data, "")
    if broken:
        for finding in broken:
            typer.echo(format_finding(finding), err=True)
        raise typer.Exit(1)
    ids = [e.id for e in Registry.model_validate(data.registry).pipelines]
    if pipeline_id not in ids:
        known = ", ".join(ids) or "(none)"
        typer.echo(f"error: pipeline '{pipeline_id}' not in the registry; known: {known}", err=True)
        raise typer.Exit(2)
    unreadable = _unreadable_to_list(data, ids.index(pipeline_id), pipeline_id)
    if unreadable:
        for finding in unreadable:
            typer.echo(format_finding(finding), err=True)
        raise typer.Exit(1)
    pipeline, overrides, _ = pipeline_for_show(data, pipeline_id)
    text = pipeline_mermaid(pipeline, overrides)
    if output is not None:
        try:
            Path(output).write_text(text, encoding="utf-8", newline="\n")
        except OSError as error:
            typer.echo(f"error: cannot write {output}: {error.strerror or error}", err=True)
            raise typer.Exit(1) from error
        return
    typer.echo(text, nl=False)


@app.command()
def show(
    pipeline_id: str = typer.Argument(...),
    node: str | None = typer.Argument(None),
    input_args: list[str] = _INPUT_OPTION,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show a pipeline, or one of its nodes, with params and inputs applied."""
    _force_utf8_stdout()
    root = _require_root()
    data = load_project(root)
    unreadable = _unreadable(data, pipeline_id)
    if unreadable:
        for finding in unreadable:
            typer.echo(format_finding(finding), err=True)
        raise typer.Exit(1)
    pipeline, overrides, pipeline_dir = pipeline_for_show(data, pipeline_id)
    try:
        inputs = parse_input_args(input_args, pipeline.inputs.keys())
    except InputError as error:
        typer.echo(f"error: {error}", err=True)
        raise typer.Exit(2) from error
    is_contained = containment_check(root, pipeline_dir)
    render = show_json if json_output else show_text
    try:
        output = render(pipeline, overrides, inputs, pipeline_dir, node, is_contained)
    except PipelinePathError as error:
        typer.echo(
            f"error: resource ref '{error.ref}' leaves the pipeline folder; "
            "keep the path inside it.",
            err=True,
        )
        raise typer.Exit(1) from error
    typer.echo(output, nl=False)
