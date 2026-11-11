"""Containment check of a path against a pipeline folder."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from lasagna.shell.project import containment_check

PD = ".lasagna/pipelines/demo"


def make_dir_link(link: Path, target: Path) -> None:
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        try:
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                check=True,
                capture_output=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            pytest.skip(f"cannot create a directory link: {exc}")


@pytest.fixture
def root(tmp_path: Path) -> Path:
    asset = tmp_path / ".lasagna" / "pipelines" / "demo" / "assets" / "x.md"
    asset.parent.mkdir(parents=True)
    asset.write_text("x")
    return tmp_path


# AC-V3-017
@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (".lasagna/pipelines/demo/assets/x.md", True),
        (".lasagna/pipelines/demo/assets/nuovo.md", True),
        (".lasagna/pipelines/demo", True),
        (".lasagna/pipelines/demo/../../x", False),
        ("x", False),
    ],
)
def test_containment_accepts_only_paths_inside_the_pipeline_folder(
    root: Path, path: str, expected: bool
) -> None:
    check = containment_check(root, PD)
    assert check(path) is expected


# AC-V3-017
def test_containment_rejects_a_link_that_leaves_the_pipeline_folder(root: Path) -> None:
    outside = root / "outside"
    outside.mkdir()
    (outside / "s.md").write_text("s")
    make_dir_link(root / PD / "assets" / "link", outside)
    check = containment_check(root, PD)
    assert check(".lasagna/pipelines/demo/assets/link/s.md") is False
    assert check(".lasagna/pipelines/demo/assets/link") is False
    assert check(".lasagna/pipelines/demo/assets/x.md") is True


# AC-V3-017
def test_containment_rejects_a_sibling_folder_with_the_same_text_prefix(
    root: Path,
) -> None:
    sibling = root / ".lasagna" / "pipelines" / "demo2" / "x.md"
    sibling.parent.mkdir(parents=True)
    sibling.write_text("x")
    check = containment_check(root, PD)
    assert check(".lasagna/pipelines/demo2/x.md") is False


# AC-V3-017
def test_containment_accepts_a_link_that_stays_inside_the_pipeline_folder(
    root: Path,
) -> None:
    real = root / PD / "assets" / "real"
    real.mkdir()
    (real / "f.md").write_text("f")
    make_dir_link(root / PD / "assets" / "inner", real)
    check = containment_check(root, PD)
    assert check(".lasagna/pipelines/demo/assets/inner/f.md") is True


# AC-V3-017
def test_containment_accepts_paths_when_the_pipeline_folder_is_itself_a_link(
    tmp_path: Path,
) -> None:
    r3 = tmp_path / "r3"
    (r3 / ".lasagna" / "pipelines").mkdir(parents=True)
    target = r3 / "elsewhere" / "demo"
    (target / "assets").mkdir(parents=True)
    (target / "assets" / "x.md").write_text("x")
    make_dir_link(r3 / PD, target)
    check = containment_check(r3, PD)
    assert check(".lasagna/pipelines/demo/assets/x.md") is True
