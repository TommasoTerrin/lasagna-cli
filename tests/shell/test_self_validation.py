from pathlib import Path

from lasagna.core.validate import validate_project
from lasagna.shell.project import load_project


# §11.2.5 (AC-V3-005, anticipated)
def test_repository_own_lasagna_directory_loads_and_validates_clean():
    repo = Path(__file__).parents[2]

    data = load_project(repo)

    assert data.registry_loaded is True
    assert data.findings == ()
    assert set(data.pipelines) == {
        "pipelines/project-manager",
        "pipelines/implementation",
        "pipelines/quick-fix",
    }
    assert all(value is not None for value in data.pipelines.values())

    findings = validate_project(data.registry, data.pipelines)
    assert findings == [], f"self-validation findings: {findings}"


# §11.2.5
def test_builtin_pipelines_copied_into_a_project_load_and_validate_clean(tmp_path):
    repo = Path(__file__).parents[2]
    builtin = repo / "src" / "lasagna" / "builtin"
    ids = {p.parent.name for p in builtin.glob("*/pipeline.yaml")}
    assert ids == {"project-manager", "implementation", "quick-fix"}

    lines = ['lasagna: "3.0"', "pipelines:"]
    for pid in sorted(ids):
        target = tmp_path / ".lasagna" / "pipelines" / pid
        target.mkdir(parents=True)
        (target / "pipeline.yaml").write_bytes(
            (builtin / pid / "pipeline.yaml").read_bytes()
        )
        lines += [f"  - id: {pid}", f"    path: pipelines/{pid}"]
    (tmp_path / ".lasagna" / "pipelines.yaml").write_bytes(
        ("\n".join(lines) + "\n").encode("utf-8")
    )

    data = load_project(tmp_path)

    assert data.registry_loaded is True
    assert data.findings == ()
    assert set(data.pipelines) == {
        "pipelines/project-manager",
        "pipelines/implementation",
        "pipelines/quick-fix",
    }
    assert all(value is not None for value in data.pipelines.values())

    findings = validate_project(data.registry, data.pipelines)
    assert findings == [], f"builtin validation findings: {findings}"
