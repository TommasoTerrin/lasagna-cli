---
status: todo            # todo | in_progress | done | blocked
depends_on: ["02"]      # ticket numbers
criteria: [AC-V3-009, AC-V3-010, AC-V3-011, AC-V3-013, AC-V3-045]
---

# 03 — Regole del grafo (V07, V10, V12), `--json` e formato dei messaggi

The `status` above is the only record of this ticket's state: the tickets index
and the current file never copy it.

## Goal

`validate` applica V07 (entry), V10 (un solo arco in avanti) e V12 (loop
`when: fail` da nodo senza gate). Ogni messaggio ha file, percorso YAML, ID
della regola e frase di correzione. `--json` restituisce `errors` e `warnings`
con `rule`, `file`, `path`, `message`.

## Context

- Milestone M2, seconda parte (§12).
- Spec §5 (V07, V10, V12; formato dei messaggi), §6.1 (entry e nodi finali),
  §8.2 (`--json`).
- `core/graph.py` nasce qui (§9.1): archi in uscita, archi "in avanti". Il
  ticket 06 lo estende (raggiungibilità V08, nodi finali V09, cicli V23).
- Formato dei messaggi: lo usano tutte le regole, comprese V01, V05 e V06 del
  ticket 01, da riallineare qui se non lo rispettano.

## Changes

- `core/graph.py`: archi in uscita per nodo, classificazione degli archi.
- `core/validate.py`: V07, V10, V12; frase di correzione per ogni regola
  esistente.
- `cli.py`: `validate --json`.
- Riga in `CHANGELOG.md` sotto Unreleased.

## Files involved

- `src/lasagna/core/graph.py`, `src/lasagna/core/validate.py`, `src/lasagna/cli.py`
- `tests/core/`, `tests/e2e/`

## Tests to pass

<!-- Filled in by the implementation pipeline (node contract) as a checklist:
one line per planned verification, in order. The green node checks off a test
with `[x] (green after N)`; the review node checks off checks and reviews. -->

## Contract

<!-- Filled in by the implementation pipeline (node contract), from its
contract template. -->

## Out of scope

- Tutte le altre regole V, la matrice di AC-V3-007, avvisi e `--strict`
  (AC-V3-008), prestazioni (AC-V3-049): ticket 06.
- `validate <id>` e `--project` (AC-V3-046): ticket 11.

## Definition of done

- [ ] every criterion has the verification the spec asks for: a test that fails on a plausible wrong implementation, a passing check, or a recorded review
- [ ] whole suite green
- [ ] changelog line under Unreleased
- [ ] traceability evidence filled in the tickets index; current file updated

## Log

<!-- One line per session: date | outcome | cycles used per criterion | summary of the [lasagna] lines | notes -->
