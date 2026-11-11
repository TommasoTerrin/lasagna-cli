import pytest

from lasagna.core.render import PipelinePathError, resolve_pipeline_ref

PD = ".lasagna/pipelines/demo"


# AC-V3-017
@pytest.mark.parametrize(
    ("ref", "expected"),
    [
        ("$pipeline/assets/x.md", ".lasagna/pipelines/demo/assets/x.md"),
        ("$pipeline/x.md", ".lasagna/pipelines/demo/x.md"),
        ("$pipeline/assets/../x.md", ".lasagna/pipelines/demo/x.md"),
        ("$pipeline/./a.md", ".lasagna/pipelines/demo/a.md"),
        ("$pipeline/a//b.md", ".lasagna/pipelines/demo/a/b.md"),
        ("$pipeline/assets/", ".lasagna/pipelines/demo/assets"),
        ("$pipeline/", ".lasagna/pipelines/demo"),
        ("$pipeline/../demo/x.md", ".lasagna/pipelines/demo/x.md"),
    ],
)
def test_pipeline_reference_resolves_into_the_pipeline_folder_path(ref, expected):
    assert resolve_pipeline_ref(ref, PD) == expected


# AC-V3-017
@pytest.mark.parametrize(
    "ref",
    [
        "$pipeline",
        "$pipelines/x",
        "x/$pipeline/y",
        " $pipeline/x",
        "$PIPELINE/x",
        "$Pipeline/x",
        "docs/a.md",
        "",
    ],
)
def test_reference_without_pipeline_prefix_at_start_is_returned_unchanged(ref):
    assert resolve_pipeline_ref(ref, PD) == ref


# AC-V3-017
@pytest.mark.parametrize(
    "ref",
    [
        "$pipeline/..",
        "$pipeline/../x",
        "$pipeline/../../x",
        "$pipeline/assets/../../x",
        "$pipeline/assets/../..",
        "$pipeline/a/../../..",
        "$pipeline/../demo2/x.md",
    ],
)
def test_pipeline_reference_leaving_the_folder_is_rejected_with_its_ref(ref):
    with pytest.raises(PipelinePathError) as excinfo:
        resolve_pipeline_ref(ref, PD)
    assert excinfo.value.ref == ref
