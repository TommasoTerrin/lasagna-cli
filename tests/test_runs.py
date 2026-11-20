from lasagna_cli.runs import (
    is_child_id,
    list_run_ids,
    run_lock_path,
    run_log_path,
    runs_dir,
)


def test_paths(tmp_path):
    assert runs_dir(tmp_path) == tmp_path / ".lasagna" / "runs"
    assert run_log_path(tmp_path, "bug-fix_03") == (
        tmp_path / ".lasagna/runs/bug-fix_03.jsonl"
    )
    assert run_lock_path(tmp_path, "bug-fix_03.tdd.1") == (
        tmp_path / ".lasagna/runs/bug-fix_03.tdd.1.lock"
    )


def test_is_child_id():
    assert is_child_id("bug-fix_03.tdd.1")
    assert not is_child_id("bug-fix_03")


def test_list_run_ids_only_logs(tmp_path):
    folder = tmp_path / ".lasagna/runs"
    folder.mkdir(parents=True)
    for name in ("b_02.jsonl", "a_01.jsonl", "a_01.lock", "notes.txt"):
        (folder / name).write_text("", encoding="utf-8")
    (folder / "sub.jsonl").mkdir()
    assert list_run_ids(tmp_path) == ["a_01", "b_02"]


def test_list_run_ids_missing_folder(tmp_path):
    assert list_run_ids(tmp_path) == []
