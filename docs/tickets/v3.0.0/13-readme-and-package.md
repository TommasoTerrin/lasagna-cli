---
status: todo            # todo | in_progress | done | blocked
depends_on: ["10", "12"]  # ticket numbers
criteria: [AC-V3-042, AC-V3-043]
---

# 13 — README e pacchetto pubblicabile

The `status` above is the only record of this ticket's state: the tickets index
and the current file never copy it.

## Goal

`README.md` e `README.it.md` descrivono la v3. Il pacchetto si costruisce con
`uv build`, si installa in un ambiente pulito e `lasagna init` funziona fuori
dal repo.

## Context

- Milestone M7 (§12), seconda parte.
- Spec §2 (obiettivi e non-obiettivi), D1, D10, §6.7 (cosa è convenzione e
  cosa no), §14.1 (`lasagna-ai`, nome su PyPI e nome di import).
- AC-V3-042 è una `review`: la nota di revisione va nell'Evidence
  dell'indice. AC-V3-043 è un `check`: comandi e risultato registrati nella
  checklist di rilascio.
- Licenze (AGENTS.md, regola 6): il contenuto di `src/lasagna/builtin/` e
  `src/lasagna/protocol/rules.md` è MIT-0 anche dentro il pacchetto
  (`REUSE.toml`).
- **Da chiedere al maintainer prima di iniziare (spec §14.1, ancora
  aperto):** il nome di import `lasagna` e la sua possibile collisione con
  `lasagna-ai`. La pubblicazione di `3.0.0a1` è già decisa (§14.1: appena
  `validate` funziona) e nessun ticket la contiene: è un'azione del
  maintainer.

## Changes

- `README.md` e `README.it.md`: protocollo, CLI, pipeline incluse,
  installazione con `uv tool` / `pipx`, cosa è convenzione e cosa no,
  differenza da `lasagna-ai`.
- `pyproject.toml`: metadati e classifier per la pubblicazione, se mancano.
- Check: `uv build`, installazione della wheel in un ambiente pulito, `lasagna
  init` in una cartella temporanea fuori dal repo.
- Riga in `CHANGELOG.md` sotto Unreleased.

## Files involved

- `README.md`, `README.it.md`, `pyproject.toml`
- `REUSE.toml` (solo se il contenuto del pacchetto lo richiede)

## Tests to pass

<!-- Filled in by the implementation pipeline (node contract) as a checklist:
one line per planned verification, in order. The green node checks off a test
with `[x] (green after N)`; the review node checks off checks and reviews. -->

## Contract

<!-- Filled in by the implementation pipeline (node contract), from its
contract template. -->

## Out of scope

- Pubblicazione su PyPI, tag, merge su `main`: nodo `release` di
  `project-manager`, con l'approvazione del maintainer.
- Bump della versione: nodo `close_version`.

## Definition of done

- [ ] every criterion has the verification the spec asks for: a test that fails on a plausible wrong implementation, a passing check, or a recorded review
- [ ] whole suite green
- [ ] changelog line under Unreleased
- [ ] traceability evidence filled in the tickets index; current file updated

## Log

<!-- One line per session: date | outcome | cycles used per criterion | summary of the [lasagna] lines | notes -->
