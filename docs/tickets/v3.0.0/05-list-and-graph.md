---
status: todo            # todo | in_progress | done | blocked
depends_on: ["02"]      # ticket numbers
criteria: [AC-V3-020, AC-V3-021]
---

# 05 — `lasagna list` e `lasagna graph`

The `status` above is the only record of this ticket's state: the tickets index
and the current file never copy it.

## Goal

`list` mostra le pipeline abilitate del progetto (`--all` anche le
disabilitate, `--builtin` quelle incluse nel pacchetto); `graph` produce il
diagramma Mermaid del §8.5, uguale a uno snapshot committato.

## Context

- Milestone M3 (§12), seconda parte.
- Spec §8.3 (`list`: id, versione, descrizione, `started_by` del nodo
  iniziale), §8.5 (forme per `started_by`, simboli `[H]`/`[C]`/`[A]`, stili
  degli archi).
- `shell/builtin.py` nasce qui (lettura delle pipeline incluse nel pacchetto,
  per `--builtin`); il ticket 09 lo riusa per `add builtin:`.
- `core/mermaid.py` è puro: riceve il modello, restituisce testo.

## Changes

- `core/view.py`: vista di `list` (markdown e `--json`).
- `core/mermaid.py`: generazione del diagramma.
- `shell/builtin.py`: elenco e lettura delle pipeline incluse.
- `cli.py`: comandi `list` e `graph` (`--output <file>`).
- Snapshot di testo del diagramma di una pipeline di prova.
- Riga in `CHANGELOG.md` sotto Unreleased.

## Files involved

- `src/lasagna/core/view.py`, `src/lasagna/core/mermaid.py`
- `src/lasagna/shell/builtin.py`, `src/lasagna/cli.py`
- `tests/core/`, `tests/e2e/`, snapshot sotto `tests/`

## Tests to pass

<!-- Filled in by the implementation pipeline (node contract) as a checklist:
one line per planned verification, in order. The green node checks off a test
with `[x] (green after N)`; the review node checks off checks and reviews. -->

## Contract

<!-- Filled in by the implementation pipeline (node contract), from its
contract template. -->

## Out of scope

- `--project` su questi comandi: ticket 11.
- Il contenuto definitivo delle pipeline incluse: ticket 12.

## Definition of done

- [ ] every criterion has the verification the spec asks for: a test that fails on a plausible wrong implementation, a passing check, or a recorded review
- [ ] whole suite green
- [ ] changelog line under Unreleased
- [ ] traceability evidence filled in the tickets index; current file updated

## Log

<!-- One line per session: date | outcome | cycles used per criterion | summary of the [lasagna] lines | notes -->
