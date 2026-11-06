---
status: todo            # todo | in_progress | done | blocked
depends_on: ["02"]      # ticket numbers
criteria: [AC-V3-015, AC-V3-016, AC-V3-017, AC-V3-018, AC-V3-019]
---

# 04 — Templating, `$pipeline/` e `lasagna show`

The `status` above is the only record of this ticket's state: the tickets index
and the current file never copy it.

## Goal

`lasagna show <id>` e `lasagna show <id> <node> --input k=v` mostrano la
pipeline e il nodo renderizzati: parametri risolti con la loro origine
(registry o default), `{{ params.* }}` e `{{ inputs.* }}` sostituiti solo nei
campi di testo, `$pipeline/` risolto.

## Context

- Milestone M3 (§12), la parte "lettura per agenti".
- Spec D9 (templating minimo: campi di testo, spazi opzionali, ogni altro `{{`
  invariato), §6.7, §8.4 (`show` con e senza nodo; input mancanti restano
  `{{ inputs.x }}`), §4.4 (precedenza registry > default).
- `core/render.py` nasce qui. Il ticket 06 ne riusa lo scanner dei segnaposto
  (V17, V24) e la risoluzione di `$pipeline/` (V20): esporli come funzioni
  pure.
- `core/view.py` nasce qui (testo e JSON di `show`); il ticket 05 lo estende
  per `list`.
- **Da chiedere al maintainer prima di iniziare (spec §14.8, P08):**
  hardening di `$pipeline/` contro path traversal (`$pipeline/../..`) e
  symlink. Proposta non ancora decisa.

## Changes

- `core/render.py`: sostituzione D9, risoluzione dei parametri, `$pipeline/`.
- `core/view.py`: vista di `show` (markdown e `--json`).
- `cli.py`: comando `show` con `--input` e `--json`.
- Riga in `CHANGELOG.md` sotto Unreleased.

## Files involved

- `src/lasagna/core/render.py`, `src/lasagna/core/view.py`, `src/lasagna/cli.py`
- `src/lasagna/shell/project.py`
- `tests/core/`, `tests/e2e/`

## Tests to pass

<!-- Filled in by the implementation pipeline (node contract) as a checklist:
one line per planned verification, in order. The green node checks off a test
with `[x] (green after N)`; the review node checks off checks and reviews. -->

## Contract

<!-- Filled in by the implementation pipeline (node contract), from its
contract template. -->

## Out of scope

- V17, V20, V24 (errori di validazione sui segnaposto e su `$pipeline/`):
  ticket 06.
- `list` e `graph`: ticket 05.
- Errori "id non presente" / "nodo inesistente" del §8.11: ticket 11.

## Definition of done

- [ ] every criterion has the verification the spec asks for: a test that fails on a plausible wrong implementation, a passing check, or a recorded review
- [ ] whole suite green
- [ ] changelog line under Unreleased
- [ ] traceability evidence filled in the tickets index; current file updated

## Log

<!-- One line per session: date | outcome | cycles used per criterion | summary of the [lasagna] lines | notes -->
