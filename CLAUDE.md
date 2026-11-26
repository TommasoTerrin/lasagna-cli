# lasagna-cli

Python CLI that orchestrates pipelines whose phases are run by humans, machines
or AI agents launched from the command line. Every run is isolated in its own
git worktree and recorded in an append-only JSONL event log.

## Sources of truth

- `harness/PROTOCOL.md`: the normative spec, in Italian, local only. Read the
  relevant section before working on any feature.
- `src/lasagna_cli/templates/lasagna/config/primitives/*.schema.yaml`: JSON
  Schemas of the primitives, part of the spec.
- Precedence: PROTOCOL.md, then schemas, then everything else. On a conflict,
  gap or ambiguity, stop and ask. Never change the protocol or the schemas on
  your own.
- These instructions take precedence over the defaults of any plugin or skill.

## Language

Everything committed is in English: code, identifiers, comments, docstrings,
CLI messages, commit messages, docs. The only exception is `README.it.md`.
`harness/` is Italian, excluded through `.git/info/exclude`: never add it to git.

## Stack and commands

Python 3.11+, uv, src layout, Typer, PyYAML, jsonschema + referencing, pytest,
ruff. Distribution name `lasagna-cli`, module `lasagna_cli`, command `lasagna`.
MIT license. CI on GitHub Actions: ubuntu-latest, macos-latest, windows-latest.

- `uv sync`: install dependencies
- `uv run pytest`: run the tests
- `uv run ruff check . && uv run ruff format --check .`: lint and format check
- `uv run lasagna --help`: run the CLI

Ask before adding a runtime dependency.

## Layout

- `src/lasagna_cli/`: the package
- `src/lasagna_cli/templates/lasagna/`: what `lasagna init` writes into
  `.lasagna/` (the `gitignore` file is written as `.gitignore`)
- `tests/fixtures/`: valid pipelines and run logs used by the tests
- `tests/fakes/`: fake agents used by the tests
- `examples/pipelines/spec-to-code/`: the acceptance-test pipeline

## Non-negotiable rules

1. User-defined commands (agent commands, `with.command`, `check`) run with
   `bash -c` on every OS. On Windows use Git for Windows' bash and never
   `C:\Windows\System32\bash.exe`, which starts WSL.
2. `${{ }}` expressions are never interpolated into shell strings. Values reach
   commands only as environment variables.
3. Only Lasagna writes `.lasagna/runs/*.jsonl`. Append-only, increasing `seq`,
   one lock per run. Current state is always derived by replaying events.
4. No background processes. The command that advances a run drives it in the
   foreground until the next human wait. Interactive phases inherit the terminal.
5. Git through the `git` CLI via subprocess. No git libraries.
6. Cross-platform: `pathlib` everywhere, forward slashes when passing paths to
   bash, LF line endings, timeouts kill the whole process tree.
7. Out of scope for the MVP: extensions, `foreach` and parallelism, active
   triggers or daemons, roles and verified identity, machine constraints,
   optional phase inputs, SQLite index.

## Testing

- Test-driven: write the failing test first.
- No test calls Claude, OpenCode or the network. Agents in tests are fake
  agents: actor files whose commands run a Python script from `tests/fakes/`.
- Tests touching git use real repositories created in `tmp_path`.
- Tests must pass on Windows, Linux and macOS.
- tests/conftest.py puts fake claude and opencode first on PATH for the whole
  session (they exit with 97). Never remove or bypass this guard.

## Workflow

- Superpowers skills to use: writing-plans, executing-plans,
  test-driven-development. The `verification-before-completion` skill no longer
  exists; its role is covered by running the full test suite and both ruff
  checks before every commit.
- Do not use: brainstorming to redesign (the design is PROTOCOL.md),
  subagent-driven-development, requesting-code-review, receiving-code-review,
  systematic-debugging, dispatching-parallel-agents. If a bug resists, stop and
  explain what you tried.
- Brainstorming is allowed only for new features not covered by PROTOCOL.md,
  never to redesign what the protocol already defines.
- One branch per milestone. Stop at the end of each milestone for review and
  do not start the next one without approval.
- Small commits with imperative English messages.
- A task is done only when tests are green and ruff is clean.
- Never pipe test or lint commands (for example into tail): check their exit
  code directly.
- A local `.git/hooks/pre-commit` (not versioned) runs `uv run pytest -q` and both
  ruff checks and blocks the commit if one fails. Never bypass it with
  `--no-verify`.
