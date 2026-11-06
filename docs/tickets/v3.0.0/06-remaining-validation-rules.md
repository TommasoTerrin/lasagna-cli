---
status: todo            # todo | in_progress | done | blocked
depends_on: ["03", "04"]  # ticket numbers
criteria: [AC-V3-007, AC-V3-008, AC-V3-049]
---

# 06 — Regole di validazione restanti, avvisi e `--strict`

The `status` above is the only record of this ticket's state: the tickets index
and the current file never copy it.

## Goal

`validate` applica tutte le regole del §5. Ognuna fra V02–V05, V07–V14,
V17–V20, V23 e V24 ha un test che la fa scattare e uno che non la fa
scattare. V22 e V25 sono avvisi (exit 0, exit 1 con `--strict`). Un registry
con 10 pipeline da 20 nodi si valida in meno di 1 secondo.

## Context

- Milestone M2 (§12), chiusura della validazione.
- Spec §5 (tabella delle regole), D9 (V17, V24), §4.3 (V18), D7 (V19),
  §9.2 (V25, prestazioni).
- Riusa `core/graph.py` del ticket 03 (V08 raggiungibilità, V09 nodo finale
  raggiungibile, V23 aciclicità di `direct` + route) e `core/render.py` del
  ticket 04 (scanner dei segnaposto per V17/V24, `$pipeline/` per V20).
- AC-V3-007 è una matrice: V07, V10 e V12 hanno già test dal ticket 03, e
  V05 se il ticket 01 l'ha testata (va controllato). Il contratto registra
  come già coperte le regole che hanno già i test (aggiungendo il commento
  `# AC-V3-007`) e pianifica red solo per le altre, per non avere test che
  passano subito. Un test parametrizzato per regola (casi che
  scattano e casi che non scattano) tiene il numero di cicli sotto il limite
  del loop `green → red`.

## Changes

- `core/validate.py`: V05 (se il ticket 01 non l'ha già testata), V02, V03, V04, V08, V09, V11, V13, V14, V17, V18, V19,
  V20, V22, V23, V24, V25, con frase di correzione.
- `core/graph.py`: raggiungibilità, nodi finali, cicli fuori dai `loop`.
- `cli.py`: `validate --strict`.
- Test di prestazioni con un registry generato (10 × 20 nodi).
- Riga in `CHANGELOG.md` sotto Unreleased.

## Files involved

- `src/lasagna/core/validate.py`, `src/lasagna/core/graph.py`, `src/lasagna/cli.py`
- `tests/core/`, `tests/e2e/`

## Tests to pass

<!-- Filled in by the implementation pipeline (node contract) as a checklist:
one line per planned verification, in order. The green node checks off a test
with `[x] (green after N)`; the review node checks off checks and reviews. -->

## Contract

<!-- Filled in by the implementation pipeline (node contract), from its
contract template. -->

## Out of scope

- `validate <id>` e `--project` (AC-V3-046): ticket 11.
- Validazione delle pipeline incluse con i parametri di Fidelitree
  (AC-V3-040): ticket 12.

## Definition of done

- [ ] every criterion has the verification the spec asks for: a test that fails on a plausible wrong implementation, a passing check, or a recorded review
- [ ] whole suite green
- [ ] changelog line under Unreleased
- [ ] traceability evidence filled in the tickets index; current file updated

## Log

<!-- One line per session: date | outcome | cycles used per criterion | summary of the [lasagna] lines | notes -->
