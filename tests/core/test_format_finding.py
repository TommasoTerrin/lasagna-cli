import pytest

from lasagna.core.models import Finding
from lasagna.core.validate import format_finding


@pytest.mark.parametrize(
    ("finding", "expected_start", "expected_full"),
    [
        (
            Finding(
                "V06",
                ".lasagna/pipelines/demo/pipeline.yaml",
                "edges[0].to",
                "edge to 'x' is not a node id; use a valid id.",
            ),
            "error V06 ",
            (
                "error V06 .lasagna/pipelines/demo/pipeline.yaml edges[0].to: "
                "edge to 'x' is not a node id; use a valid id."
            ),
        ),
        (
            Finding("V01", ".lasagna/pipelines.yaml", "", "empty YAML file: add it."),
            "error V01 ",
            "error V01 .lasagna/pipelines.yaml: empty YAML file: add it.",
        ),
        (
            Finding(
                "V05",
                ".lasagna/pipelines.yaml",
                "pipelines[0].path",
                "pipeline file is missing; create it.",
                level="warning",
            ),
            "warning V05 ",
            (
                "warning V05 .lasagna/pipelines.yaml pipelines[0].path: "
                "pipeline file is missing; create it."
            ),
        ),
    ],
    ids=["with-path", "empty-path", "warning-level"],
)
def test_format_finding_renders_level_rule_file_path_and_message(
    finding, expected_start, expected_full
):
    # no AC id (format_finding)
    output = format_finding(finding)
    assert output.startswith(expected_start)
    assert output == expected_full
