---
status: todo            # todo | in_progress | done | blocked
depends_on: ["05", "06"]  # ticket numbers
criteria: [AC-V3-028, AC-V3-029, AC-V3-030, AC-V3-047]
---

# 09 — `lasagna add`

The `status` above is the only record of this ticket's state: the tickets index
and the current file never copy it.

## Goal

`lasagna add <source>` copia una pipeline (`builtin:<id>` o cartella locale)
in `.lasagna/pipelines/<id>/` e la registra in `pipelines.yaml` preservando
commenti e ordine. Una pipeline non valida non viene copiata; un id esistente
si rifiuta senza `--force`; da cartella si scrive `enabled: false` salvo
`--enable`. Alla fine elenca tutto ciò che è eseguibile.

## Context

- Milestone M5 (§12).
- Spec §8.8 (i cinque passi di `add`, messaggio finale "a pipeline is
  instructions for your agent: review it with `lasagna show <id>`"), §4.3
  (`source`, `enabled`), D14 (`ruamel.yaml` round-trip), P15.
- Riusa `shell/builtin.py` del ticket 05 e la validazione completa del ticket
  06 (passo 1: valida la sorgente da sola; passo 5: valida il registry
  risultante).
- `core/sources.py` nasce qui (parsing della sorgente, puro).
- **Da chiedere al maintainer prima di iniziare (spec §14.8, P08):**
  hardening di `add` contro symlink e path traversal nella cartella sorgente.
  Proposta non ancora decisa.

## Changes

- `core/sources.py`: `builtin:<id>` o cartella; errore per le altre.
- `shell/project.py`: copia della cartella e scrittura round-trip del registry.
- `cli.py`: comando `add` con `--id`, `--param k=v`, `--enable`, `--force`.
- Riga in `CHANGELOG.md` sotto Unreleased.

## Files involved

- `src/lasagna/core/sources.py`, `src/lasagna/shell/project.py`
- `src/lasagna/shell/builtin.py`, `src/lasagna/cli.py`
- `tests/core/`, `tests/shell/`, `tests/e2e/`

## Tests to pass

<!-- Filled in by the implementation pipeline (node contract) as a checklist:
one line per planned verification, in order. The green node checks off a test
with `[x] (green after N)`; the review node checks off checks and reviews. -->

## Contract

<!-- Filled in by the implementation pipeline (node contract), from its
contract template. -->

## Out of scope

- `library:` e `git+` (3.4, P12).
- `init --with`: ticket 10.
- Gli errori "unknown source", "no pipeline.yaml", "exists: use --force",
  "cannot write" come tabella §8.11 completa: ticket 11 (qui solo quanto
  serve ad AC-V3-029 e AC-V3-030).

## Definition of done

- [ ] every criterion has the verification the spec asks for: a test that fails on a plausible wrong implementation, a passing check, or a recorded review
- [ ] whole suite green
- [ ] changelog line under Unreleased
- [ ] traceability evidence filled in the tickets index; current file updated

## Log

<!-- One line per session: date | outcome | cycles used per criterion | summary of the [lasagna] lines | notes -->
