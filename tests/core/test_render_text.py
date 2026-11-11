import pytest

from lasagna.core.render import find_placeholders, render_text


# AC-V3-015
@pytest.mark.parametrize(
    ("template", "expected"),
    [
        ("{{ params.x }}", "X"),
        ("{{params.x}}", "X"),
        ("{{   params.x   }}", "X"),
        ("{{\tparams.x\t}}", "X"),
        ("{{ inputs.y }}", "Y"),
        ("{{inputs.y}}", "Y"),
        ("a {{ params.x }} b {{ inputs.y }} c", "a X b Y c"),
        ("{{ params.x }}{{ params.x }}", "XX"),
    ],
)
def test_placeholders_with_any_spaces_or_tabs_are_replaced_by_their_value(template, expected):
    assert render_text(template, {"x": "X"}, {"y": "Y"}) == expected


# AC-V3-015
@pytest.mark.parametrize(
    "text",
    [
        "{{ foo }}",
        "${{ github.event.x }}",
        "{% if x %}",
        "{{ params }}",
        "{{ params. x }}",
        "{{ params.x.y }}",
        "{{ Params.x }}",
        "{{ INPUTS.y }}",
        "{{ params.x",
        "{ { params.x } }",
        "{{ params.x }",
        "{{ params.x\n}}",
        "{{ params.x } }",
        "{{}}",
        "plain text",
    ],
)
def test_texts_that_are_not_exact_placeholders_stay_unchanged(text):
    assert render_text(text, {"x": "X", "x.y": "XY"}, {"y": "Y"}) == text


# AC-V3-015
@pytest.mark.parametrize(
    ("text", "params", "inputs", "expected"),
    [
        ("{{ params.zzz }}", {"x": "X"}, {"y": "Y"}, "{{ params.zzz }}"),
        ("{{ inputs.zzz }}", {"x": "X"}, {"y": "Y"}, "{{ inputs.zzz }}"),
        ("{{ params.y }}", {"x": "X"}, {"y": "Y"}, "{{ params.y }}"),
        ("{{ inputs.x }}", {"x": "X"}, {"y": "Y"}, "{{ inputs.x }}"),
        ("{{ params.x }}", {}, {}, "{{ params.x }}"),
        ("{{ inputs.y }}", {}, {}, "{{ inputs.y }}"),
        ("{{ params.x }} {{ inputs.zzz }}", {"x": "X"}, {"y": "Y"}, "X {{ inputs.zzz }}"),
    ],
)
def test_a_name_not_provided_stays_as_written(text, params, inputs, expected):
    assert render_text(text, params, inputs) == expected


# AC-V3-015
def test_a_dollar_sign_before_a_placeholder_stays_and_the_placeholder_is_replaced():
    assert render_text("${{ params.x }}", {"x": "X"}, {}) == "$X"


# AC-V3-015
@pytest.mark.parametrize(
    "value",
    ["a\\1b\\g<0>c$&d", ""],
)
def test_a_value_is_inserted_literally_without_regex_replacement_semantics(value):
    assert render_text("{{ params.x }}", {"x": value}, {}) == value


# AC-V3-015
@pytest.mark.parametrize(
    ("template", "params", "inputs", "expected"),
    [
        ("{{ params.a }}", {"a": "{{ params.b }}", "b": "B"}, {}, "{{ params.b }}"),
        ("{{ inputs.y }}", {}, {"y": "{{ params.a }}"}, "{{ params.a }}"),
        ("{{ params.a }}", {"a": "{{ inputs.y }}"}, {"y": "Y"}, "{{ inputs.y }}"),
    ],
)
def test_an_inserted_value_is_not_scanned_again_for_placeholders(template, params, inputs, expected):
    assert render_text(template, params, inputs) == expected


# AC-V3-015
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "{{ params.a }} x {{inputs.b}} {{ foo }} ${{ params.a }} {{ params.q.r }}",
            [("params", "a"), ("inputs", "b"), ("params", "a")],
        ),
        ("", []),
        ("{{ foo }}", []),
    ],
)
def test_placeholders_are_listed_in_order_of_appearance_with_repetitions_kept(text, expected):
    assert find_placeholders(text) == expected


# AC-V3-015
def test_placeholder_with_an_unknown_kind_is_left_alone_even_if_the_key_exists_in_both_maps():
    text = "{{ foo.x }} {{foo.x}}"
    assert render_text(text, {"x": "X"}, {"x": "Y"}) == text
