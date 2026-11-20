"""Read the pipeline definition from a commit, never from the working copy.

Only the `.lasagna/` folder of the commit is extracted into a temporary folder,
where the usual loader and validators run on it unchanged.
"""

import io
import shutil
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from lasagna_cli.gitops import GitError, run_git_bytes
from lasagna_cli.loader import load_project
from lasagna_cli.model import Project

LASAGNA_DIR = ".lasagna"


class DefinitionError(Exception):
    """The definition cannot be read from the commit."""


def _safe_parts(name: str) -> tuple[str, ...]:
    path = PurePosixPath(name)
    parts = path.parts
    if (
        "\\" in name
        or path.is_absolute()
        or ".." in parts
        or (parts and ":" in parts[0])
        or not parts
        or parts[0] != LASAGNA_DIR
    ):
        raise DefinitionError(f"unsafe entry in the definition archive: '{name}'")
    return parts


def extract_lasagna(zip_bytes: bytes, target: Path) -> None:
    """Write the `.lasagna/` entries of a zip under `target`; refuse any other.

    Every entry is checked before anything is written.
    """
    try:
        archive = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile:
        raise DefinitionError("the definition archive is not a valid zip") from None
    with archive:
        entries = [(info, _safe_parts(info.filename)) for info in archive.infolist()]
        for info, parts in entries:
            destination = target.joinpath(*parts)
            if info.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(info))


@contextmanager
def snapshot_project(root: Path, commit: str) -> Iterator[Project]:
    """Yield the project as committed at `commit`, in a temporary folder."""
    try:
        data = run_git_bytes(root, "archive", "--format=zip", commit, "--", LASAGNA_DIR)
    except GitError as error:
        raise DefinitionError(
            f"cannot read {LASAGNA_DIR}/ from commit {commit}: {error}"
        ) from None
    folder = Path(tempfile.mkdtemp(prefix="lasagna-def-"))
    try:
        extract_lasagna(data, folder)
        yield load_project(folder)
    finally:
        shutil.rmtree(folder, ignore_errors=True)
