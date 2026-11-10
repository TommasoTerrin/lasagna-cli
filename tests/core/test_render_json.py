import json

from lasagna.core.models import Finding
from lasagna.core.validate import render_json


# AC-V3-013
def test_no_findings_render_as_empty_error_and_warning_lists():
    assert render_json([]) == '{\n  "errors": [],\n  "warnings": []\n}\n'


# AC-V3-013
def test_one_error_and_one_warning_render_as_the_exact_documented_text():
    findings = [
        Finding("V06", "f.yaml", "edges[0].to", "m1"),
        Finding("V22", "g.yaml", "nodes[1]", "m2", level="warning"),
    ]
    expected = (
        "{\n"
        '  "errors": [\n'
        "    {\n"
        '      "rule": "V06",\n'
        '      "file": "f.yaml",\n'
        '      "path": "edges[0].to",\n'
        '      "message": "m1"\n'
        "    }\n"
        "  ],\n"
        '  "warnings": [\n'
        "    {\n"
        '      "rule": "V22",\n'
        '      "file": "g.yaml",\n'
        '      "path": "nodes[1]",\n'
        '      "message": "m2"\n'
        "    }\n"
        "  ]\n"
        "}\n"
    )
    assert render_json(findings) == expected


# AC-V3-013
def test_findings_are_classified_by_level_not_rule_id_and_keep_input_order():
    findings = [
        Finding("V22", "a.yaml", "p1", "m1"),
        Finding("V06", "b.yaml", "p2", "m2", level="warning"),
        Finding("V06", "c.yaml", "p3", "m3"),
    ]
    data = json.loads(render_json(findings))
    assert data == {
        "errors": [
            {"rule": "V22", "file": "a.yaml", "path": "p1", "message": "m1"},
            {"rule": "V06", "file": "c.yaml", "path": "p3", "message": "m3"},
        ],
        "warnings": [
            {"rule": "V06", "file": "b.yaml", "path": "p2", "message": "m2"},
        ],
    }


# AC-V3-013
def test_non_ascii_text_is_not_escaped_and_an_empty_path_stays_the_empty_string():
    text = render_json([Finding("V01", "f.yaml", "", "è; fix it.")])
    assert "è" in text
    assert "\\u00e8" not in text
    assert json.loads(text)["errors"] == [
        {"rule": "V01", "file": "f.yaml", "path": "", "message": "è; fix it."}
    ]
