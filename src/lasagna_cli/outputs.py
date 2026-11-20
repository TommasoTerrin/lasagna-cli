"""The `$LASAGNA_OUTPUT` file and the check of a phase's declared outputs."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

from lasagna_cli.model import Output
from lasagna_cli.resolve import UnresolvedError


def new_output_file(worktree: Path, run_id: str) -> Path:
    """Create a new empty `$LASAGNA_OUTPUT` file under `<worktree>/.lasagna/runs/`."""
    folder = worktree / ".lasagna" / "runs"
    folder.mkdir(parents=True, exist_ok=True)
    counter = 1
    while True:
        path = folder / f"{run_id}.{counter}.out"
        try:
            path.open("x").close()
        except FileExistsError:
            counter += 1
            continue
        return path


def parse_output_file(path: Path) -> dict[str, str]:
    """`name=value` lines of an output file; the last occurrence of a key wins."""
    try:
        text = path.read_bytes().decode("utf-8", errors="replace")
    except FileNotFoundError:
        return {}
    values: dict[str, str] = {}
    for line in text.split("\n"):
        line = line.removesuffix("\r")
        if not line.strip() or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


@dataclass(frozen=True)
class OutputResult:
    outputs: dict[str, str]
    missing: tuple[str, ...]
    errors: tuple[str, ...]


def _relative_inside(worktree: Path, raw: str) -> str | None:
    """The path as a normalised relative POSIX path, or None if it leaves the tree."""
    posix = PurePosixPath(raw.replace("\\", "/"))
    if (
        posix.is_absolute()
        or PureWindowsPath(raw).drive
        or ".." in posix.parts
        or not posix.parts
    ):
        return None
    target = (worktree / posix).resolve()
    if not target.is_relative_to(worktree.resolve()):
        return None
    return posix.as_posix()


def collect_outputs(
    declared: Mapping[str, Output],
    written: Mapping[str, str],
    worktree: Path,
    resolve_path: Callable[[str, dict[str, str]], str],
) -> OutputResult:
    """Read the declared outputs: values first, then the files that must exist."""
    outputs: dict[str, str] = {}
    missing: list[str] = []
    errors: list[str] = []
    for name, spec in declared.items():
        if spec.type != "value":
            continue
        if name in written:
            outputs[name] = written[name]
        else:
            missing.append(name)
            errors.append(f"output '{name}' was not written to $LASAGNA_OUTPUT")
    values = dict(outputs)
    for name, spec in declared.items():
        if spec.type != "file":
            continue
        template = spec.path or ""
        try:
            raw = resolve_path(template, values)
        except UnresolvedError as error:
            missing.append(name)
            errors.append(f"output '{name}': path '{template}': {error}")
            continue
        relative = _relative_inside(worktree, raw)
        if relative is None:
            missing.append(name)
            errors.append(f"output '{name}': path '{raw}' is outside the worktree")
        elif not (worktree / relative).is_file():
            missing.append(name)
            errors.append(f"output '{name}': file '{relative}' does not exist")
        else:
            outputs[name] = relative
    return OutputResult(outputs, tuple(missing), tuple(errors))
