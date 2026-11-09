import ast
from pathlib import Path

import lasagna

IMPURE_MODULES = {"os", "subprocess", "shutil", "socket", "random"}
MOCK_MODULES = {"unittest.mock", "mock", "pytest_mock"}
MOCK_PARAMS = {"monkeypatch", "mocker"}


def _root(name: str) -> str:
    return name.split(".")[0]


def _core_violations(tree: ast.AST) -> list[str]:
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _root(alias.name) in IMPURE_MODULES:
                    found.append(f"import {alias.name}")
                if alias.name == "lasagna.shell" or alias.name.startswith("lasagna.shell."):
                    found.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level == 0 and _root(module) in IMPURE_MODULES:
                found.append(f"from {module} import ...")
            if node.level == 0 and (module == "lasagna.shell" or module.startswith("lasagna.shell.")):
                found.append(f"from {module} import ...")
            if node.level == 0 and module == "lasagna" and any(a.name == "shell" for a in node.names):
                found.append("from lasagna import shell")
            if node.level > 0 and (module == "shell" or module.startswith("shell.")):
                found.append(f"from {'.' * node.level}{module} import ...")
            if node.level > 0 and module == "" and any(a.name == "shell" for a in node.names):
                found.append(f"from {'.' * node.level} import shell")
            if node.level > 0 and module == "lasagna" and any(a.name == "shell" for a in node.names):
                found.append("relative import of shell")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open":
            found.append("call to open()")
    return found


def _test_violations(tree: ast.AST) -> list[str]:
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in MOCK_MODULES or _root(alias.name) in {"mock", "pytest_mock"}:
                    found.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level == 0 and (
                module in MOCK_MODULES
                or _root(module) in {"mock", "pytest_mock"}
                or module.startswith("unittest.mock")
                or (module == "unittest" and any(a.name == "mock" for a in node.names))
            ):
                found.append(f"from {module} import ...")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            every = args.posonlyargs + args.args + args.kwonlyargs
            for arg in every:
                if arg.arg in MOCK_PARAMS:
                    found.append(f"{node.name}({arg.arg})")
    return found


def _scan_dir(directory: Path) -> tuple[dict[str, Path], dict[str, list[str]]]:
    scanned = {p.relative_to(directory).as_posix(): p for p in directory.rglob("*.py")}
    problems = {}
    for rel, path in scanned.items():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        bad = _core_violations(tree)
        if bad:
            problems[f"core/{rel}"] = bad
    return scanned, problems


# AC-V3-022
def test_purity_scan_reaches_subpackages(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "x.py").write_text("import os\n", encoding="utf-8")

    scanned, problems = _scan_dir(tmp_path)

    assert "sub/x.py" in scanned
    assert "core/sub/x.py" in problems


# AC-V3-022
def test_core_is_pure_and_core_tests_use_no_doubles():
    core_dir = Path(lasagna.__file__).parent / "core"
    assert core_dir.is_dir(), f"core directory is missing: {core_dir}"
    scanned, problems = _scan_dir(core_dir)

    assert "models.py" in scanned, f"core/models.py is missing; scanned: {sorted(scanned)}"
    assert "validate.py" in scanned, f"core/validate.py is missing; scanned: {sorted(scanned)}"
    assert not problems, f"core must stay pure: {problems}"

    tests_core = Path(__file__).parent
    test_files = sorted(tests_core.glob("*.py"))
    assert test_files, "no test files found in tests/core"
    test_problems = {}
    for path in test_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        bad = _test_violations(tree)
        if bad:
            test_problems[path.name] = bad
    assert not test_problems, f"core tests must not use doubles: {test_problems}"
