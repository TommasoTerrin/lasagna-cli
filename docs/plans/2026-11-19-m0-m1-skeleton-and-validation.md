# M0 + M1: Skeleton, Shell Resolution, Model and Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An installable `lasagna` CLI with `--version`, cross-platform bash resolution, and `lasagna init` / `lasagna validate` covering the primitive schemas and every rule of PROTOCOL §10 that does not depend on starting a run.

**Architecture:** Pure modules (`shell`, `expressions`, `schemas`, the `validation` rules) take plain data and return values or `Issue` lists; thin effectful modules (`project`, `loader`, `scaffold`, `cli`) touch the filesystem, git and the terminal. The loader turns `.lasagna/` into frozen dataclasses; files that fail their schema become issues and are left out of the model, so the semantic rules only see well-typed data.

**Tech Stack:** Python 3.11+, uv (build backend `uv_build`), Typer, PyYAML, jsonschema + referencing, pytest, ruff, GitHub Actions.

**Spec:** `harness/PROTOCOL.md` (local only, Italian, normative), `src/lasagna_cli/templates/lasagna/config/primitives/*.schema.yaml`, `CLAUDE.md`.

## Global Constraints

- Python `>=3.11`; distribution `lasagna-cli`, module `lasagna_cli`, command `lasagna`; version `0.1.0`; MIT license.
- Runtime dependencies are exactly `typer`, `pyyaml`, `jsonschema`, `referencing`. Ask before adding any other one.
- Everything committed is in English. Never `git add harness/` (already in `.git/info/exclude`).
- User commands run with `bash -c` on every OS. On Windows, never `C:\Windows\System32\bash.exe` and never a `bash.exe` under `WindowsApps`.
- `pathlib` everywhere; paths shown to users and stored in issues are POSIX, relative to the repo root; text files are LF.
- Git only through the `git` CLI via `subprocess`.
- Tests never call Claude, OpenCode or the network. Git tests use real repos in `tmp_path`. No hand-written `\` paths in tests except as data for the Windows resolver.
- Exit codes (PROTOCOL §7): 0 ok, 1 run failed, 2 usage or validation error, 3 waiting for a human, 130 Ctrl+C.
- Every CLI command has a one-line docstring and every option and argument a `help` text, so `lasagna --help` and `lasagna <command> --help` guide the user. Typer's default Rich formatting is enough; banners and visual polish come after the MVP.
- A task is done only when `uv run pytest` is green and `uv run ruff check . && uv run ruff format --check .` is clean.
- Branches: M0 on `m0-skeleton` from `develop`; M1 on `m1-model-validation` from `m0-skeleton`. Stop after Task 3 for review, and after Task 12.
- Commit messages: imperative English, ending with the `Co-Authored-By` line from the session.

## File Structure

```
pyproject.toml, uv.lock, LICENSE, .gitignore
.github/workflows/ci.yml
src/lasagna_cli/
  __init__.py          __version__ via importlib.metadata
  cli.py               Typer app: --version, init, validate; exit codes
  shell.py             bash resolution (pure + host wrapper), to_bash_path, shell_env
  issues.py            Issue dataclass
  schemas.py           bundled schemas, registry, schema_errors, primitive copy warnings
  project.py           find_repo_root via git common dir
  scaffold.py          init_project
  config.py            load_config for config/lasagna.yaml
  model.py             frozen dataclasses (Actor, Pipeline, Phase, ...)
  loader.py            load_project: YAML -> schema -> model + issues
  expressions.py       find_refs / has_expression for ${{ }}
  validation/
    __init__.py        validate_project
    references.py      names, references, graph, nesting, harness files
    actors.py          with/params/interactive/harness, sub-pipeline io, deciders
    expr_rules.py      where expressions may appear and what they may reference
tests/
  conftest.py          git helper, repo + project fixtures, write_pipeline helper
  test_cli_version.py, test_shell.py, test_shell_bash.py, test_schemas.py,
  test_project_init.py, test_config.py, test_loader.py, test_expressions.py,
  test_rules_references.py, test_rules_actors.py, test_rules_expressions.py,
  test_validate_cli.py
```

---

## M0 — Skeleton

### Task 1: Project bootstrap, `--version`, CI

**Files:**
- Create: `pyproject.toml`, `LICENSE`, `.gitignore`, `.github/workflows/ci.yml`, `src/lasagna_cli/__init__.py`, `src/lasagna_cli/cli.py`, `tests/test_cli_version.py`
- Commit as is first: `CLAUDE.md`, `.gitattributes`, `src/lasagna_cli/templates/`, `tests/fixtures/`, `examples/`

**Interfaces:**
- Produces: `lasagna_cli.__version__: str`; `lasagna_cli.cli.app: typer.Typer`; `lasagna_cli.cli.main() -> None`; constants in `cli.py`: `EXIT_OK = 0`, `EXIT_FAILED = 1`, `EXIT_USAGE = 2`, `EXIT_WAITING = 3`, `EXIT_INTERRUPTED = 130`.

- [ ] **Step 1: Branch and commit the spec assets**

```bash
git switch -c m0-skeleton
git add CLAUDE.md .gitattributes src/lasagna_cli/templates tests/fixtures examples
git commit -m "Add protocol templates, schemas, fixtures and acceptance pipeline"
```

- [ ] **Step 2: Write `pyproject.toml`, `.gitignore`, `LICENSE`**

`pyproject.toml`: `[project]` name `lasagna-cli`, version `0.1.0`, `requires-python = ">=3.11"`, license `MIT`, dependencies `typer>=0.12`, `pyyaml>=6.0`, `jsonschema>=4.18`, `referencing>=0.30`; `[project.scripts] lasagna = "lasagna_cli.cli:main"`; `[build-system] requires = ["uv_build>=0.11,<0.12"]`, `build-backend = "uv_build"`; `[dependency-groups] dev = ["pytest>=8", "ruff>=0.6"]`; `[tool.ruff] target-version = "py311"`, `line-length = 88`; `[tool.ruff.lint] select = ["E", "F", "I", "UP", "B"]`; `[tool.pytest.ini_options] testpaths = ["tests"]`, `addopts = "-ra"`.
`.gitignore`: the standard Python entries (`__pycache__/`, `*.py[cod]`, `.venv/`, `dist/`, `build/`, `*.egg-info/`, `.pytest_cache/`, `.ruff_cache/`, `.coverage`) plus `.claude/`.
`LICENSE`: MIT, `Copyright (c) 2026 Tommaso Terrin`.

- [ ] **Step 3: Write the failing test** in `tests/test_cli_version.py`

```python
from typer.testing import CliRunner
from lasagna_cli.cli import app

