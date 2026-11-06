---
status: todo            # todo | in_progress | done | blocked
depends_on: ["06"]      # ticket numbers
criteria: [AC-V3-039, AC-V3-040, AC-V3-041]
---

# 12 — Pipeline incluse definitive

The `status` above is the only record of this ticket's state: the tickets index
and the current file never copy it.

## Goal

Le tre pipeline incluse in `src/lasagna/builtin/` passano
`lasagna validate --strict`, `project-manager` si valida con i parametri di
Fidelitree (§11.4), e gli asset del §10 esistono con le sezioni richieste.

## Context

- Milestone M7 (§12), prima parte.
- Spec §10 (blocchi normativi e asset con le loro sezioni), §11.3, §11.4.
- Le frasi degli `steps` e i testi degli asset si possono rifinire senza
  cambiare struttura, nodi, archi e gate (§10); ogni modifica ai file va
  riportata nei blocchi YAML della spec §10.
- D11: si modifica solo `src/lasagna/builtin/`, **mai** `.lasagna/pipelines/`.
- **Rischio di red che passa subito (AC-V3-041):** gli asset e le loro sezioni
  esistono già da M0. Il contratto fa passare il test da un nome dichiarato che
  ancora non esiste (per esempio un lettore degli asset in `shell/builtin.py`
  o un estrattore delle sezioni in `core/`).
- **Da chiedere al maintainer prima di iniziare:** spec §14.8, P19 (test di
  sincronizzazione blocchi della spec ↔ file, non approvato); spec §14.1, il
  nome di import `lasagna` (da decidere prima di M7).

## Changes

- Rifinitura delle pipeline e degli asset in `src/lasagna/builtin/`, se
  `validate --strict` o le lessons learned dei ticket 01–11 lo chiedono.
- Test: le tre pipeline incluse con `--strict`; `project-manager` con i
  parametri del §11.4; esistenza e sezioni degli asset.
- `docs/specs/v3.0.0.md` §10: blocchi aggiornati se i file cambiano.
- AC-V3-039 (check): `uv run lasagna validate --strict` sulle pipeline
  incluse, registrato nella checklist di rilascio.
- Riga in `CHANGELOG.md` sotto Unreleased.

## Files involved

- `src/lasagna/builtin/**`
- `docs/specs/v3.0.0.md` (solo §10, se i file cambiano)
- `tests/`

## Tests to pass

<!-- Filled in by the implementation pipeline (node contract) as a checklist:
one line per planned verification, in order. The green node checks off a test
with `[x] (green after N)`; the review node checks off checks and reviews. -->

## Contract

<!-- Filled in by the implementation pipeline (node contract), from its
contract template. -->

## Out of scope

- La metà "`diff -r` vuoto" di AC-V3-039: si verifica nel nodo
  `close_version` di `project-manager`, quando la copia di processo si
  riallinea con approvazione (D11).
- `.lasagna/pipelines/` e `.lasagna/rules.md`: mai in questo ticket.
- README: ticket 13.

## Definition of done

- [ ] every criterion has the verification the spec asks for: a test that fails on a plausible wrong implementation, a passing check, or a recorded review
- [ ] whole suite green
- [ ] changelog line under Unreleased
- [ ] traceability evidence filled in the tickets index; current file updated

## Log

<!-- One line per session: date | outcome | cycles used per criterion | summary of the [lasagna] lines | notes -->
