import subprocess
import sys
from pathlib import Path

import pytest

from lasagna.core.schema import render_schema


# AC-V3-014
def test_gen_schema_command_writes_exactly_the_two_schema_files_with_exact_bytes(tmp_path):
    out = tmp_path / "out"
    out.mkdir()

    result = subprocess.run(
        [sys.executable, "-m", "lasagna.shell.gen_schema", str(out)],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert sorted(p.name for p in out.iterdir()) == ["pipeline.schema.json", "registry.schema.json"]
    for kind in ("registry", "pipeline"):
        assert (out / f"{kind}.schema.json").read_bytes() == render_schema(kind).encode("utf-8")


# AC-V3-014
@pytest.mark.parametrize("kind", ["registry", "pipeline"])
def test_committed_schema_file_is_byte_identical_to_the_rendered_schema(kind):
    repo = Path(__file__).parents[2]
    path = repo / "schema" / f"{kind}.schema.json"

    assert path.is_file(), f"missing committed schema file: {path}"
    assert path.read_bytes() == render_schema(kind).encode("utf-8")