def test_version_prints_name_and_version():
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output == "lasagna 0.1.0\n"

def test_help_lists_commands():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    for name in app_command_names():
        assert name in result.output
```

`app_command_names()` is a local helper returning `[c.name or c.callback.__name__ for c in app.registered_commands]`, so the test grows with every command added later.

- [ ] **Step 4: Run it to make sure it fails**

Run: `uv sync && uv run pytest tests/test_cli_version.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lasagna_cli.cli'`

- [ ] **Step 5: Implement `__init__.py` and `cli.py`**

`__version__ = importlib.metadata.version("lasagna-cli")`. In `cli.py`: `app = typer.Typer(no_args_is_help=True, add_completion=False)`, an eager `--version` option in `@app.callback()` that prints `lasagna {__version__}` and exits 0, and `main()` calling `app()`.

- [ ] **Step 6: Run the tests and lint**

Run: `uv run pytest -v && uv run ruff check . && uv run ruff format --check . && uv run lasagna --version`
Expected: 1 passed, ruff clean, prints `lasagna 0.1.0`

- [ ] **Step 7: Write `.github/workflows/ci.yml`**

Runs on `push` and `pull_request`, with a matrix over `ubuntu-latest`, `macos-latest` and `windows-latest` and `fail-fast: false`. Steps: `actions/checkout@v4`, `astral-sh/setup-uv@v6`, `uv sync --locked --python 3.11`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest`. Every `run:` step uses `shell: bash`.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock LICENSE .gitignore .github src/lasagna_cli/__init__.py src/lasagna_cli/cli.py tests/test_cli_version.py docs/plans
git commit -m "Add project skeleton with lasagna --version and CI on three OSes"
```

### Task 2: Bash resolution (pure)

**Files:**
- Create: `src/lasagna_cli/shell.py`, `tests/test_shell.py`

**Interfaces:**
- Produces:
  - `class ShellNotFoundError(Exception)`
  - `resolve_bash(setting: str, *, platform: str, environ: Mapping[str, str], is_file: Callable[[str], bool]) -> str`
  - `host_bash(setting: str = "auto") -> str`, which calls `resolve_bash` with `sys.platform`, `os.environ` and `os.path.isfile`
  - `to_bash_path(path: str | os.PathLike) -> str`
  - `shell_env(platform: str) -> dict[str, str]`

Rules (PROTOCOL §4):
- **macOS and Linux:** `bash` from `PATH`, split on `:`.
- **Windows (`platform == "win32"`):** use `PureWindowsPath` and `;`, and read environment variable names case-insensitively. Search in this order:
  1. `Git\bin\bash.exe` under `ProgramFiles`, then `ProgramFiles(x86)`, then `LOCALAPPDATA\Programs`.
  2. For each `git.exe` on `PATH` whose folder is named `cmd` or `bin` (case-insensitive): `<that folder's parent>\bin\bash.exe`.
  3. `bash.exe` on `PATH`. A hit at `<X>\usr\bin\bash.exe` is replaced by `<X>\bin\bash.exe` when that file exists.
- **Rejected on Windows:** any candidate under `\Windows\System32\`, and any candidate with a `WindowsApps` path component (case-insensitive). This applies to an explicit setting too.
- **Explicit setting** (not `"auto"`): it must be absolute for the platform's path flavour and `is_file` must accept it; otherwise raise `ShellNotFoundError`.
- **Error message:** every `ShellNotFoundError` message contains `Git for Windows` (on win32), `https://git-scm.com/download/win` (on win32), and `shell:` together with `.lasagna/config/lasagna.yaml`.
- **`to_bash_path`:** replaces `\` with `/` (for example `C:\a b\c` → `C:/a b/c`).
- **`shell_env`:** returns `{"MSYS_NO_PATHCONV": "1", "MSYS2_ARG_CONV_EXCL": "*"}` on win32, and `{}` elsewhere.

- [ ] **Step 1: Write the failing tests** in `tests/test_shell.py` (runs on every OS)

```python
import pytest
from lasagna_cli.shell import ShellNotFoundError, resolve_bash, to_bash_path, shell_env

def files(*paths):
    lowered = {p.lower() for p in paths}
    return lambda p: p.lower() in lowered

WIN_ENV = {"ProgramFiles": r"C:\Program Files", "ProgramFiles(x86)": r"C:\Program Files (x86)",
           "LOCALAPPDATA": r"C:\Users\u\AppData\Local", "PATH": ""}

def win(env=None, *existing, setting="auto"):
    return resolve_bash(setting, platform="win32", environ={**WIN_ENV, **(env or {})}, is_file=files(*existing))

def test_windows_standard_location():
    assert win(None, r"C:\Program Files\Git\bin\bash.exe") == r"C:\Program Files\Git\bin\bash.exe"

def test_windows_program_files_before_localappdata():
    assert win(None, r"C:\Users\u\AppData\Local\Programs\Git\bin\bash.exe",
               r"C:\Program Files\Git\bin\bash.exe") == r"C:\Program Files\Git\bin\bash.exe"

