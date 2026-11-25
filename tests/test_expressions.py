import pytest

from lasagna_cli.expressions import ExpressionError, Ref, find_refs, has_expression


def test_phase_output_and_phase_input_refs_in_order():
    text = "${{ phases.fetch-issue.outputs.issue-file }}/x ${{inputs.a}}"
    assert find_refs(text) == [
        Ref("phases", "fetch-issue", "issue-file"),
        Ref("inputs", None, "a"),
    ]


def test_main_skill_ref():
    assert find_refs("${{ harness.main_skill }}") == [
        Ref("harness.main_skill", None, None)
    ]


def test_pipeline_input_ref():
    assert find_refs("${{ pipeline.inputs.issue }}") == [
        Ref("pipeline.inputs", None, "issue")
    ]


def test_current_phase_output_ref():
    assert find_refs("${{ outputs.spec-dir }}/spec.md") == [
        Ref("outputs", None, "spec-dir")
    ]


def test_plain_text_has_no_refs():
    assert find_refs("plain $X text ${Y} {{z}}") == []


def test_has_expression():
    assert has_expression("a ${{ inputs.a }}")
    assert has_expression("${{")
    assert not has_expression("$X ${Y}")


@pytest.mark.parametrize(
    "text",
    [
        "${{ foo.bar }}",
        "${{ inputs.Bad }}",
        "${{ inputs.a",
        "${{ }}",
        "${{ inputs.a inputs.b }}",
        "${{ phases.a.inputs.b }}",
        "ok ${{ inputs.a }} then ${{ nope",
    ],
)
def test_malformed_expressions_raise(text):
    with pytest.raises(ExpressionError):
        find_refs(text)


def test_lasagna_output_ref():
    assert find_refs("write to ${{ lasagna.output }}") == [
        Ref("lasagna.output", None, None)
    ]
