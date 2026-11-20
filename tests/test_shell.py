import pytest

from lasagna_cli.shell import ShellNotFoundError, resolve_bash, shell_env, to_bash_path


def files(*paths):
    lowered = {p.lower() for p in paths}
    return lambda p: p.lower() in lowered


WIN_ENV = {
    "ProgramFiles": r"C:\Program Files",
    "ProgramFiles(x86)": r"C:\Program Files (x86)",
    "LOCALAPPDATA": r"C:\Users\u\AppData\Local",
    "PATH": "",
}


def win(env=None, *existing, setting="auto"):
    return resolve_bash(
        setting,
        platform="win32",
        environ={**WIN_ENV, **(env or {})},
        is_file=files(*existing),
    )


def test_windows_standard_location():
    assert (
        win(None, r"C:\Program Files\Git\bin\bash.exe")
        == r"C:\Program Files\Git\bin\bash.exe"
    )


def test_windows_program_files_before_localappdata():
    assert (
        win(
            None,
            r"C:\Users\u\AppData\Local\Programs\Git\bin\bash.exe",
            r"C:\Program Files\Git\bin\bash.exe",
        )
        == r"C:\Program Files\Git\bin\bash.exe"
    )


def test_windows_localappdata_user_install():
    p = r"C:\Users\u\AppData\Local\Programs\Git\bin\bash.exe"
    assert win(None, p) == p


def test_windows_derived_from_git_on_path():
    assert (
        win(
            {"PATH": r"D:\Tools\Git\cmd"},
            r"D:\Tools\Git\cmd\git.exe",
            r"D:\Tools\Git\bin\bash.exe",
        )
        == r"D:\Tools\Git\bin\bash.exe"
    )


def test_windows_prefers_bin_over_usr_bin_on_path():
    assert (
        win(
            {"PATH": r"D:\Git\usr\bin"},
            r"D:\Git\usr\bin\bash.exe",
            r"D:\Git\bin\bash.exe",
        )
        == r"D:\Git\bin\bash.exe"
    )


def test_windows_rejects_wsl_launchers():
    path = r"C:\Windows\System32;C:\Users\u\AppData\Local\Microsoft\WindowsApps"
    with pytest.raises(ShellNotFoundError) as err:
        win(
            {"PATH": path},
            r"C:\Windows\System32\bash.exe",
            r"C:\Users\u\AppData\Local\Microsoft\WindowsApps\bash.exe",
        )
    msg = str(err.value)
    assert "Git for Windows" in msg and "https://git-scm.com/download/win" in msg
    assert "shell:" in msg and ".lasagna/config/lasagna.yaml" in msg


@pytest.mark.parametrize(
    "setting", [r"C:\Windows\System32\bash.exe", r"bash.exe", r"D:\missing\bash.exe"]
)
def test_windows_explicit_setting_rejected(setting):
    with pytest.raises(ShellNotFoundError):
        win(None, r"C:\Windows\System32\bash.exe", setting=setting)


def test_windows_explicit_setting_accepted():
    assert (
        win(None, r"D:\Git\bin\bash.exe", setting=r"D:\Git\bin\bash.exe")
        == r"D:\Git\bin\bash.exe"
    )


@pytest.mark.parametrize("platform", ["linux", "darwin"])
def test_posix_uses_path(platform):
    got = resolve_bash(
        "auto",
        platform=platform,
        environ={"PATH": "/opt/x:/usr/bin"},
        is_file=files("/usr/bin/bash"),
    )
    assert got == "/usr/bin/bash"


def test_posix_missing_bash():
    with pytest.raises(ShellNotFoundError, match="shell:"):
        resolve_bash(
            "auto", platform="linux", environ={"PATH": "/usr/bin"}, is_file=files()
        )


def test_to_bash_path_and_shell_env():
    assert to_bash_path(r"C:\Users\a b\x") == "C:/Users/a b/x"
    assert to_bash_path("/usr/bin") == "/usr/bin"
    assert shell_env("win32") == {"MSYS_NO_PATHCONV": "1", "MSYS2_ARG_CONV_EXCL": "*"}
    assert shell_env("linux") == {}
