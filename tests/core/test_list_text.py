from lasagna.core.view import ListItem, list_text

PROJECT_LIST = """\
# Pipelines

- alpha 1.0.0 started_by=human: Descrizione | con barra è è.
- beta 2.0 started_by=agent (disabled): Altro.
- gamma - started_by=-
- delta 3 started_by=agent:\x20
- eps 4 started_by=- (disabled)
- zeta - started_by=human (disabled):\x20
"""

BUILTIN_LIST = """\
# Built-in pipelines

- quick-fix 0.1 started_by=agent: Fix.
- solo - started_by=-
"""

EMPTY_PROJECT = "# Pipelines\n\n(none)\n"
EMPTY_BUILTIN = "# Built-in pipelines\n\n(none)\n"


# AC-V3-020
def test_list_text_renders_each_item_line_title_and_empty_list_exactly():
    items = [
        ListItem("alpha", "1.0.0", "Descrizione | con barra è è.", "human", True),
        ListItem("beta", "2.0", "Altro.", "agent", False),
        ListItem("gamma", None, None, None, True),
        ListItem("delta", "3", "", "agent", True),
        ListItem("eps", "4", None, None, False),
        ListItem("zeta", None, "", "human", False),
    ]
    assert list_text(items, False) == PROJECT_LIST

    builtin = [
        ListItem("quick-fix", "0.1", "Fix.", "agent", None),
        ListItem("solo", None, None, None, None),
    ]
    assert list_text(builtin, True) == BUILTIN_LIST

    assert list_text([], False) == EMPTY_PROJECT
    assert list_text([], True) == EMPTY_BUILTIN
