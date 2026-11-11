# Changelog

All notable changes to this project are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

- chore: bootstrap lasagna v3 process (rules.md, registry, built-in pipelines, AGENTS.md)
- chore: apply the pre-commit review of the M0 harness (P01-P36, see docs/reviews/2026-11-05-m0-review.md): approvals are written after their gate, `access` is a whitelist, `max_iterations` counts retries, one budget for green, the schema loses its fields without a consumer, sub-pipelines, the global library and `add git+` move to later versions
- chore: license the code, specification, docs and tests under Apache-2.0 and the content copied into other projects under MIT-0 (REUSE.toml)
- chore: add the minimal package scaffold (pyproject.toml, uv.lock, smoke test) so the first red fails for the right reason
- docs: add SECURITY.md, CONTRIBUTING.md and .editorconfig
- feat: add the `lasagna` script with `--version` and a minimal `validate` (V01, V05, V06) over essential models, with a purity test for core/
- test: check every forbidden form of the core purity detector against synthetic snippets, and that the scan reaches `__init__.py` and subpackages
- feat: full protocol model (registry, pipeline, nodes, resources, gates, direct/loop/router edges), x-* extension keys, V06 on every edge type, generated JSON Schema (schema/*.json) and self-validation of this repo's .lasagna/ and the built-in pipelines
- feat: V07 (an absent entry included), V10 and V12 over core/graph.py, validate --json, a correction phrase at the end of every message, findings on stdout and usage errors on stderr, stdout always UTF-8
- feat: `lasagna show <id> [<node>] [--input k=v] [--json]` renders a pipeline or a node with the resolved params (and where each comes from), `{{ params.* }}` and `{{ inputs.* }}` substituted in text fields only, and `$pipeline/` resolved in resource refs with a containment check against `..` and links that leave the folder
