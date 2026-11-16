from lasagna.core.view import ListItem, list_json

PROJECT_JSON = """\
{
  "pipelines": [
    {
      "id": "alpha",
      "version": "1.0.0",
      "description": "Descrizione | con barra è è.",
      "started_by": "human",
      "enabled": true
    },
    {
      "id": "beta",
      "version": "2.0",
      "description": "Altro.",
      "started_by": "agent",
      "enabled": false
    },
    {
      "id": "bare",
      "version": null,
      "description": null,
      "started_by": null
    }
  ]
}
"""

EMPTY_JSON = """\
{
  "pipelines": []
}
"""


# AC-V3-020
def test_list_json_renders_exact_shape_with_null_values_and_absent_enabled():
    items = [
        ListItem("alpha", "1.0.0", "Descrizione | con barra è è.", "human", True),
        ListItem("beta", "2.0", "Altro.", "agent", False),
        ListItem("bare", None, None, None, None),
    ]
    assert list_json(items) == PROJECT_JSON

    assert list_json([]) == EMPTY_JSON
