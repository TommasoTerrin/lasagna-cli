---
status: todo            # todo | in_progress | done | blocked
depends_on: ["07"]      # ticket numbers
criteria: [AC-V3-025, AC-V3-026, AC-V3-027]
---

# 08 — `lasagna doctor`

The `status` above is the only record of this ticket's state: the tickets index
and the current file never copy it.

## Goal

`lasagna doctor [<id>]` riporta `ok`, `missing` o `unverified` per ogni
risorsa secondo il §8.7 ed esce 1 se manca una risorsa `required`. `check` e
`doctor` funzionano su Windows con path che contengono spazi.

## Context

- Milestone M4 (§12), seconda parte.
- Spec §8.7 (regole per tipo di risorsa; skill cercate in `.agents/skills/`,
  `.claude/skills/`, `.opencode/skills/`), §9.2 (Windows, `pathlib`).
- FCIS: `shell/facts.py` raccoglie i fatti (esistenza di file, `PATH`),
  `core/doctor.py` decide l'esito senza I/O.
- Questo repo vive in una cartella con spazi (OneDrive): i test di
  AC-V3-027 usano `tmp_path` con una sottocartella con spazi e girano anche
  anche su Windows (la CI è della 3.0.1: per ora in locale).

## Changes

- `core/doctor.py`: decisione `ok`/`missing`/`unverified` dai fatti.
- `shell/facts.py`: raccolta dei fatti.
- `cli.py`: comando `doctor` con `--json`.
- Test di `check` e `doctor` con path che contengono spazi.
- Riga in `CHANGELOG.md` sotto Unreleased.

## Files involved

- `src/lasagna/core/doctor.py`, `src/lasagna/shell/facts.py`, `src/lasagna/cli.py`
- `src/lasagna/shell/run.py` (solo se AC-V3-027 lo richiede)
- `tests/core/`, `tests/shell/`, `tests/e2e/`

## Tests to pass

<!-- Filled in by the implementation pipeline (node contract) as a checklist:
one line per planned verification, in order. The green node checks off a test
with `[x] (green after N)`; the review node checks off checks and reviews. -->

## Contract

<!-- Filled in by the implementation pipeline (node contract), from its
contract template. -->

## Out of scope

- Verifica reale di `mcp`, `url` e tipi non del nucleo: restano
  `unverified` ("the agent must verify").
- `--project` e gli errori del §8.11: ticket 11.

## Definition of done

- [ ] every criterion has the verification the spec asks for: a test that fails on a plausible wrong implementation, a passing check, or a recorded review
- [ ] whole suite green
- [ ] changelog line under Unreleased
- [ ] traceability evidence filled in the tickets index; current file updated

## Log

<!-- One line per session: date | outcome | cycles used per criterion | summary of the [lasagna] lines | notes -->
