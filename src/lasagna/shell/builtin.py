"""Reads the pipelines included in the package."""

from importlib.resources import as_file, files
from pathlib import Path

from ruamel.yaml import YAML

from lasagna.core.models import Pipeline


def _root() -> Path:
    with as_file(files("lasagna") / "builtin") as root:
        return Path(root)


def _ids_in(root: Path) -> list[str]:
    """Return the sorted names of the folders in root that hold a pipeline.yaml."""
    return sorted(d.name for d in root.iterdir() if (d / "pipeline.yaml").is_file())


def builtin_ids() -> list[str]:
    """Return the ids of the included pipelines, sorted."""
    return _ids_in(_root())


def builtin_dir(pipeline_id: str) -> Path:
    """Return the folder of an included pipeline; KeyError if unknown."""
    if pipeline_id not in builtin_ids():
        raise KeyError(pipeline_id)
    return _root() / pipeline_id


def load_builtin(pipeline_id: str) -> Pipeline:
    """Load an included pipeline; KeyError if unknown."""
    text = (builtin_dir(pipeline_id) / "pipeline.yaml").read_text(encoding="utf-8")
    return Pipeline.model_validate(YAML(typ="safe").load(text))
