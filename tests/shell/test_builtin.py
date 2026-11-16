from importlib.resources import files

import pytest

from lasagna.core.models import Pipeline
from lasagna.shell.builtin import _ids_in, builtin_dir, builtin_ids, load_builtin


# AC-V3-020
def test_builtin_ids_match_packaged_pipeline_folders_and_load_by_id():
    root = files("lasagna") / "builtin"
    expected = sorted(
        d.name for d in root.iterdir() if d.is_dir() and (d / "pipeline.yaml").is_file()
    )

    assert expected == ["implementation", "project-manager", "quick-fix"]
    ids = builtin_ids()
    assert isinstance(ids, list)
    assert ids == expected

    for pipeline_id in expected:
        loaded = load_builtin(pipeline_id)
        assert isinstance(loaded, Pipeline)
        assert loaded.id == pipeline_id

    with pytest.raises(KeyError):
        load_builtin("nope")
    with pytest.raises(KeyError):
        builtin_dir("nope")


# AC-V3-020
def test_ids_in_returns_only_folders_with_pipeline_yaml_sorted(tmp_path):
    for name in ("zeta", "alpha"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "pipeline.yaml").write_text("x: 1\n", encoding="utf-8")
    (tmp_path / "no-yaml").mkdir()
    (tmp_path / "no-yaml" / "other.txt").write_text("x", encoding="utf-8")
    (tmp_path / "loose.yaml").write_text("x: 1\n", encoding="utf-8")

    assert _ids_in(tmp_path) == ["alpha", "zeta"]
