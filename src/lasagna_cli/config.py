"""Loading and checking `config/lasagna.yaml`, which has no schema."""

from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

import yaml

from lasagna_cli.issues import Issue


@dataclass(frozen=True)
class Config:
    shell: str = "auto"
    max_depth: int = 3
    worktrees_dir: str = ".lasagna/worktrees"
    branch_prefix: str = "lasagna/"


def load_config(path: Path, label: str) -> tuple[Config, list[Issue]]:
    """Read the config file; invalid values fall back to the defaults."""
    if not path.is_file():
        return Config(), [Issue(label, "", "missing config/lasagna.yaml")]
    try:
        data = yaml.safe_load(path.read_text("utf-8"))
    except yaml.YAMLError as error:
        reason = " ".join(str(error).split())
        return Config(), [Issue(label, "", f"invalid YAML: {reason}")]
    if data is None:
        return Config(), []
    issues: list[Issue] = []

    def add(field: str, message: str) -> None:
        issues.append(Issue(label, field, message))

    if not isinstance(data, dict):
        return Config(), [Issue(label, "", "must be a mapping")]

    defaults = Config()
    values = {
        "shell": defaults.shell,
        "max_depth": defaults.max_depth,
        "worktrees_dir": defaults.worktrees_dir,
        "branch_prefix": defaults.branch_prefix,
    }

    def section(key: str, allowed: set[str]) -> dict:
        raw = data.get(key)
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            add(key, "must be a mapping")
            return {}
        for sub in raw:
            if sub not in allowed:
                add(f"{key}.{sub}", "unknown key")
        return raw

    for key in data:
        if key not in {"version", "shell", "limits", "worktrees"}:
            add(str(key), "unknown key")
    if "version" in data and (
        data["version"] != 1 or isinstance(data["version"], bool)
    ):
        add("version", "must be 1")
    if "shell" in data:
        shell = data["shell"]
        if shell == "auto" or (isinstance(shell, str) and Path(shell).is_absolute()):
            values["shell"] = shell
        else:
            add("shell", 'must be "auto" or an absolute path')

    limits = section("limits", {"max_depth"})
    if "max_depth" in limits:
        depth = limits["max_depth"]
        if isinstance(depth, int) and not isinstance(depth, bool) and depth >= 0:
            values["max_depth"] = depth
        else:
            add("limits.max_depth", "must be an integer >= 0")

    worktrees = section("worktrees", {"dir", "branch_prefix"})
    if "dir" in worktrees:
        directory = worktrees["dir"]
        if isinstance(directory, str) and directory and not _is_rooted(directory):
            values["worktrees_dir"] = directory
        else:
            add("worktrees.dir", "must be a non-empty relative path")
    if "branch_prefix" in worktrees:
        prefix = worktrees["branch_prefix"]
        if isinstance(prefix, str) and prefix:
            values["branch_prefix"] = prefix
        else:
            add("worktrees.branch_prefix", "must be a non-empty string")

    return Config(**values), issues


def _is_rooted(value: str) -> bool:
    return (
        PurePosixPath(value).is_absolute()
        or PureWindowsPath(value).is_absolute()
        or PureWindowsPath(value).root != ""
    )
