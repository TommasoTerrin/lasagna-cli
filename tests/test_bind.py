from pathlib import Path

import pytest
from conftest import write_pipeline

from lasagna_cli.bind import BindError, check_bind, parse_bind
from lasagna_cli.loader import load_project

LEAN = """\
type: agent
name: lean
params:
  prompt:
    required: true
commands:
  run: echo "$LASAGNA_PARAM_PROMPT"
"""

STRICT = """\
type: agent
name: strict
params:
  prompt:
    required: true
  style:
    required: true
commands:
  run: echo "$LASAGNA_PARAM_PROMPT"
"""

OTHER_MACHINE = """\
type: machine
name: other
"""


def test_parse_bind_splits_on_the_first_equals() -> None:
    assert parse_bind(["a=claude", "b=x=y"]) == {"a": "claude", "b": "x=y"}
    assert parse_bind([]) == {}


@pytest.mark.parametrize("item", ["a", "=claude", "a=", ""])
def test_parse_bind_rejects_a_malformed_item(item: str) -> None:
    with pytest.raises(BindError):
        parse_bind([item])


def test_parse_bind_rejects_a_repeated_phase() -> None:
    with pytest.raises(BindError, match="twice"):
        parse_bind(["a=claude", "a=opencode"])


@pytest.fixture
def loaded(project: Path):
    actors = project / ".lasagna" / "actors"
    (actors / "lean.yaml").write_text(LEAN, encoding="utf-8", newline="\n")
    (actors / "strict.yaml").write_text(STRICT, encoding="utf-8", newline="\n")
    (actors / "other.yaml").write_text(OTHER_MACHINE, encoding="utf-8", newline="\n")
    write_pipeline(
        project,
        {
            "name": "p",
            "phases": [
                {"id": "m", "actor": "machine", "with": {"command": "true"}},
                {
                    "id": "ai",
                    "needs": ["m"],
                    "actor": "claude",
                    "with": {"prompt": "hi", "model": "large"},
                },
            ],
        },
    )
    project_model = load_project(project)
    return project_model, project_model.pipelines["p"]


def test_a_valid_swap_has_no_errors(loaded) -> None:
    project, pipeline = loaded
    assert check_bind(project, pipeline, {"ai": "opencode", "m": "other"}) == []


def test_an_unknown_phase(loaded) -> None:
    project, pipeline = loaded
    errors = check_bind(project, pipeline, {"nope": "opencode"})
    assert len(errors) == 1 and "unknown phase 'nope'" in errors[0]


def test_an_unknown_actor(loaded) -> None:
    project, pipeline = loaded
    errors = check_bind(project, pipeline, {"ai": "ghost"})
    assert len(errors) == 1 and "unknown actor 'ghost'" in errors[0]


def test_an_actor_of_another_type(loaded) -> None:
    project, pipeline = loaded
    errors = check_bind(project, pipeline, {"m": "claude"})
    assert len(errors) == 1 and "agent" in errors[0] and "machine" in errors[0]


def test_a_param_the_new_actor_does_not_accept(loaded) -> None:
    project, pipeline = loaded
    errors = check_bind(project, pipeline, {"ai": "lean"})
    assert len(errors) == 1 and "model" in errors[0]


def test_a_required_param_nobody_provides(loaded) -> None:
    project, pipeline = loaded
    errors = check_bind(project, pipeline, {"ai": "strict"})
    assert any("style" in error for error in errors)
