"""`lasagna init`: write the .lasagna/ folder."""

import shutil
from pathlib import Path

from lasagna_cli.project import templates_dir

# Dotfiles are stored without the dot so packaging tools do not skip them.
DOTFILES = {"gitignore": ".gitignore", "gitattributes": ".gitattributes"}


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
        destination = target / DOTFILES.get(relative.as_posix(), relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    (target / "pipelines").mkdir(exist_ok=True)
