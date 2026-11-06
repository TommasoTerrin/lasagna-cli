---
status: todo            # todo | in_progress | done | blocked
depends_on: ["04"]      # ticket numbers
criteria: [AC-V3-023]
---

# 07 — `lasagna check`

The `status` above is the only record of this ticket's state: the tickets index
and the current file never copy it.

## Goal

`lasagna check <id> <node>` esegue il gate `check` del nodo (o le route di un
router `decided_by: check`) dalla radice del progetto, con i template
risolti: exit 0 se il comando esce 0, 1 altrimenti, 2 se il nodo non ha un
gate `check`.

## Context

- Milestone M4 (§12), prima parte.
- Spec §8.6 (stampa comando, exit code, ultime 50 righe di output, esito),
  §9.2 (`shell=True`: `cmd.exe` su Windows; `run` è una chiamata di programma,
  eventualmente con `&&`), §6.4.
- Riusa `core/render.py` del ticket 04 per risolvere `{{ params.* }}` in
  `run` (`{{ inputs.* }}` in `run` è vietato da V24).
- `shell/run.py` nasce qui. I test usano comandi portabili (es. l'interprete
  Python corrente con `-c`), niente rete.

## Changes

- `shell/run.py`: esecuzione del comando dalla radice, cattura dell'output.
- `core/`: scelta del gate o delle route da eseguire e formattazione
  dell'esito (puro).
- `cli.py`: comando `check` con `--input`.
- Riga in `CHANGELOG.md` sotto Unreleased.

## Files involved

- `src/lasagna/shell/run.py`, `src/lasagna/cli.py`
- `src/lasagna/core/view.py` (o un modulo `core/` dedicato, a scelta del contratto)
- `tests/shell/`, `tests/e2e/`

## Tests to pass

<!-- Filled in by the implementation pipeline (node contract) as a checklist:
one line per planned verification, in order. The green node checks off a test
with `[x] (green after N)`; the review node checks off checks and reviews. -->

## Contract

<!-- Filled in by the implementation pipeline (node contract), from its
contract template. -->

## Out of scope

- Path con spazi su Windows (AC-V3-027): ticket 08, insieme a `doctor`.
- "command not found" e gli altri casi del §8.11: ticket 11.
- La semantica dei contatori in `rules.md` (AC-V3-024): ticket 10.

## Definition of done

- [ ] every criterion has the verification the spec asks for: a test that fails on a plausible wrong implementation, a passing check, or a recorded review
- [ ] whole suite green
- [ ] changelog line under Unreleased
- [ ] traceability evidence filled in the tickets index; current file updated

## Log

<!-- One line per session: date | outcome | cycles used per criterion | summary of the [lasagna] lines | notes -->
