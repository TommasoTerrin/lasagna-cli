# AGENTS.md — lasagna-cli

Entry point for any coding agent working on this repository.

<!-- lasagna:start -->
## Process (lasagna)
This project describes its work processes as lasagna pipelines.
Before starting a task, read `.lasagna/rules.md` (and `.lasagna/rules.local.md`
if present), then pick a pipeline from `.lasagna/pipelines.yaml`.
<!-- lasagna:end -->

## What this repository is

lasagna 3: a **protocol** to describe work processes for coding agents (YAML
registry and pipelines plus `rules.md`) and a **Python CLI** that manages it.
It is built **with its own pipelines** (dogfooding): the protocol works without
the CLI, so the agent follows `.lasagna/` by reading the files until the CLI
exists.

- Spec of 3.0.0: `docs/specs/v3.0.0.md` (the only source of truth for this version).
- Roadmap of later versions: `docs/roadmap.md`.
- Where the work stands: `docs/current.md`.
- Tickets: `docs/tickets/v3.0.0/` (created by the project-manager pipeline).
- Design conventions and commands: `docs/architecture.md`.
- Background only: `docs/reference/lasagna-v2-spec.md`, the spec of the
  previous product (a Claude Code plugin, repository `lasagna-code`, now
  deprecated). Ideas come from there; nothing is built on it.

## Rules

1. One ticket per session, with the `implementation` pipeline; planning
   sessions use `project-manager`; small fixes use `quick-fix`.
2. Never edit `.lasagna/pipelines/`: it is the frozen process copy. The product
   sources of the built-in pipelines are in `src/lasagna/builtin/` (spec D11).
   Exception ("process hotfix"): a defect of the process that prevents work is
   fixed in both copies in the same commit, with the maintainer's approval and
   a `fix(process):` entry in the changelog.
3. Decisions in the spec's §3 are closed: if one turns out wrong, stop and ask.
   Open points (§14) are asked before they are touched.
4. Commit and push only with the maintainer's approval. Conventional Commits.
5. Product files (code, `rules.md`, pipelines, CLI messages, README) are in
   English; project documents in `docs/` are in Italian.
6. Licenses: Apache-2.0 for code, spec, docs and tests; MIT-0 for the content
   that `lasagna add` copies into other projects (`src/lasagna/builtin/`,
   `src/lasagna/protocol/rules.md` and their copies in `.lasagna/`). The mapping
   is in `REUSE.toml`; do not add per-file license headers.
