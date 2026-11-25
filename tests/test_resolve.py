import pytest

from lasagna_cli.expressions import ExpressionError, Ref, render
from lasagna_cli.resolve import Scope, UnresolvedError, resolve_text


def scope(**over) -> Scope:
    values = {
        "pipeline_inputs": {"topic": "cats"},
        "phase_outputs": {"a": {"spec-dir": "specs/x"}},
        "inputs": {"spec-dir": "specs/x"},
        "outputs": {"result": "ok"},
        "main_skill": ".lasagna/pipelines/p/harness/phases/b/SKILL.md",
        "output": ".lasagna/runs/p_01.p-a.1.out",
    }
    values.update(over)
    return Scope(**values)


def test_each_reference_kind() -> None:
    s = scope()
    assert resolve_text("${{ pipeline.inputs.topic }}", s) == "cats"
    assert resolve_text("${{ phases.a.outputs.spec-dir }}", s) == "specs/x"
    assert resolve_text("${{ inputs.spec-dir }}", s) == "specs/x"
    assert resolve_text("${{ outputs.result }}", s) == "ok"
    assert resolve_text("${{ harness.main_skill }}", s).endswith("SKILL.md")
    assert resolve_text("${{ lasagna.output }}", s) == ".lasagna/runs/p_01.p-a.1.out"


def test_several_expressions_in_one_string() -> None:
    text = "write ${{ pipeline.inputs.topic }} into ${{inputs.spec-dir}}/x.md"
    assert resolve_text(text, scope()) == "write cats into specs/x/x.md"


def test_text_without_expressions_is_unchanged() -> None:
    assert resolve_text("plain $text {{ nope }}", scope()) == "plain $text {{ nope }}"


@pytest.mark.parametrize(
    ("text", "over", "ref"),
    [
        (
            "${{ phases.a.outputs.x }}",
            {},
            Ref("phases", "a", "x"),
        ),
        (
            "${{ phases.zzz.outputs.x }}",
            {},
            Ref("phases", "zzz", "x"),
        ),
        ("${{ pipeline.inputs.none }}", {}, Ref("pipeline.inputs", None, "none")),
        ("${{ inputs.none }}", {}, Ref("inputs", None, "none")),
        ("${{ inputs.x }}", {"inputs": None}, Ref("inputs", None, "x")),
        ("${{ outputs.x }}", {"outputs": None}, Ref("outputs", None, "x")),
        ("${{ outputs.none }}", {}, Ref("outputs", None, "none")),
        (
            "${{ harness.main_skill }}",
            {"main_skill": None},
            Ref("harness.main_skill", None, None),
        ),
        (
            "${{ lasagna.output }}",
            {"output": None},
            Ref("lasagna.output", None, None),
        ),
    ],
)
def test_unresolved_references_raise_with_the_ref(text, over, ref) -> None:
    with pytest.raises(UnresolvedError) as info:
        resolve_text(text, scope(**over))
    assert info.value.ref == ref


def test_value_containing_an_expression_is_inserted_literally() -> None:
    s = scope(pipeline_inputs={"topic": "${{ inputs.spec-dir }}"})
    assert resolve_text("${{ pipeline.inputs.topic }}", s) == "${{ inputs.spec-dir }}"


def test_render_calls_lookup_in_order() -> None:
    calls: list[Ref] = []

    def lookup(ref: Ref) -> str:
        calls.append(ref)
        return f"<{ref.name}>"

    out = render("a ${{ inputs.x }} b ${{ outputs.y }} c", lookup)
    assert out == "a <x> b <y> c"
    assert calls == [Ref("inputs", None, "x"), Ref("outputs", None, "y")]


def test_render_raises_expression_error_like_find_refs() -> None:
    with pytest.raises(ExpressionError):
        render("${{ nonsense }}", lambda ref: "")
    with pytest.raises(ExpressionError):
        render("${{ inputs.x", lambda ref: "")


def test_unresolved_lasagna_output_names_the_expression() -> None:
    with pytest.raises(UnresolvedError, match="cannot resolve lasagna.output"):
        resolve_text("${{ lasagna.output }}", scope(output=None))
