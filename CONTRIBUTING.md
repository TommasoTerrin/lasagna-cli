# Contributing to lasagna

Thanks for looking. lasagna is built **with its own pipelines**, so contributing
follows the process the project describes.

## Before you start

1. Read `AGENTS.md` and `.lasagna/rules.md`: they are the entry point for people
   and for coding agents alike.
2. The specification of 3.0.0 is `docs/specs/v3.0.0.md` (in Italian: project
   documents under `docs/` are in Italian; code, `rules.md`, pipelines, CLI
   messages and the README are in English). Decisions in its section 3 are
   closed: if one looks wrong, open an issue and discuss it; do not work around
   it. Open points (section 14) are asked before they are touched.
3. For anything bigger than a small fix, open an issue or a discussion first.

## How work is organised

- One ticket per session, with the `implementation` pipeline; planning with
  `project-manager`; small fixes with `quick-fix`. Tickets live in
  `docs/tickets/`.
- `.lasagna/pipelines/` is the frozen process copy: do not edit it. The product
  sources of the built-in pipelines are in `src/lasagna/builtin/`. A process
  defect that blocks work is fixed in both copies in the same commit, with the
  maintainer's approval (spec D11).
- Branches: `main` is for releases, `develop` for work. Open pull requests
  against `develop`.
- Commits follow [Conventional Commits](https://www.conventionalcommits.org/).

## Development setup

```bash
uv sync
uv run pytest
uv run ruff check
```

Python 3.11 or newer. Tests must run without network access. The code in
`src/lasagna/core/` is pure (no I/O): see `docs/architecture.md`.

## License of contributions

There is no CLA. By submitting a contribution you license it under the license
of the path it touches (see `REUSE.toml`): Apache-2.0 for code, specification,
documentation and tests; MIT-0 for the built-in pipelines, their assets and
`rules.md`.

## Security

Do not report vulnerabilities in public issues: see `SECURITY.md`.