def test_windows_localappdata_user_install():
    p = r"C:\Users\u\AppData\Local\Programs\Git\bin\bash.exe"
    assert win(None, p) == p

def test_windows_derived_from_git_on_path():
    assert win({"PATH": r"D:\Tools\Git\cmd"}, r"D:\Tools\Git\cmd\git.exe",
               r"D:\Tools\Git\bin\bash.exe") == r"D:\Tools\Git\bin\bash.exe"

def test_windows_prefers_bin_over_usr_bin_on_path():
    assert win({"PATH": r"D:\Git\usr\bin"}, r"D:\Git\usr\bin\bash.exe",
               r"D:\Git\bin\bash.exe") == r"D:\Git\bin\bash.exe"

def test_windows_rejects_wsl_launchers():
    path = r"C:\Windows\System32;C:\Users\u\AppData\Local\Microsoft\WindowsApps"
    with pytest.raises(ShellNotFoundError) as err:
        win({"PATH": path}, r"C:\Windows\System32\bash.exe",
            r"C:\Users\u\AppData\Local\Microsoft\WindowsApps\bash.exe")
    msg = str(err.value)
    assert "Git for Windows" in msg and "https://git-scm.com/download/win" in msg
    assert "shell:" in msg and ".lasagna/config/lasagna.yaml" in msg

@pytest.mark.parametrize("setting", [r"C:\Windows\System32\bash.exe", r"bash.exe", r"D:\missing\bash.exe"])
def test_windows_explicit_setting_rejected(setting):
    with pytest.raises(ShellNotFoundError):
        win(None, r"C:\Windows\System32\bash.exe", setting=setting)

def test_windows_explicit_setting_accepted():
    assert win(None, r"D:\Git\bin\bash.exe", setting=r"D:\Git\bin\bash.exe") == r"D:\Git\bin\bash.exe"

@pytest.mark.parametrize("platform", ["linux", "darwin"])
def test_posix_uses_path(platform):
    got = resolve_bash("auto", platform=platform, environ={"PATH": "/opt/x:/usr/bin"}, is_file=files("/usr/bin/bash"))
    assert got == "/usr/bin/bash"

def test_posix_missing_bash():
    with pytest.raises(ShellNotFoundError, match="shell:"):
        resolve_bash("auto", platform="linux", environ={"PATH": "/usr/bin"}, is_file=files())

def test_to_bash_path_and_shell_env():
    assert to_bash_path(r"C:\Users\a b\x") == "C:/Users/a b/x"
    assert to_bash_path("/usr/bin") == "/usr/bin"
    assert shell_env("win32") == {"MSYS_NO_PATHCONV": "1", "MSYS2_ARG_CONV_EXCL": "*"}
    assert shell_env("linux") == {}
```

- [ ] **Step 2: Run to make sure they fail**

Run: `uv run pytest tests/test_shell.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lasagna_cli.shell'`

- [ ] **Step 3: Implement `shell.py`** with the signatures and rules above. Return the candidate string exactly as it was built, so the tests compare original casing.

- [ ] **Step 4: Run the tests and lint**

Run: `uv run pytest -v && uv run ruff check . && uv run ruff format --check .`
Expected: all pass, ruff clean

- [ ] **Step 5: Commit**

```bash
git add src/lasagna_cli/shell.py tests/test_shell.py
git commit -m "Resolve bash per platform, rejecting WSL launchers on Windows"
```

### Task 3: Real bash round trip (quoting, injection, MSYS)

**Files:**
- Create: `tests/test_shell_bash.py`

**Interfaces:**
- Consumes: `host_bash()`, `to_bash_path()`, `shell_env()` from Task 2.

Every test runs `subprocess.run([host_bash(), "-c", command], cwd=tmp_path, env={**os.environ, **shell_env(sys.platform), **extra}, capture_output=True)`, through a local helper `run_bash(command, cwd, **extra) -> CompletedProcess[bytes]`.

- [ ] **Step 1: Write the tests**

```python
def spec_to_code_check() -> str:
    data = yaml.safe_load(Path("examples/pipelines/spec-to-code/spec-to-code.yaml").read_text("utf-8"))
    return data["phases"][1]["loop"]["until"]["check"]

def test_spec_to_code_check_reaches_bash_intact(tmp_path):
    (tmp_path / "specs").mkdir()
    spec = tmp_path / "specs" / "spec.md"
    spec.write_bytes(b"## Checklist\n- [x] done\n  - [ ] todo\n")
    assert run_bash(spec_to_code_check(), tmp_path, LASAGNA_INPUT_SPEC_DIR="specs").returncode == 1
    spec.write_bytes(b"## Checklist\n- [x] done\n")
    assert run_bash(spec_to_code_check(), tmp_path, LASAGNA_INPUT_SPEC_DIR="specs").returncode == 0

def test_double_quotes_in_command(tmp_path):
    assert run_bash('printf %s "a \\"b\\" c"', tmp_path).stdout == b'a "b" c'

INJECTION = '"; touch pwned1; echo "$(touch pwned2) `touch pwned3` \' && touch pwned4'

def test_env_value_is_never_executed(tmp_path):
    result = run_bash('printf %s "$X" > out.txt', tmp_path, X=INJECTION)
    assert result.returncode == 0
    assert (tmp_path / "out.txt").read_text("utf-8") == INJECTION
    assert not list(tmp_path.glob("pwned*"))

def test_unicode_env_value_round_trip(tmp_path):
    run_bash('printf %s "$X" > out.txt', tmp_path, X="caffè ✓")
    assert (tmp_path / "out.txt").read_bytes().decode("utf-8") == "caffè ✓"

def test_slash_argument_reaches_native_program_unchanged(tmp_path):
    cmd = '"$PY" -c "import sys; print(sys.argv[1])" "$X"'
    out = run_bash(cmd, tmp_path, PY=to_bash_path(sys.executable), X="/foo/bar")
    assert out.stdout.decode().strip() == "/foo/bar"
```

