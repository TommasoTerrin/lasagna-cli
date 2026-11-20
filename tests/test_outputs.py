from pathlib import Path

from lasagna_cli.model import Output
from lasagna_cli.outputs import (
    collect_outputs,
    new_output_file,
    parse_output_file,
)
from lasagna_cli.resolve import Scope, resolve_text


def parse(tmp_path: Path, data: bytes) -> dict[str, str]:
    path = tmp_path / "out"
    path.write_bytes(data)
    return parse_output_file(path)


def test_parsing_rules(tmp_path: Path) -> None:
    assert parse(tmp_path, b"a=1\n\n  \nb=2\n") == {"a": "1", "b": "2"}
    assert parse(tmp_path, b"a=1\r\nb=2\r\n") == {"a": "1", "b": "2"}
    assert parse(tmp_path, b"a=b=c\n") == {"a": "b=c"}
    assert parse(tmp_path, b"a=1\na=2\n") == {"a": "2"}
    assert parse(tmp_path, b"garbage\na=1\nmore garbage\n") == {"a": "1"}
    assert parse(tmp_path, b"") == {}
    assert parse(tmp_path, "name=caffè\n".encode()) == {"name": "caffè"}
    assert parse(tmp_path, b"empty=\n") == {"empty": ""}


def test_missing_file_gives_no_outputs(tmp_path: Path) -> None:
    assert parse_output_file(tmp_path / "nope") == {}


def test_new_output_file_is_unique_and_creates_the_folder(tmp_path: Path) -> None:
    first = new_output_file(tmp_path, "p_01")
    second = new_output_file(tmp_path, "p_01")
    assert first != second
    assert first.is_file() and second.is_file()
    assert first.parent == tmp_path / ".lasagna" / "runs"
    assert first.read_text() == ""


def resolver():
    def resolve(template: str, values: dict[str, str]) -> str:
        scope = Scope(pipeline_inputs={}, phase_outputs={}, outputs=values)
        return resolve_text(template, scope)

    return resolve


def collect(tmp_path: Path, declared, written):
    return collect_outputs(declared, written, tmp_path, resolver())


def test_value_only(tmp_path: Path) -> None:
    result = collect(tmp_path, {"x": Output("value", None)}, {"x": "1", "y": "2"})
    assert result.outputs == {"x": "1"}
    assert result.missing == ()
    assert result.errors == ()


def test_file_only(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("x", encoding="utf-8")
    result = collect(tmp_path, {"doc": Output("file", "docs/a.md")}, {})
    assert result.outputs == {"doc": "docs/a.md"}
    assert result.missing == ()


def test_file_path_uses_a_value_output(tmp_path: Path) -> None:
    (tmp_path / "specs" / "todo-app").mkdir(parents=True)
    (tmp_path / "specs" / "todo-app" / "spec.md").write_text("x", encoding="utf-8")
    declared = {
        "spec-dir": Output("value", None),
        "spec": Output("file", "${{ outputs.spec-dir }}/spec.md"),
    }
    result = collect(tmp_path, declared, {"spec-dir": "specs/todo-app"})
    assert result.outputs == {
        "spec-dir": "specs/todo-app",
        "spec": "specs/todo-app/spec.md",
    }
    assert result.missing == ()


def test_missing_file(tmp_path: Path) -> None:
    result = collect(tmp_path, {"doc": Output("file", "nope.md")}, {})
    assert result.outputs == {}
    assert result.missing == ("doc",)
    assert "doc" in result.errors[0] and "nope.md" in result.errors[0]


def test_missing_value(tmp_path: Path) -> None:
    result = collect(tmp_path, {"x": Output("value", None)}, {})
    assert result.missing == ("x",)
    assert "x" in result.errors[0]


def test_file_depending_on_a_missing_value_is_missing(tmp_path: Path) -> None:
    declared = {
        "dir": Output("value", None),
        "spec": Output("file", "${{ outputs.dir }}/spec.md"),
    }
    result = collect(tmp_path, declared, {})
    assert result.missing == ("dir", "spec")


def test_undeclared_key_is_ignored(tmp_path: Path) -> None:
    result = collect(tmp_path, {}, {"decision": "start", "next": "b", "z": "1"})
    assert result.outputs == {}
    assert result.missing == ()


def test_path_that_escapes_the_worktree(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    (tmp_path / "secret.txt").write_text("x", encoding="utf-8")
    absolute = (tmp_path / "secret.txt").as_posix()
    declared = {
        "up": Output("file", "../secret.txt"),
        "abs": Output("file", absolute),
    }
    result = collect_outputs(declared, {}, work, resolver())
    assert result.outputs == {}
    assert result.missing == ("up", "abs")
    assert all("outside" in e for e in result.errors)
