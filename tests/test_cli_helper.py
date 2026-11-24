from conftest import invoke, plain


def test_plain_strips_ansi_codes() -> None:
    assert plain("\x1b[1m--bind\x1b[0m \x1b[33;1mPHASE\x1b[0m") == "--bind PHASE"


def test_invoke_returns_the_output_without_ansi_codes(monkeypatch) -> None:
    monkeypatch.setenv("FORCE_COLOR", "1")
    result = invoke("start", "--help")
    assert result.exit_code == 0
    assert "\x1b[" not in result.output
    assert "--bind" in result.output
