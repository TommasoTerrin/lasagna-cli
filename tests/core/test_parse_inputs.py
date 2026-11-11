import re

import pytest

from lasagna.core.render import InputError, parse_input_args

DECLARED = {"ticket", "note"}


def assert_format_f(message: str) -> None:
    problem, fix = message.rsplit("; ", 1)
    assert problem.strip()
    assert re.fullmatch(r"[a-z]\S*( \S+)+\.", fix), fix


# AC-V3-019
@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["ticket=a.md"], {"ticket": "a.md"}),
        (["ticket=a.md", "note=n"], {"ticket": "a.md", "note": "n"}),
        (["ticket=a=b"], {"ticket": "a=b"}),
        (["ticket="], {"ticket": ""}),
        (["ticket=a", "ticket=b"], {"ticket": "b"}),
        (["ticket= x "], {"ticket": " x "}),
        (["ticket={{ params.p }}"], {"ticket": "{{ params.p }}"}),
        ([], {}),
    ],
)
def test_input_args_split_on_first_equals_last_wins_no_strip(args, expected):
    assert parse_input_args(args, DECLARED) == expected


# AC-V3-019
@pytest.mark.parametrize(
    ("args", "declared", "quoted"),
    [
        (["ticket"], DECLARED, "'ticket'"),
        (["=v"], DECLARED, "'=v'"),
        (["ghost=1"], DECLARED, "'ghost'"),
        (["ticket=a", "ghost=1"], DECLARED, "'ghost'"),
        (["Ticket=a"], DECLARED, "'Ticket'"),
        (["ticket=a"], set(), "'ticket'"),
    ],
)
def test_invalid_input_args_raise_input_error_in_format_f_naming_the_culprit(
    args, declared, quoted
):
    with pytest.raises(InputError) as excinfo:
        parse_input_args(args, declared)
    message = str(excinfo.value)
    assert_format_f(message)
    assert quoted in message
