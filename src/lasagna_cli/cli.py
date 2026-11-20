"""Command-line interface of Lasagna."""

import re
from pathlib import Path
from typing import Annotated

import typer

from lasagna_cli import __version__
from lasagna_cli.eventlog import CorruptLogError
from lasagna_cli.loader import load_project
from lasagna_cli.project import NotAGitRepoError, find_repo_root
from lasagna_cli.runs import run_log_path
from lasagna_cli.runtree import load_root_summaries, load_run_tree
from lasagna_cli.scaffold import init_project
from lasagna_cli.status import (
    render_json,
    render_runs_json,
    render_runs_text,
    render_text,
)
from lasagna_cli.validation import validate_project

RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
EXIT_WAITING = 3
EXIT_INTERRUPTED = 130

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Orchestrate pipelines whose phases are run by humans, machines or agents.",
)


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"lasagna {__version__}")
        raise typer.Exit(EXIT_OK)


@app.callback()
def root(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_print_version,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
) -> None:
    """Orchestrate pipelines whose phases are run by humans, machines or agents."""


def _fail(message: str) -> typer.Exit:
    typer.echo(message, err=True)
    return typer.Exit(EXIT_USAGE)


def require_project_root() -> Path:
    """Repo root of a project that has `.lasagna/`, or exit 2 with the reason."""
    try:
        root = find_repo_root(Path.cwd())
    except NotAGitRepoError as error:
        raise _fail(str(error)) from None
    if not (root / ".lasagna").is_dir():
        raise _fail("no .lasagna/ found; run lasagna init")
    return root


@app.command()
def init() -> None:
    """Create .lasagna/ with the primitives and default actors."""
    try:
        root = find_repo_root(Path.cwd())
    except NotAGitRepoError as error:
        raise _fail(str(error)) from None
    try:
        init_project(root)
    except FileExistsError:
        raise _fail(".lasagna/ already exists") from None
    typer.echo("Created .lasagna/")


@app.command()
def validate() -> None:
    """Check the schemas and the rules of every actor and pipeline."""
    root = require_project_root()
    project = load_project(root)
    issues = validate_project(project)
    for issue in issues:
        typer.echo(str(issue))
    errors = sum(1 for i in issues if i.severity == "error")
    warnings = len(issues) - errors
    if errors:
        typer.echo(f"{errors} errors, {warnings} warnings")
        raise typer.Exit(EXIT_USAGE)
    typer.echo(
        f"valid: {len(project.actors)} actors, {len(project.pipelines)} pipelines "
        f"({warnings} warnings)"
    )


@app.command()
def status(
    run: Annotated[
        str | None,
        typer.Argument(help="Run id (root or child). Omit it to list the root runs."),
    ] = None,
    as_json: Annotated[
        bool, typer.Option("--json", help="Print the state as JSON.")
    ] = False,
) -> None:
    """Show the state of the runs, derived from their event logs."""
    root = require_project_root()
    try:
        if run is None:
            trees = load_root_summaries(root)
            typer.echo(
                render_runs_json(trees) if as_json else render_runs_text(trees),
                nl=False,
            )
            return
        if not RUN_ID_PATTERN.match(run) or not run_log_path(root, run).is_file():
            raise _fail(f"unknown run '{run}'")
        tree = load_run_tree(root, run)
    except CorruptLogError as error:
        raise _fail(str(error)) from None
    typer.echo(render_json(tree) if as_json else render_text(tree), nl=False)


def main() -> None:
    """Run the lasagna command."""
    app()