- [ ] **Step 2: Run them**

Run: `uv run pytest tests/test_shell_bash.py -v`
Expected: PASS on this Windows machine. Remove `shell_env` from the helper once to check that `test_slash_argument_reaches_native_program_unchanged` fails without the MSYS variables, then restore it. If any other test fails, the cause is a real Windows quoting or encoding problem: stop and report instead of working around it.

- [ ] **Step 3: Lint, then commit**

```bash
uv run ruff check . && uv run ruff format --check .
git add tests/test_shell_bash.py
git commit -m "Test bash -c round trip, env-only values and MSYS path conversion"
```

- [ ] **Step 4: Push the branch and check CI on all three OSes, then stop for the M0 review.**

---

## M1 — Model and validation

Start with `git switch -c m1-model-validation` from `m0-skeleton`, after approval.

### Task 4: `Issue` and the bundled schemas

**Files:**
- Create: `src/lasagna_cli/issues.py`, `src/lasagna_cli/schemas.py`, `tests/test_schemas.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Issue: file: str; field: str; message: str; severity: Literal["error", "warning"] = "error"`
    - `file`: POSIX path relative to the repo root.
    - `field`: dotted path such as `phases[1].with.command`, or `""` for the whole file.
    - `__str__` gives `"{severity}: {file}: {field}: {message}"`, without the `{field}: ` part when `field` is empty.
  - `PRIMITIVE_KINDS = ("human", "machine", "agent", "pipeline", "phase", "run")`
  - `bundled_primitives_dir() -> Path`: `importlib.resources.files("lasagna_cli") / "templates/lasagna/config/primitives"`
  - `schema_errors(kind: str, instance: object) -> list[tuple[str, str]]`: `(field path, message)` pairs, sorted by path. It uses a cached `Draft202012Validator` over a `referencing.Registry` holding all the bundled files (each keyed by its `$id`).
  - Format checker: a `FormatChecker(formats=())` with a single `date-time` check, which uses `datetime.fromisoformat` (accepting `Z`) and requires a timezone.
  - Path conversion: `["phases", 1, "with"]` → `phases[1].with`.

- [ ] **Step 1: Write the failing tests**

```python
FIXTURES = Path("tests/fixtures")

@pytest.mark.parametrize("path", sorted(FIXTURES.glob("pipelines/*/*.yaml")) + [Path("examples/pipelines/spec-to-code/spec-to-code.yaml")])
def test_fixture_pipelines_match_schema(path):
    assert schema_errors("pipeline", yaml.safe_load(path.read_text("utf-8"))) == []

def test_template_actors_match_schema():
    for path in (bundled_primitives_dir().parent.parent / "actors").glob("*.yaml"):
        data = yaml.safe_load(path.read_text("utf-8"))
        assert schema_errors(data["type"], data) == []

def test_fixture_run_events_match_schema():
    for path in FIXTURES.glob("runs/*.jsonl"):
        for line in path.read_text("utf-8").splitlines():
            assert schema_errors("run", json.loads(line)) == []

def test_invalid_timestamp_is_rejected():
    event = {"v": 1, "seq": 1, "ts": "yesterday", "run": "r", "event": "run_resumed", "by": "human"}
    assert [p for p, _ in schema_errors("run", event)] == ["ts"]

def test_error_paths_are_dotted_with_indexes():
    pipeline = {"name": "p", "phases": [{"id": "a", "actor": "machine"}, {"id": "b", "actor": "x", "interactive": True, "timeout": "1m"}]}
    assert "phases[1].timeout" in [p for p, _ in schema_errors("pipeline", pipeline)]

def test_issue_str():
    assert str(Issue("a.yaml", "phases[0].id", "bad")) == "error: a.yaml: phases[0].id: bad"
    assert str(Issue("a.yaml", "", "bad", "warning")) == "warning: a.yaml: bad"
```

- [ ] **Step 2: Run to make sure they fail**

Run: `uv run pytest tests/test_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `issues.py` and `schemas.py`** with the interfaces above.

- [ ] **Step 4: Run the tests and lint.** Expected: all pass, ruff clean.

- [ ] **Step 5: Commit** `git commit -m "Validate instances against the bundled primitive schemas"`

### Task 5: Repo root discovery and `lasagna init`

**Files:**
- Create: `src/lasagna_cli/project.py`, `src/lasagna_cli/scaffold.py`, `tests/conftest.py`, `tests/test_project_init.py`
- Modify: `src/lasagna_cli/cli.py` (add `init`)

**Interfaces:**
- Produces:
  - `class NotAGitRepoError(Exception)`
  - `find_repo_root(cwd: Path) -> Path`: runs `git rev-parse --path-format=absolute --git-common-dir` with `cwd`; returns the parent if the result is named `.git`; otherwise, or if git fails, raises `NotAGitRepoError("not inside a git repository")`.
  - `templates_dir() -> Path`: `importlib.resources.files("lasagna_cli") / "templates/lasagna"`.
  - `init_project(root: Path) -> None`: raises `FileExistsError` if `root/.lasagna` exists. Otherwise copies every template file byte for byte (`shutil.copyfile`), writes `gitignore` as `.gitignore`, and creates an empty `pipelines/` directory.
  - CLI `lasagna init`: prints `Created .lasagna/` and exits 0. On an existing `.lasagna/` it prints `.lasagna/ already exists` and exits 2. Outside git it prints `not inside a git repository` and exits 2. Errors go to stderr.
  - `tests/conftest.py`:
    - `git(*args: str, cwd: Path) -> str`: check=True, returns stripped stdout.
    - fixture `repo(tmp_path) -> Path`: `git init -b main`, plus a local `user.name` and `user.email`.
    - fixture `project(repo) -> Path`: `init_project(repo)`, returns `repo`.
    - `write_pipeline(root: Path, data: dict, *, main_skills: Iterable[str] = (), skills: Iterable[str] = (), mcp: Iterable[str] = ()) -> Path`: writes `.lasagna/pipelines/<name>/<name>.yaml` with `yaml.safe_dump(sort_keys=False)` and the named harness files (`harness/phases/<id>/SKILL.md`, `harness/skills/<n>/SKILL.md`, `harness/mcp/<n>.json`).

- [ ] **Step 1: Write the failing tests**

```python
def test_find_repo_root_from_subdir_and_linked_worktree(repo, tmp_path):
    (repo / "sub").mkdir()
    assert find_repo_root(repo / "sub") == repo.resolve()
    git("commit", "--allow-empty", "-m", "init", cwd=repo)
    wt = tmp_path / "wt"
    git("worktree", "add", str(wt), cwd=repo)
    assert find_repo_root(wt) == repo.resolve()

