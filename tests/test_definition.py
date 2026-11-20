import io
import zipfile
from pathlib import Path

import pytest
from conftest import base_pipeline, git, machine_pipeline, write_pipeline

from lasagna_cli.definition import DefinitionError, extract_lasagna, snapshot_project
from lasagna_cli.gitops import head_commit
from lasagna_cli.validation import validate_project


def commands_of(project, name: str) -> list[str]:
    return [p.with_["command"] for p in project.pipelines[name].phases]


def test_snapshot_reads_the_commit_not_the_working_copy(project: Path) -> None:
    machine_pipeline(project, "p", "echo one", "echo two")
    git("add", "-A", cwd=project)
    git("commit", "-m", "p", cwd=project)
    commit = head_commit(project)

    machine_pipeline(project, "p", "echo changed")
    machine_pipeline(project, "extra", "true")

    with snapshot_project(project, commit) as snapshot:
        assert sorted(snapshot.pipelines) == ["p"]
        assert commands_of(snapshot, "p") == ["echo one", "echo two"]


def test_snapshot_validates_like_the_working_copy(project: Path) -> None:
    write_pipeline(project, base_pipeline("p"))
    git("add", "-A", cwd=project)
    git("commit", "-m", "p", cwd=project)
    with snapshot_project(project, head_commit(project)) as snapshot:
        assert validate_project(snapshot) == []


def test_snapshot_cleans_up(committed_project: Path) -> None:
    with snapshot_project(committed_project, head_commit(committed_project)) as snap:
        folder = snap.root
        assert folder.is_dir()
    assert not folder.exists()


def test_missing_commit_and_missing_lasagna_dir_raise(repo: Path) -> None:
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    git("add", "-A", cwd=repo)
    git("commit", "-m", "no lasagna", cwd=repo)
    with pytest.raises(DefinitionError):
        with snapshot_project(repo, head_commit(repo)):
            pass
    with pytest.raises(DefinitionError):
        with snapshot_project(repo, "0" * 40):
            pass


def test_only_lasagna_is_extracted(committed_project: Path) -> None:
    (committed_project / "src").mkdir()
    (committed_project / "src" / "x.py").write_text("x = 1\n", encoding="utf-8")
    (committed_project / "README.md").write_text("hi\n", encoding="utf-8")
    git("add", "-A", cwd=committed_project)
    git("commit", "-m", "more", cwd=committed_project)
    with snapshot_project(committed_project, head_commit(committed_project)) as snap:
        assert sorted(p.name for p in snap.root.iterdir()) == [".lasagna"]


def make_zip(*names: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in names:
            archive.writestr(name, "evil")
    return buffer.getvalue()


@pytest.mark.parametrize(
    "entry", ["../evil.txt", ".lasagna/../evil.txt", "/abs/evil.txt", "other/x.txt"]
)
def test_unsafe_archive_entry_is_rejected(tmp_path: Path, entry: str) -> None:
    target = tmp_path / "target"
    target.mkdir()
    with pytest.raises(DefinitionError):
        extract_lasagna(make_zip(".lasagna/ok.txt", entry), target)
    assert not (tmp_path / "evil.txt").exists()
    assert not (tmp_path / "abs").exists()


def test_extract_lasagna_writes_files_and_directories(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    data = make_zip(".lasagna/", ".lasagna/a/b.txt")
    extract_lasagna(data, target)
    assert (target / ".lasagna" / "a" / "b.txt").read_text() == "evil"


def test_snapshot_ignores_inherited_git_variables(
    committed_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    decoy = tmp_path / "decoy"
    decoy.mkdir()
    git("init", "-b", "main", cwd=decoy)
    monkeypatch.setenv("GIT_DIR", str(decoy / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(decoy))
    with snapshot_project(committed_project, head_commit(committed_project)) as snap:
        assert (snap.root / ".lasagna").is_dir()
