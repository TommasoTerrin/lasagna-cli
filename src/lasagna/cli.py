"""Command line interface of lasagna."""

from pathlib import Path

import typer

from lasagna import PROTOCOL_VERSION, __version__
from lasagna.core.validate import format_finding, validate_project
from lasagna.shell.project import find_project_root, load_project

app = typer.Typer(add_completion=False)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"lasagna {__version__} (protocol {PROTOCOL_VERSION})")
        raise typer.Exit(0)


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
def validate() -> None:
    """Validate the `.lasagna/` registry and pipelines."""
    root = find_project_root(Path.cwd())
    if root is None:
        typer.echo("error: no .lasagna/ folder found here or in any parent folder")
        raise typer.Exit(2)
    data = load_project(root)
    findings = list(data.findings)
    if data.registry_loaded:
        findings += validate_project(data.registry, data.pipelines)
    for finding in findings:
        typer.echo(format_finding(finding))
    if any(f.level == "error" for f in findings):
        raise typer.Exit(1)
    typer.echo("ok: no problems found")
