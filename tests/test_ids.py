from pathlib import Path

import pytest
from conftest import git

from lasagna_cli.ids import check_custom_id, child_run_id, next_run_id, project_lock
from lasagna_cli.locking import LockBusyError
from lasagna_cli.runs import runs_dir


@pytest.fixture
def root(repo: Path) -> Path:
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    git("add", "-A", cwd=repo)
    git("commit", "-m", "initial", cwd=repo)
    return repo


def touch_log(root: Path, run_id: str) -> None:
    path = runs_dir(root) / f"{run_id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def test_first_id(root: Path) -> None:
    assert next_run_id(root, "bug-fix", "lasagna/") == "bug-fix_01"


def test_next_after_existing(root: Path) -> None:
    touch_log(root, "bug-fix_01")
    touch_log(root, "bug-fix_02")
    assert next_run_id(root, "bug-fix", "lasagna/") == "bug-fix_03"


def test_gaps_use_max_plus_one(root: Path) -> None:
    touch_log(root, "p_01")
    touch_log(root, "p_05")
    assert next_run_id(root, "p", "lasagna/") == "p_06"


def test_after_99_comes_100(root: Path) -> None:
    touch_log(root, "p_99")
    assert next_run_id(root, "p", "lasagna/") == "p_100"


def test_other_pipelines_and_child_logs_are_ignored(root: Path) -> None:
    touch_log(root, "other_07")
    touch_log(root, "p_01.child.1")
    touch_log(root, "p_01.child.9")
    touch_log(root, "p_01")
    assert next_run_id(root, "p", "lasagna/") == "p_02"


def test_pipeline_does_not_match_a_pipeline_with_its_name_as_prefix(
    root: Path,
) -> None:
    touch_log(root, "p_x_04")
    git("branch", "lasagna/p_x_09", cwd=root)
    assert next_run_id(root, "p", "lasagna/") == "p_01"


def test_deleted_logs_do_not_cause_collision_with_old_branches(root: Path) -> None:
    git("branch", "lasagna/bug-fix_05", cwd=root)
    assert next_run_id(root, "bug-fix", "lasagna/") == "bug-fix_06"

    git("branch", "lasagna/bug-fix_07", cwd=root)
    for n in (1, 2, 3):
        touch_log(root, f"bug-fix_{n:02d}")
    assert next_run_id(root, "bug-fix", "lasagna/") == "bug-fix_08"

    for n in (1, 2, 3):
        (runs_dir(root) / f"bug-fix_{n:02d}.jsonl").unlink()
    assert next_run_id(root, "bug-fix", "lasagna/") == "bug-fix_08"


def test_branch_prefix_from_config_is_used(root: Path) -> None:
    git("branch", "x/p_04", cwd=root)
    git("branch", "lasagna/p_09", cwd=root)
    assert next_run_id(root, "p", "x/") == "p_05"


def test_other_branches_and_child_branches_are_ignored(root: Path) -> None:
    git("branch", "lasagna/other_09", cwd=root)
    git("branch", "lasagna/p_01.x.1", cwd=root)
    assert next_run_id(root, "p", "lasagna/") == "p_01"


@pytest.mark.parametrize("run_id", ["fix", "Fix-1", "a_b-c", "9lives"])
def test_valid_custom_ids(root: Path, run_id: str) -> None:
    assert check_custom_id(root, run_id, "lasagna/") is None


@pytest.mark.parametrize("run_id", ["", "a.b", "a/b", "-x", "_x", "a b"])
def test_invalid_custom_ids(root: Path, run_id: str) -> None:
    assert check_custom_id(root, run_id, "lasagna/") == f"invalid run id '{run_id}'"


def test_used_custom_id(root: Path) -> None:
    touch_log(root, "mine")
    assert check_custom_id(root, "mine", "lasagna/") == "run id 'mine' is already used"


def test_custom_id_rejected_when_only_the_branch_exists(root: Path) -> None:
    git("branch", "lasagna/mine", cwd=root)
    assert (
        check_custom_id(root, "mine", "lasagna/")
        == "branch 'lasagna/mine' already exists"
    )


def test_child_run_id() -> None:
    assert child_run_id("p_01", "sub", 2) == "p_01.sub.2"


def test_project_lock_conflicts_when_held_twice(root: Path) -> None:
    first = project_lock(root)
    first.acquire()
    try:
        with pytest.raises(LockBusyError):
            project_lock(root).acquire()
    finally:
        first.release()
    with project_lock(root):
        pass
