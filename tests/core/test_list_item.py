from lasagna.core.models import Pipeline
from lasagna.core.view import ListItem, list_item


def _pipeline(**extra):
    data = {
        "lasagna": "3.0",
        "id": "demo",
        "version": "1.2.3",
        "params": {"area": {"default": "core"}},
        "inputs": {"ticket": {"description": "T."}},
        "entry": "first",
        "nodes": [
            {"id": "first", "description": "First.", "started_by": "agent"},
            {"id": "second", "description": "Second.", "started_by": "human"},
        ],
        "edges": [{"type": "direct", "from": "first", "to": "second"}],
    }
    data.update(extra)
    return Pipeline.model_validate(data)


# AC-V3-020
def test_list_item_renders_one_line_description_and_picks_started_by_of_entry():
    desc = "Work on {{ params.area }}\n  for   {{ inputs.ticket }}.\n\nDone."
    pipeline = _pipeline(description=desc)

    default = list_item(pipeline, {}, True)
    assert default == ListItem(
        id="demo",
        version="1.2.3",
        description="Work on core for {{ inputs.ticket }}. Done.",
        started_by="agent",
        enabled=True,
    )

    overridden = list_item(pipeline, {"area": "web"}, False)
    assert overridden.description == "Work on web for {{ inputs.ticket }}. Done."
    assert overridden.enabled is False

    assert list_item(pipeline, {}, None).enabled is None

    second = list_item(_pipeline(entry="second", description="x"), {}, None)
    assert second.started_by == "human"

    assert list_item(_pipeline(), {}, True).description is None

    no_entry = _pipeline(description="x")
    data = no_entry.model_dump(by_alias=True)
    data.pop("entry")
    assert list_item(Pipeline.model_validate(data), {}, True).started_by is None

    assert list_item(_pipeline(entry="ghost", description="x"), {}, True).started_by is None

    padded = _pipeline(description="\n  A\t{{ params.area }}  \r\n b \n")
    assert list_item(padded, {"area": "web"}, None).description == "A web b"

    no_version = _pipeline(description="x").model_dump(by_alias=True)
    no_version.pop("version")
    assert list_item(Pipeline.model_validate(no_version), {}, None).version is None