def test_find_repo_root_outside_git(tmp_path):
    with pytest.raises(NotAGitRepoError):
        find_repo_root(tmp_path)

def test_init_copies_templates_with_dotgitignore(repo):
    init_project(repo)
    src = templates_dir()
    expected = {p.relative_to(src).as_posix().replace("gitignore", ".gitignore") for p in src.rglob("*") if p.is_file()}
    got = {p.relative_to(repo / ".lasagna").as_posix() for p in (repo / ".lasagna").rglob("*") if p.is_file()}
    assert got == expected
    assert (repo / ".lasagna" / "pipelines").is_dir()
    assert (repo / ".lasagna/.gitignore").read_bytes() == b"runs/\nworktrees/\n"
    assert all(b"\r\n" not in (repo / ".lasagna" / f).read_bytes() for f in got)

def test_init_cli_twice(repo, monkeypatch):
    monkeypatch.chdir(repo)
    assert CliRunner().invoke(app, ["init"]).exit_code == 0
    result = CliRunner().invoke(app, ["init"])
    assert result.exit_code == 2 and ".lasagna/ already exists" in result.output

def test_init_cli_outside_git(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["init"])
    assert result.exit_code == 2 and "not inside a git repository" in result.output
```

(Use `CliRunner(mix_stderr=False)` and check `result.stderr` if the installed Typer version separates the two streams.)

- [ ] **Step 2: Run to make sure they fail.** Expected: `ModuleNotFoundError`.
- [ ] **Step 3: Implement `project.py`, `scaffold.py` and the `init` command.**
- [ ] **Step 4: Run the tests and lint, and check the wheel ships the templates**

Run: `uv run pytest -v && uv build --wheel && uv run python -m zipfile -l dist/lasagna_cli-0.1.0-py3-none-any.whl`
Expected: tests pass; the listing contains `lasagna_cli/templates/lasagna/gitignore` and `lasagna_cli/templates/lasagna/config/primitives/run.schema.yaml`.

- [ ] **Step 5: Commit** `git commit -m "Add lasagna init and repo root discovery through the git common dir"`

### Task 6: `config/lasagna.yaml`

**Files:**
- Create: `src/lasagna_cli/config.py`, `tests/test_config.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Config: shell: str = "auto"; max_depth: int = 3; worktrees_dir: str = ".lasagna/worktrees"; branch_prefix: str = "lasagna/"`
  - `load_config(path: Path, label: str) -> tuple[Config, list[Issue]]`, where `label` is the issue `file`.

Rules (all optional keys fall back to the defaults):
- `version` must be the integer `1`.
- `shell` is `"auto"` or an absolute path (`Path(v).is_absolute()` on the host).
- `limits.max_depth` is an int ≥ 0 (not a bool).
- `worktrees.dir` is a non-empty relative path.
- `worktrees.branch_prefix` is a non-empty string.
- Unknown keys, at top level or nested, are errors: `unknown key`.
- A missing file gives the issue `("", "missing config/lasagna.yaml")` plus the defaults. Invalid YAML gives the issue `("", "invalid YAML: <reason>")`.

- [ ] **Step 1: Write the failing tests**
  - `test_template_config_loads_without_issues`: the template file gives `Config()` and `[]`.
  - `test_invalid_values`: one parametrized case per rule. Each asserts exactly one issue, with these fields and messages:

    | Field | Message |
    |---|---|
    | `version` | `must be 1` |
    | `shell` | `must be "auto" or an absolute path` |
    | `limits.max_depth` | `must be an integer >= 0` |
    | `worktrees.dir` | `must be a non-empty relative path` |
    | `worktrees.branch_prefix` | `must be a non-empty string` |
    | `limits.foo` | `unknown key` |

  - `test_missing_file`: gives defaults and one issue.
- [ ] **Step 2: Run to make sure they fail.**
- [ ] **Step 3: Implement `config.py`.**
- [ ] **Step 4: Run the tests and lint.**
- [ ] **Step 5: Commit** `git commit -m "Load and check config/lasagna.yaml"`

### Task 7: Model and loader

**Files:**
- Create: `src/lasagna_cli/model.py`, `src/lasagna_cli/loader.py`, `tests/test_loader.py`

**Interfaces:**
- Consumes: `Issue`, `schema_errors`, `load_config`, `Config`.
- Produces (all `@dataclass(frozen=True)`):
  - `Param(required: bool, default: str | None)`
  - `AgentCommands(check: tuple[str, ...], inject: str | None, run: str, run_interactive: str | None, cleanup: str | None)`
  - `Actor(name: str, type: Literal["human", "machine", "agent"], file: str, params: dict[str, Param], models: dict[str, str], commands: AgentCommands | None)`: `params` and `models` are empty and `commands` is `None` for non-agents.
  - `Decider(by: str, check: str | None, prompt: str | None, instructions: str | None)`
  - `Output(type: Literal["file", "value"], path: str | None)`
  - `Loop(max_iterations: int, until: Decider)`
  - `Phase(index: int, id: str, needs: tuple[str, ...], actor: str | None, pipeline: str | None, interactive: bool, with_: dict[str, str], main_skill: bool, skills: tuple[str, ...], mcp: tuple[str, ...], inputs: dict[str, str], outputs: dict[str, Output], trigger: Decider | None, route: Decider | None, loop: Loop | None, timeout: str | None)`
  - `PipelineInput(required: bool, default: str | None)`
  - `Pipeline(name: str, dir: str, file: str, trigger_by: tuple[str, ...], inputs: dict[str, PipelineInput], outputs: dict[str, str], skills: tuple[str, ...], mcp: tuple[str, ...], phases: tuple[Phase, ...])`:
    - `dir` is POSIX relative to the repo root, e.g. `.lasagna/pipelines/bug-fix`.
    - `trigger_by` defaults to `("human",)`.
    - Methods: `phase(id: str) -> Phase`, `children(id: str) -> list[str]` (in file order), `ancestors(id: str) -> set[str]` (transitive `needs`).
  - `@dataclass class Project(root: Path, config: Config, actors: dict[str, Actor], pipelines: dict[str, Pipeline], issues: list[Issue])`
  - `load_project(root: Path) -> Project`: reads `root/.lasagna`; issues are collected, never raised.

Loader rules:
- **Actors** come from `actors/*.yaml`, in sorted order.
- **Unknown actor type:** field `type`, message `unknown actor type '<t>' (extensions are not active in the MVP)`.
- **Duplicate actor name:** issue on the later file, field `name`, message `duplicate actor name '<n>' (also in <other file>)`.
- **Pipelines:** each directory in `pipelines/` must contain `<dir>/<dir>.yaml`; otherwise the issue has `file` set to the directory, field `""` and message `missing pipeline file <dir>.yaml`.
- **Pipeline name:** must equal the folder name; otherwise field `name`, message `must match the folder name '<dir>'`.
- **YAML:** invalid YAML or a non-mapping document gives field `""`, message `invalid YAML: ...` or `must be a mapping`.
- **Schema errors:** become issues, and the object is left out of the model.

- [ ] **Step 1: Write the failing tests**
  - `test_loads_fixtures`: copies `tests/fixtures/pipelines/*` into a `project` and loads it. Checks:
    - `issues == []`;
    - actor names `{"human", "machine", "claude", "opencode"}`;
    - `p.pipelines["bug-fix"].phase("triage").route.by == "claude"`;
    - `children("triage") == ["quick-fix", "tdd"]`;
    - `ancestors("review") == {"fetch-issue", "triage", "quick-fix", "tdd"}`;
    - the `tdd` phase has `pipeline == "tdd"`.
  - One test per loader rule above, each asserting the exact `(file, field, message)` triple.
  - `test_schema_error_excludes_pipeline`: the pipeline is missing from `pipelines` and its issue carries the schema path.
- [ ] **Step 2: Run to make sure they fail.**
- [ ] **Step 3: Implement `model.py` and `loader.py`.**
- [ ] **Step 4: Run the tests and lint.**
- [ ] **Step 5: Commit** `git commit -m "Load actors and pipelines into a typed model"`

### Task 8: Expression parser

**Files:**
- Create: `src/lasagna_cli/expressions.py`, `tests/test_expressions.py`

**Interfaces:**
- Produces:
  - `class ExpressionError(ValueError)`
  - `@dataclass(frozen=True) class Ref(scope: Literal["pipeline.inputs", "phases", "inputs", "outputs", "harness.main_skill"], phase: str | None, name: str | None)`
  - `has_expression(text: str) -> bool`: true if `${{` appears.
  - `find_refs(text: str) -> list[Ref]`: in order of appearance; raises `ExpressionError` on a malformed body or an unclosed `${{`.

Grammar, where `NAME` is `[a-z][a-z0-9]*(?:-[a-z0-9]+)*`. Each `${{ ... }}`, with optional surrounding whitespace, contains exactly one of:
- `pipeline.inputs.NAME`
- `phases.NAME.outputs.NAME`
- `inputs.NAME`
- `outputs.NAME`
- `harness.main_skill`

- [ ] **Step 1: Write the failing tests**
  - `find_refs("${{ phases.fetch-issue.outputs.issue-file }}/x ${{inputs.a}}") == [Ref("phases", "fetch-issue", "issue-file"), Ref("inputs", None, "a")]`
  - `find_refs("${{ harness.main_skill }}") == [Ref("harness.main_skill", None, None)]`
  - `find_refs("${{ pipeline.inputs.issue }}") == [Ref("pipeline.inputs", None, "issue")]`
  - `find_refs("plain $X text") == []`
  - These raise `ExpressionError`: `"${{ foo.bar }}"`, `"${{ inputs.Bad }}"`, `"${{ inputs.a"`, `"${{ }}"`.
- [ ] **Step 2: Run to make sure they fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the tests and lint.**
- [ ] **Step 5: Commit** `git commit -m "Parse \${{ }} expressions into references"`

### Task 9: References, graph and nesting rules

**Files:**
- Create: `src/lasagna_cli/validation/__init__.py`, `src/lasagna_cli/validation/references.py`, `tests/test_rules_references.py`

**Interfaces:**
- Consumes: `Project`, `Pipeline`, `Phase`, `Issue`.
- Produces:
  - `check_references(project: Project) -> list[Issue]`
  - `validate_project(project: Project) -> list[Issue]` in `validation/__init__.py`: `project.issues` plus every `check_*`, sorted by `(file, field)`. Later tasks add their checks to it.

Rules: issues go on the pipeline file; `i` is the phase index.

| # | Field | Message |
|---|---|---|
| R1 | `phases[i].actor` | `unknown actor '<a>'` |
| R2 | `phases[i].trigger.by`, `phases[i].route.by`, `phases[i].loop.until.by` | `unknown actor '<a>'` |
| R3 | `trigger.by` | `unknown actor '<a>'` |
| R4 | `phases[i].pipeline` | `unknown pipeline '<p>'` |
| R5 | `phases[i].id` | `duplicate phase id '<id>'` |
| R6 | `phases[i].needs` | `unknown phase '<id>'` |
| R7 | `phases` | `exactly one phase without needs is required, found <n>` |
| R8 | `phases` | `cycle between phases: a -> b -> a` |
| R9a | `phases[i]` | `phase '<id>' has <n> children and needs a route` |
| R9b | `phases[i].route` | `route is only allowed on a phase with more than one child` |
| R10 | `phases[i].pipeline` | `cycle between pipelines: a -> b -> a` |
| R11 | `phases[i].pipeline` | `nesting depth <d> exceeds limits.max_depth <m>` |
| R12 | `phases[i].harness.main_skill` | `missing harness/phases/<id>/SKILL.md` |
| R13 | `harness.skills` or `phases[i].harness.skills` | `missing skill '<n>' (harness/skills/<n>/SKILL.md)` |
| R14 | `harness.mcp` or `phases[i].harness.mcp` | `missing MCP file '<n>' (harness/mcp/<n>.json)` |

R11 depth: a pipeline's depth is 0 with no sub-pipeline phases, otherwise 1 plus the maximum depth of its children. Each pipeline is checked as a potential root. Skip R11 for pipelines involved in a cycle.

- [ ] **Step 1: Write the failing tests**
  - A `base_pipeline()` helper returns a valid two-phase pipeline dict: machine `a` → machine `b`.
  - One parametrized case per row above: the case mutates the base (or writes two pipelines for R4, R10 and R11), runs `validate_project(load_project(project))`, and asserts that an `Issue` with that field and that message is present.
  - R11 cases:
    - A max_depth of 1 with a nesting depth of 2 fails.
    - A max_depth of 0 with one sub-pipeline fails.
    - The fixtures with the default max_depth of 3 pass.
- [ ] **Step 2: Run to make sure they fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the tests and lint.**
- [ ] **Step 5: Commit** `git commit -m "Validate names, references, graph shape and nesting depth"`

### Task 10: Actor, sub-pipeline and decider rules

**Files:**
- Create: `src/lasagna_cli/validation/actors.py`, `tests/test_rules_actors.py`
- Modify: `src/lasagna_cli/validation/__init__.py`

**Interfaces:**
- Produces: `check_actors(project: Project) -> list[Issue]`. Phases or deciders whose actor is unknown are skipped (R1/R2 already report them). `<d>` stands for a decider field: `trigger`, `route` or `loop.until`.

| # | Condition | Field | Message |
|---|---|---|---|
| A1a | machine phase without `with.command` | `phases[i].with.command` | `required for a machine actor` |
| A1b | machine `with` key other than `command` | `phases[i].with.<k>` | `not allowed for a machine actor` |
| A2 | human `with` key other than `instructions`, `command` | `phases[i].with.<k>` | `not allowed for a human actor` |
| A3a | agent `with` key not in `params` | `phases[i].with.<k>` | `agent '<a>' has no param '<k>'` |
| A3b | agent param with `required: true` missing from `with` | `phases[i].with` | `missing required param '<k>' for agent '<a>'` |
| A4 | `interactive: true` on a non-agent, or on an agent without `run_interactive` | `phases[i].interactive` | `requires an agent with commands.run_interactive` |
| A5 | `harness` on a phase not run by an agent | `phases[i].harness` | `only allowed on phases run by an agent` |
| A6a | child input with `required` true and no `default`, missing from the phase `inputs` | `phases[i].inputs` | `missing input '<k>' required by pipeline '<p>'` |
| A6b | phase input not declared by the child | `phases[i].inputs.<k>` | `pipeline '<p>' has no input '<k>'` |
| D1a | machine decider with `prompt` or `instructions` | `phases[i].<d>.<f>` | `not allowed when a machine decides` |
| D1b | machine route without `check` | `phases[i].route.check` | `required when a machine decides a route` |
| D2a | agent decider without `prompt` | `phases[i].<d>.prompt` | `required when an agent decides` |
| D2b | agent decider with `check` or `instructions` | `phases[i].<d>.<f>` | `not allowed when an agent decides` |
| D3 | human decider with `check` or `prompt` | `phases[i].<d>.<f>` | `not allowed when a human decides` |

- [ ] **Step 1: Write the failing tests**: one parametrized negative case per row, built from `base_pipeline()`. Also one positive test: the fixtures and `examples/pipelines/spec-to-code` produce no issues from `check_actors`.
- [ ] **Step 2: Run to make sure they fail.**
- [ ] **Step 3: Implement and register in `validate_project`.**
- [ ] **Step 4: Run the tests and lint.**
- [ ] **Step 5: Commit** `git commit -m "Validate actor params, sub-pipeline inputs and deciders"`

### Task 11: Expression placement rules

**Files:**
- Create: `src/lasagna_cli/validation/expr_rules.py`, `tests/test_rules_expressions.py`
- Modify: `src/lasagna_cli/validation/__init__.py`

**Interfaces:**
- Consumes: `find_refs`, `has_expression`, `ExpressionError`.
- Produces: `check_expressions(project: Project) -> list[Issue]`.

Fields that run as shell commands must contain no `${{` at all. Each has its own field path:
- phase `with.command`;
- decider `check`;
- actor `commands.check[j]`, `commands.inject`, `commands.run`, `commands.run_interactive` and `commands.cleanup`, with the actor file as the issue's `file`.

The message is: `expressions are not allowed in shell commands; use environment variables`.

Fields where expressions are scanned, and the scopes allowed in each:

| Field | Allowed scopes |
|---|---|
| `phases[i].inputs.<k>` | `pipeline.inputs`, `phases` |
| `phases[i].with.<k>` (k ≠ `command`) | `pipeline.inputs`, `phases`, `inputs`, `harness.main_skill` |
| `phases[i].outputs.<k>.path` | `pipeline.inputs`, `phases`, `inputs`, `outputs` (value outputs only), `harness.main_skill` |
| `phases[i].trigger.prompt` / `.instructions` | `pipeline.inputs`, `phases`, `harness.main_skill` |
| `phases[i].route.*`, `phases[i].loop.until.*` (prompt, instructions) | all five scopes |
| `outputs.<k>` (pipeline) | `phases` |

Reference checks:

| # | Condition | Message |
|---|---|---|
| E1 | `${{` in a shell field | `expressions are not allowed in shell commands; use environment variables` |
| E2 | malformed expression | `invalid expression: <ExpressionError text>` |
| E3 | scope not allowed in this field | `<scope>.* is not allowed here` |
| E4a | `phases.<id>`, in a phase field, where `<id>` is not an ancestor | `phase '<id>' is not an ancestor of '<this>'` |
| E4b | output not declared by phase `<id>` (for a sub-pipeline phase, its declared outputs are the child pipeline's `outputs` keys) | `phase '<id>' has no output '<n>'` |
| E5 | `pipeline.inputs.<n>` not declared | `pipeline has no input '<n>'` |
| E6 | `inputs.<n>` not declared in the phase `inputs` | `phase '<this>' has no input '<n>'` |
| E7a | `outputs.<n>` not declared by the phase | `phase '<this>' has no output '<n>'` |
| E7b | in a file path, `outputs.<n>` of type `file` | `only value outputs are allowed in a file path` |
| E8 | `harness.main_skill` when the phase lacks `harness.main_skill: true` | `requires harness.main_skill: true` |

- [ ] **Step 1: Write the failing tests**
  - One parametrized negative case per row of the reference table and per scope cell that forbids something:
    - `inputs.*` in a trigger prompt;
    - `inputs.*` inside `inputs`;
    - `outputs.*` in `with`;
    - `harness.main_skill` in pipeline outputs;
    - `outputs.*` in a trigger.
  - One case per shell field, including an actor command.
  - Positive test: the fixtures and the example produce no issues from `check_expressions`. That covers `${{ outputs.spec-dir }}/spec.md` and `phases.tdd.outputs.test-file` through the child's outputs.
- [ ] **Step 2: Run to make sure they fail.**
- [ ] **Step 3: Implement and register in `validate_project`.**
- [ ] **Step 4: Run the tests and lint.**
- [ ] **Step 5: Commit** `git commit -m "Validate where expressions appear and what they reference"`

### Task 12: `lasagna validate`

**Files:**
- Create: `tests/test_validate_cli.py`
- Modify: `src/lasagna_cli/cli.py`, `src/lasagna_cli/schemas.py`, `src/lasagna_cli/validation/__init__.py`

**Interfaces:**
- Produces:
  - `primitive_copy_warnings(root: Path) -> list[Issue]` in `schemas.py`. For each bundled schema file, compare bytes with `.lasagna/config/primitives/<file>`, CRLF normalised to LF:
    - if different: a warning `differs from the schema bundled with lasagna <version>`;
    - if missing: a warning `missing (bundled schemas are used)`.
  - `validate_project` includes these warnings.
  - CLI `lasagna validate`:
    - finds the root with `find_repo_root(Path.cwd())`; outside git it prints the error and exits 2;
    - if `.lasagna/` is missing: `no .lasagna/ found; run lasagna init`, exit 2;
    - otherwise prints each issue as `str(issue)`, then a summary:
      - with errors: `<e> errors, <w> warnings` and exit 2;
      - without errors: `valid: <n> actors, <m> pipelines (<w> warnings)` and exit 0.

The "Avvio" rules of §10 (`--as`, `--bind`, `--id`, clean `.lasagna/`) belong to `lasagna start` and are deferred to M3.

- [ ] **Step 1: Write the failing tests**
  - `test_fixtures_and_example_are_valid`: copy `tests/fixtures/pipelines/*` and `examples/pipelines/spec-to-code` into `project`, chdir, invoke `validate`. Expect exit 0, `valid: 4 actors, 3 pipelines (0 warnings)` in the output, and no `error:` lines.
  - `test_errors_exit_2`: a pipeline whose `name` differs from its folder. Expect exit 2, a line `error: .lasagna/pipelines/x/x.yaml: name: must match the folder name 'x'`, and the summary `1 errors, 0 warnings`.
  - `test_changed_primitive_copy_warns`: append a comment to `.lasagna/config/primitives/run.schema.yaml`. Expect exit 0 and a `warning: .lasagna/config/primitives/run.schema.yaml: differs from the schema bundled with lasagna 0.1.0` line.
  - `test_no_lasagna_dir`: exit 2 with `run lasagna init`.
- [ ] **Step 2: Run to make sure they fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Full verification**

Run: `uv run pytest -v && uv run ruff check . && uv run ruff format --check .`
Then by hand, in a scratch repo outside the project: `git init`, `uv run --project <repo> lasagna init`, copy `examples/pipelines/spec-to-code` into `.lasagna/pipelines/`, `uv run --project <repo> lasagna validate`.
Expected: all green; manual validate prints `valid: 4 actors, 1 pipelines (0 warnings)`.

- [ ] **Step 5: Commit, push, check CI on the three OSes, then stop for the M1 review.**

```bash
git commit -m "Add lasagna validate with schema, semantic rules and copy warnings"
```
