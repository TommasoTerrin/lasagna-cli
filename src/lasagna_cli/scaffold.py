"""`lasagna init`: write the .lasagna/ folder."""

import shutil
from pathlib import Path

from lasagna_cli.project import templates_dir


def init_project(root: Path) -> None:
    """Copy the bundled templates into `root/.lasagna`."""
    target = root / ".lasagna"
    if target.exists():
        raise FileExistsError(target)
    source = templates_dir()
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        name = ".gitignore" if relative.as_posix() == "gitignore" else None
        destination = target / (name or relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    (target / "pipelines").mkdir(exist_ok=True)
