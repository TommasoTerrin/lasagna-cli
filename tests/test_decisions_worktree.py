from pathlib import Path

from conftest import drive_run, git, write_agent_actor, write_pipeline

SNAPSHOT = "lasagna: snapshot before a decision"


def commit(root: Path) -> None:
    git("add", "-A", cwd=root)
    git("commit", "-m", "setup", cwd=root)


def judge(root: Path, decide: str) -> None:
    """Agent `judge`: writes a stray file, then the decision line."""
    write_agent_actor(
        root,
        "judge",
        run=f'echo stray > stray.txt; {decide} >> "$LASAGNA_OUTPUT"',
    )


def machine(id: str, *needs: str, command: str = "true", **extra) -> dict:
    phase: dict = {"id": id, "actor": "machine", "with": {"command": command}}
    if needs:
        phase["needs"] = list(needs)
    phase.update(extra)
    return phase


def setup(root: Path, *phases: dict) -> None:
    write_pipeline(root, {"name": "p", "phases": list(phases)})
    commit(root)


def branch_files(root: Path) -> list[str]:
    return git("ls-tree", "-r", "--name-only", "lasagna/p_01", cwd=root).splitlines()


def outputs_kept(worktree: Path) -> bool:
    return any((worktree / ".lasagna" / "runs").glob("p_01.*.out"))


def test_a_trigger_decision_leaves_no_file(committed_project: Path) -> None:
    judge(committed_project, "echo decision=start")
    setup(
        committed_project,
        machine("a"),
        machine(
            "b",
            "a",
            command="[ ! -e stray.txt ]",
            trigger={"by": "judge", "prompt": "Go?"},
        ),
    )
    result = drive_run(committed_project, "p")
    assert result.code == 0
    assert not (result.worktree / "stray.txt").exists()
    assert "stray.txt" not in branch_files(committed_project)
    assert outputs_kept(result.worktree)


def test_a_route_decision_leaves_no_file(committed_project: Path) -> None:
    judge(committed_project, "echo next=b")
    setup(
        committed_project,
        machine("a", command="echo a > a.txt", route={"by": "judge", "prompt": "?"}),
        machine("b", "a", command="[ ! -e stray.txt ] && echo b > b.txt"),
        machine("c", "a"),
    )
    result = drive_run(committed_project, "p")
    assert result.code == 0
    assert not (result.worktree / "stray.txt").exists()
    assert "stray.txt" not in branch_files(committed_project)
    assert "b.txt" in branch_files(committed_project)
    assert "a.txt" in branch_files(committed_project)


def test_a_loop_decision_keeps_the_work_of_the_iteration(
    committed_project: Path,
) -> None:
    judge(
        committed_project,
        'if [ "$LASAGNA_ITERATION" -ge 2 ]; then echo decision=stop; '
        "else echo decision=continue; fi",
    )
    loop = {"max_iterations": 3, "until": {"by": "judge", "prompt": "Done?"}}
    before = git("rev-list", "--count", "HEAD", cwd=committed_project)
    setup(
        committed_project,
        machine(
            "a",
            command='[ ! -e stray.txt ] && echo w > "work-$LASAGNA_ITERATION.txt"',
            loop=loop,
        ),
    )
    result = drive_run(committed_project, "p")
    assert result.code == 0
    files = branch_files(committed_project)
    assert "work-1.txt" in files and "work-2.txt" in files
    assert "stray.txt" not in files
    assert not (result.worktree / "stray.txt").exists()
    # setup commit + exactly one phase commit, no temporary commit left
    count = git("rev-list", "--count", "lasagna/p_01", cwd=committed_project)
    assert int(count) == int(before) + 2
    subjects = git("log", "--format=%s", "lasagna/p_01", cwd=committed_project)
    assert SNAPSHOT not in subjects
    reflog = git("reflog", "--format=%gs", cwd=result.worktree)
    assert SNAPSHOT in reflog


def test_no_snapshot_when_the_iteration_changed_nothing(
    committed_project: Path,
) -> None:
    judge(committed_project, "echo decision=stop")
    loop = {"max_iterations": 2, "until": {"by": "judge", "prompt": "Done?"}}
    setup(committed_project, machine("a", loop=loop))
    result = drive_run(committed_project, "p")
    assert result.code == 0
    assert not (result.worktree / "stray.txt").exists()
    reflog = git("reflog", "--format=%gs", cwd=result.worktree)
    assert SNAPSHOT not in reflog
