"""Command line interface of lasagna."""

import sys
from pathlib import Path

import typer

from lasagna import PROTOCOL_VERSION, __version__
from lasagna.core.models import Finding, Registry
from lasagna.core.render import InputError, PipelinePathError, parse_input_args
from lasagna.core.validate import (
    REGISTRY_FILE,
    format_finding,
    pipeline_file,
    render_json,
    validate_project,
)
from lasagna.core.view import show_json, show_text
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
