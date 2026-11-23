"""Wiring of the modules the engine is split into (no behaviour of its own)."""

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest
from conftest import git, write_pipeline

import lasagna_cli
from lasagna_cli.deciders import Deciders
from lasagna_cli.definition import snapshot_project
from lasagna_cli.engine import Engine
from lasagna_cli.eventlog import EventWriter
from lasagna_cli.gitops import head_commit
from lasagna_cli.locking import FileLock
from lasagna_cli.manual import ManualPhases
from lasagna_cli.phases import PhaseExecutor
from lasagna_cli.runenv import RunContext, RunEnv
from lasagna_cli.runner import run_shell
from lasagna_cli.runs import run_lock_path, run_log_path

SPLIT_MODULES = ("runenv", "deciders", "phases", "manual")


@pytest.fixture
def run_pair(committed_project: Path) -> Iterator[tuple[RunContext, EventWriter]]:
    write_pipeline(
        committed_project,
        {
            "name": "p",
            "phases": [{"id": "a", "actor": "machine", "with": {"command": "true"}}],
        },
    )
    git("add", "-A", cwd=committed_project)
    git("commit", "-m", "p", cwd=committed_project)
    commit = head_commit(committed_project)
    with snapshot_project(committed_project, commit) as snapshot:
        lock = FileLock(run_lock_path(committed_project, "p_01"))
        lock.acquire()
        try:
            writer = EventWriter(run_log_path(committed_project, "p_01"), "p_01", lock)
            ctx = RunContext(
                root=committed_project,
                run_id="p_01",
                pipeline=snapshot.pipelines["p"],
                project=snapshot,
                worktree=committed_project / ".lasagna" / "worktrees" / "p_01",
                inputs={},
                base_commit=commit,
            )
            yield ctx, writer
        finally:
            lock.release()


def build_run(context_and_writer: tuple[RunContext, EventWriter]) -> RunEnv:
    ctx, writer = context_and_writer
    return RunEnv(ctx, writer, run_shell, "linux")


def test_the_new_classes_are_built_from_a_context_and_a_writer(
    run_pair: tuple[RunContext, EventWriter],
) -> None:
    run = build_run(run_pair)
    deciders = Deciders(run)
    executor = PhaseExecutor(run, deciders)
    manual = ManualPhases(run, executor)
    assert (deciders.run, executor.run, manual.run) == (run, run, run)
    assert run.full("a") == f"{run.ctx.pipeline.name}/a"


def test_the_engine_keeps_its_public_api(
    run_pair: tuple[RunContext, EventWriter],
) -> None:
    ctx, writer = run_pair
    engine = Engine(ctx, writer)
    for name in ("drive", "manual_run", "manual_done", "manual_fail"):
        assert callable(getattr(engine, name))


def test_no_split_module_imports_the_engine() -> None:
    package = Path(lasagna_cli.__file__).parent
    for name in SPLIT_MODULES:
        tree = ast.parse((package / f"{name}.py").read_text(encoding="utf-8"))
        imported = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        } | {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        assert "lasagna_cli.engine" not in imported, name
