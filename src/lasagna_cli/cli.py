"""Command-line interface of Lasagna."""

import re
from pathlib import Path, PurePosixPath
from typing import Annotated

import typer

from lasagna_cli import __version__
from lasagna_cli.definition import DefinitionError, snapshot_project
from lasagna_cli.engine import Engine, RunContext
from lasagna_cli.eventlog import CorruptLogError, EventWriter, read_events
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
from lasagna_cli.refs import (
    RefError,
    parse_decide_args,
    resolve_phase,
    resolve_run,
    split_run_phase,
)
from lasagna_cli.runs import run_lock_path, run_log_path
from lasagna_cli.runtree import load_root_summaries, load_run_tree
from lasagna_cli.scaffold import init_project
from lasagna_cli.session import RunBusyError, Session, open_session
from lasagna_cli.state import derive_state
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


phase_app = typer.Typer(
    no_args_is_help=True,
    help="Run, complete or fail the open manual (human) phase of a run.",
)
app.add_typer(phase_app, name="phase")


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
    _report(context, code)


def _report(ctx: RunContext, code: int) -> None:
    """Say how the command ended and, for a wait, what the human can do."""
    run_id = ctx.run_id
    if code == EXIT_WAITING:
        state = derive_state(read_events(run_log_path(ctx.root, run_id)))
        typer.echo(f"Run {run_id}: waiting for a human")
        for wait in state.waiting:
            phase = wait.phase.removeprefix(f"{ctx.pipeline.name}/")
            if wait.for_ == "trigger":
                options = "start|skip"
            else:
                options = "|".join(ctx.pipeline.children(phase))
            typer.echo(
                f"  {wait.phase} ({wait.for_}, by {wait.by}): "
                f"lasagna decide {run_id} {phase} {options}"
            )
        for item in state.phases:
            if item.state == "running" and item.mode == "manual":
                phase = item.phase.removeprefix(f"{ctx.pipeline.name}/")
                typer.echo(
                    f"  {item.phase} (manual): lasagna phase done {run_id} {phase}"
                )
    else:
        outcome = {EXIT_OK: "done", EXIT_FAILED: "failed"}
        typer.echo(f"Run {run_id}: {outcome.get(code, 'interrupted')}")
    if code != EXIT_OK:
        raise typer.Exit(code)


@app.command()
def decide(
    args: Annotated[
        list[str],
        typer.Argument(
            help="[RUN] [PHASE] VALUE: start or skip for a trigger, a child phase "
            "for a route. RUN and PHASE can be omitted when only one is waiting."
        ),
    ],
) -> None:
    """Record a human decision and drive the run to the next wait or the end."""
    root = require_project_root()
    try:
        run_arg, phase_arg, value = parse_decide_args(root, args)
        run_id = resolve_run(root, run_arg)
        with open_session(root, run_id) as session:
            _decide(root, session, phase_arg, value)
    except RefError as error:
        raise _fail(str(error)) from None
    except RunBusyError:
        raise _fail("run is being advanced by another command") from None
    except CorruptLogError as error:
        raise _fail(str(error)) from None


def _decide(root: Path, session: Session, phase_arg: str | None, value: str) -> None:
    ctx = session.ctx
    state = session.state()
    if state.status in ("done", "failed", "cancelled"):
        raise _fail(f"run '{ctx.run_id}' is {state.status}; nothing to decide")
    full = resolve_phase(load_run_tree(root, ctx.run_id), phase_arg)
    phase_id = full.removeprefix(f"{ctx.pipeline.name}/")
    waits = [w for w in state.waiting if w.phase == full]
    if not waits:
        raise _fail(f"phase '{phase_id}' is not waiting for a decision")
    wait = waits[0]
    if wait.for_ == "trigger":
        valid = ["start", "skip"]
    elif wait.for_ == "route":
        valid = ctx.pipeline.children(phase_id)
    else:
        raise _fail("loop decisions are not supported yet")
    if value not in valid:
        raise _fail(
            f"invalid value '{value}' for the {wait.for_} of '{phase_id}'; "
            f"valid values: {', '.join(valid)}"
        )
    session.writer.append(
        "decision", phase=full, kind=wait.for_, by=wait.by, value=value
    )
    _report(ctx, Engine(ctx, session.writer).drive())


RunPhaseArgs = Annotated[
    list[str] | None,
    typer.Argument(
        help="[RUN] [PHASE]: both can be omitted when only one is waiting. "
        "The phase is its id or its full name."
    ),
]


def _manual_command(args: list[str] | None, action) -> None:
    """Open the run of a phase command, find the open manual phase, act on it."""
    root = require_project_root()
    try:
        run_arg, phase_arg = split_run_phase(root, args or [])
        run_id = resolve_run(root, run_arg)
        with open_session(root, run_id) as session:
            ctx = session.ctx
            state = session.state()
            if state.status in ("done", "failed", "cancelled"):
                raise _fail(f"run '{run_id}' is {state.status}; nothing to do")
            phase_id = _open_manual_phase(ctx, state, phase_arg)
            engine = Engine(ctx, session.writer)
            code = action(engine, ctx.pipeline.phase(phase_id))
            if code is None:
                code = engine.drive()
            _report(ctx, code)
    except RefError as error:
        raise _fail(str(error)) from None
    except RunBusyError:
        raise _fail("run is being advanced by another command") from None
    except CorruptLogError as error:
        raise _fail(str(error)) from None


def _open_manual_phase(ctx: RunContext, state, given: str | None) -> str:
    prefix = f"{ctx.pipeline.name}/"
    open_names = [
        p.phase for p in state.phases if p.state == "running" and p.mode == "manual"
    ]
    if not open_names:
        raise _fail(f"no manual phase is running in run '{ctx.run_id}'")
    if given is None:
        return open_names[0].removeprefix(prefix)
    full = given if "/" in given else f"{prefix}{given}"
    if full not in open_names:
        raise _fail(
            f"phase '{given}' is not the running manual phase "
            f"(running: {', '.join(open_names)})"
        )
    return full.removeprefix(prefix)


@phase_app.command("run")
def phase_run(args: RunPhaseArgs = None) -> None:
    """Run the command of the open manual phase in the terminal."""

    def action(engine: Engine, phase) -> int | None:
        if "command" not in phase.with_:
            raise _fail("this phase has no command; use lasagna phase done")
        return engine.manual_run(phase.id)

    _manual_command(args, action)


@phase_app.command("done")
def phase_done(
    args: RunPhaseArgs = None,
    output: Annotated[
        list[str] | None,
        typer.Option("--output", help="Value output as name=value. Repeatable."),
    ] = None,
) -> None:
    """Declare the open manual phase done; its changes are committed."""

    def action(engine: Engine, phase) -> int | None:
        written: dict[str, str] = {}
        for item in output or []:
            name, separator, value = item.partition("=")
            if not separator or not name:
                raise _fail(f"invalid --output '{item}': expected name=value")
            declared = phase.outputs.get(name)
            if declared is None or declared.type != "value":
                raise _fail(f"'{name}' is not a declared value output of this phase")
            written[name] = value
        return engine.manual_done(phase.id, written)

    _manual_command(args, action)


@phase_app.command("fail")
def phase_fail(
    args: RunPhaseArgs = None,
    reason: Annotated[
        str | None, typer.Option("--reason", help="Why the phase failed.")
    ] = None,
) -> None:
    """Declare the open manual phase failed; the run fails with it."""

    def action(engine: Engine, phase) -> int | None:
        return engine.manual_fail(phase.id, reason)

    _manual_command(args, action)


def main() -> None:
    """Run the lasagna command."""
    app()
