"""Command-line interface of Lasagna."""

import re
from pathlib import Path, PurePosixPath
from typing import Annotated

import typer

from lasagna_cli import __version__
from lasagna_cli.definition import DefinitionError, snapshot_project
from lasagna_cli.engine import Engine, RunContext
from lasagna_cli.eventlog import CorruptLogError, EventWriter
from lasagna_cli.gitops import (
    GitError,
    add_worktree,
    has_identity,
    head_commit,
    lasagna_changes,
)
from lasagna_cli.ids import check_custom_id, next_run_id, project_lock
from lasagna_cli.loader import load_project
from lasagna_cli.locking import FileLock, LockBusyError
from lasagna_cli.project import NotAGitRepoError, find_repo_root
from lasagna_cli.runs import run_lock_path, run_log_path
from lasagna_cli.runtree import load_root_summaries, load_run_tree
from lasagna_cli.scaffold import init_project
from lasagna_cli.status import (
    render_json,
    render_runs_json,
    render_runs_text,
    render_text,
)
from lasagna_cli.support import unsupported_features
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
        raise _fail(f"{error}; run git init first") from None
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


def _fail_all(messages: list[str]) -> typer.Exit:
    for message in messages:
        typer.echo(message, err=True)
    return typer.Exit(EXIT_USAGE)


def _parse_inputs(pipeline, given: list[str]) -> dict[str, str]:
    """Check `--input k=v` against the declared inputs and fill the defaults."""
    errors: list[str] = []
    values: dict[str, str] = {}
    for item in given:
        name, separator, value = item.partition("=")
        if not separator or not name:
            errors.append(f"invalid --input '{item}': expected name=value")
        elif name not in pipeline.inputs:
            errors.append(f"unknown input '{name}' for pipeline '{pipeline.name}'")
        else:
            values[name] = value
    for name, spec in pipeline.inputs.items():
        if name in values:
            continue
        if spec.default is not None:
            values[name] = spec.default
        elif spec.required:
            errors.append(f"missing required input '{name}'")
    if errors:
        raise _fail_all(errors)
    return values


@app.command()
def start(
    pipeline: Annotated[str, typer.Argument(help="Name of the pipeline to run.")],
    run_id: Annotated[
        str | None,
        typer.Option("--id", help="Run id to use instead of <pipeline>_<NN>."),
    ] = None,
    inputs: Annotated[
        list[str] | None,
        typer.Option("--input", help="Pipeline input as name=value. Repeatable."),
    ] = None,
    as_actor: Annotated[
        str | None,
        typer.Option("--as", help="Actor starting the run (default: human)."),
    ] = None,
) -> None:
    """Start a run in its own worktree and drive it until the next human wait."""
    root = require_project_root()
    pipelines_dir = root / ".lasagna" / "pipelines"
    known = (
        {p.name for p in pipelines_dir.iterdir() if p.is_dir()}
        if pipelines_dir.is_dir()
        else set()
    )
    if pipeline not in known:
        raise _fail(f"unknown pipeline '{pipeline}'")
    try:
        if not has_identity(root):
            raise _fail("git user.name and user.email must be set")
        changes = lasagna_changes(root)
        if changes:
            raise _fail_all(
                [
                    "uncommitted changes in .lasagna/:",
                    *(f"  {line}" for line in changes),
                    "commit them before starting a run",
                ]
            )
        commit = head_commit(root)
        with snapshot_project(root, commit) as snapshot:
            _start_from_snapshot(
                root, snapshot, commit, pipeline, run_id, inputs or [], as_actor
            )
    except (GitError, DefinitionError) as error:
        raise _fail(str(error)) from None


def _start_from_snapshot(
    root: Path,
    snapshot,
    commit: str,
    pipeline: str,
    run_id: str | None,
    given_inputs: list[str],
    as_actor: str | None,
) -> None:
    errors = [str(i) for i in validate_project(snapshot) if i.severity == "error"]
    if errors:
        raise _fail_all(errors)
    if pipeline not in snapshot.pipelines:
        raise _fail(f"unknown pipeline '{pipeline}' in commit {commit[:12]}")
    unsupported = unsupported_features(snapshot, pipeline)
    if unsupported:
        raise _fail_all(unsupported)

    definition = snapshot.pipelines[pipeline]
    starter = as_actor or "human"
    allowed = ", ".join(definition.trigger_by)
    if as_actor is not None and as_actor not in snapshot.actors:
        raise _fail(f"unknown actor '{as_actor}'")
    if starter not in definition.trigger_by:
        raise _fail(
            f"actor '{starter}' cannot start pipeline '{pipeline}' "
            f"(trigger.by: {allowed})"
        )
    values = _parse_inputs(definition, given_inputs)

    config = snapshot.config
    try:
        ids_lock = project_lock(root)
        ids_lock.acquire()
    except LockBusyError:
        raise _fail("another lasagna command is assigning a run id; retry") from None
    run_lock: FileLock | None = None
    try:
        if run_id is not None:
            problem = check_custom_id(root, run_id, config.branch_prefix)
            if problem:
                raise _fail(problem)
            chosen = run_id
        else:
            chosen = next_run_id(root, pipeline, config.branch_prefix)
        run_lock = FileLock(run_lock_path(root, chosen))
        run_lock.acquire()
        relative = PurePosixPath(config.worktrees_dir.replace("\\", "/")) / chosen
        worktree = root / relative
        branch = f"{config.branch_prefix}{chosen}"
        add_worktree(root, worktree, branch, commit)
        writer = EventWriter(run_log_path(root, chosen), chosen, run_lock)
        writer.append(
            "run_started",
            pipeline=pipeline,
            by=starter,
            inputs=values,
            parent=None,
            worktree=relative.as_posix(),
            branch=branch,
            base_commit=commit,
            definition=commit,
        )
    except BaseException:
        if run_lock is not None:
            run_lock.release()
        raise
    finally:
        ids_lock.release()

    for warning in writer.warnings:
        typer.echo(f"warning: {warning}", err=True)
    typer.echo(f"Started run {chosen} on branch {branch}")
    try:
        context = RunContext(
            root=root,
            run_id=chosen,
            pipeline=definition,
            project=snapshot,
            worktree=worktree,
            inputs=values,
            base_commit=commit,
        )
        code = Engine(context, writer).drive()
    finally:
        run_lock.release()
    outcome = {EXIT_OK: "done", EXIT_FAILED: "failed", EXIT_INTERRUPTED: "interrupted"}
    typer.echo(f"Run {chosen}: {outcome.get(code, 'stopped')}")
    if code != EXIT_OK:
        raise typer.Exit(code)


def main() -> None:
    """Run the lasagna command."""
    app()
