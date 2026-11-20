"""Find the bash that runs user commands, and prepare paths and env for it.

Every user command runs with ``bash -c`` on every OS. On Windows that bash is
Git for Windows' bash, never the WSL launchers in ``System32`` or
``WindowsApps``.
"""

import os
import sys
from collections.abc import Callable, Iterator, Mapping
from pathlib import PurePath, PurePosixPath, PureWindowsPath

CONFIG_FILE = ".lasagna/config/lasagna.yaml"
GIT_FOR_WINDOWS_URL = "https://git-scm.com/download/win"


class ShellNotFoundError(Exception):
    """No usable bash was found, or the configured one is not usable."""


def _not_found(platform: str, reason: str) -> ShellNotFoundError:
    if platform == "win32":
        hint = (
            f"Install Git for Windows ({GIT_FOR_WINDOWS_URL}) or set 'shell:' "
            f"in {CONFIG_FILE} to the absolute path of Git for Windows' "
            "bin\\bash.exe."
        )
    else:
        hint = (
            f"Install bash or set 'shell:' in {CONFIG_FILE} to the absolute "
            "path of a bash executable."
        )
    return ShellNotFoundError(f"{reason}. {hint}")


def _env_get(environ: Mapping[str, str], name: str, platform: str) -> str:
    if platform != "win32":
        return environ.get(name, "")
    wanted = name.lower()
    for key, value in environ.items():
        if key.lower() == wanted:
            return value
    return ""


def _is_wsl_launcher(path: PureWindowsPath) -> bool:
    parts = [p.lower() for p in path.parts]
    if "windowsapps" in parts:
        return True
    return any(
        parts[i] == "windows" and parts[i + 1] == "system32"
        for i in range(len(parts) - 1)
    )


def _path_dirs(raw: str, sep: str) -> Iterator[str]:
    for entry in raw.split(sep):
        entry = entry.strip().strip('"')
        if entry:
            yield entry


def _windows_candidates(
    environ: Mapping[str, str], is_file: Callable[[str], bool]
) -> Iterator[PureWindowsPath]:
    for var, extra in (
        ("ProgramFiles", ()),
        ("ProgramFiles(x86)", ()),
        ("LOCALAPPDATA", ("Programs",)),
    ):
        base = _env_get(environ, var, "win32")
        if base:
            yield PureWindowsPath(base, *extra, "Git", "bin", "bash.exe")

    dirs = [
        PureWindowsPath(d) for d in _path_dirs(_env_get(environ, "PATH", "win32"), ";")
    ]

    for d in dirs:
        if d.name.lower() in ("cmd", "bin") and is_file(str(d / "git.exe")):
            yield d.parent / "bin" / "bash.exe"

    for d in dirs:
        candidate = d / "bash.exe"
        if not is_file(str(candidate)):
            continue
        if d.name.lower() == "bin" and d.parent.name.lower() == "usr":
            preferred = d.parent.parent / "bin" / "bash.exe"
            if is_file(str(preferred)):
                yield preferred
                continue
        yield candidate


def resolve_bash(
    setting: str,
    *,
    platform: str,
    environ: Mapping[str, str],
    is_file: Callable[[str], bool],
) -> str:
    """Return the bash executable to use, or raise ShellNotFoundError."""
    windows = platform == "win32"

    if setting != "auto":
        path: PurePath = PureWindowsPath(setting) if windows else PurePosixPath(setting)
        if not path.is_absolute():
            raise _not_found(platform, f"shell '{setting}' is not an absolute path")
        if windows and _is_wsl_launcher(PureWindowsPath(setting)):
            raise _not_found(platform, f"shell '{setting}' would start WSL")
        if not is_file(setting):
            raise _not_found(platform, f"shell '{setting}' does not exist")
        return setting

    if windows:
        for candidate in _windows_candidates(environ, is_file):
            if not _is_wsl_launcher(candidate) and is_file(str(candidate)):
                return str(candidate)
        raise _not_found(platform, "Git for Windows' bash was not found")

    for d in _path_dirs(_env_get(environ, "PATH", platform), ":"):
        candidate = str(PurePosixPath(d) / "bash")
        if is_file(candidate):
            return candidate
    raise _not_found(platform, "bash was not found on PATH")


def host_bash(setting: str = "auto") -> str:
    """Resolve bash for the current host."""
    return resolve_bash(
        setting, platform=sys.platform, environ=os.environ, is_file=os.path.isfile
    )


def to_bash_path(path: str | os.PathLike[str]) -> str:
    """Return the path with forward slashes, as bash expects it."""
    return os.fspath(path).replace("\\", "/")


def shell_env(platform: str) -> dict[str, str]:
    """Environment variables Lasagna adds to every command on this platform."""
    if platform == "win32":
        return {"MSYS_NO_PATHCONV": "1", "MSYS2_ARG_CONV_EXCL": "*"}
    return {}
