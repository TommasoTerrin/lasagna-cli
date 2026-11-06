---
status: todo            # todo | in_progress | done | blocked
depends_on: ["01"]      # ticket numbers
criteria: [AC-V3-005, AC-V3-006, AC-V3-014]
---

# 02 — Modello completo, chiavi `x-*`, JSON Schema

The `status` above is the only record of this ticket's state: the tickets index
and the current file never copy it.

## Goal

I modelli accettano ogni campo del protocollo 3.0 (§4.3–4.8): i registry del
§4.3 e del §11.1 e le tre pipeline del §10 si validano senza errori, il
`.lasagna/` di questo repo compreso. Le chiavi `x-*` sono ammesse solo dove la
spec lo consente. I JSON Schema committati corrispondono ai modelli.

## Context

- Milestone M2 (§12), prima metà: il modello. Le regole restanti sono dei
  ticket 03 e 06.
- Spec §4.3 (regole su chiavi sconosciute e `x-*`: ammesse negli oggetti a
  chiavi fisse, rifiutate nelle mappe `params`, `inputs`, `outputs`), §4.4–4.8
  (campi), §9.2 (JSON Schema generato da `models.py` con uno script, test che
  confronta).
- I blocchi YAML dei §4.3, §10 e §11.1 sono **normativi**: lo schema deve
  accettarli così come sono (§0).
- Auto-validazione (spec §11.2.5): da qui in poi la suite ha un test che valida
  il `.lasagna/` di questo repo. Anticipata rispetto al §11.2.5 ("M1") perché
  il modello essenziale del ticket 01 non accetta ancora tutti i campi.
- `docs/architecture.md`: `extra="forbid"`, `x-*` gestite esplicitamente.

## Changes

- `core/models.py` completo: registry, voce di pipeline (`enabled`, `source`,
  `params`), pipeline (`params`, `inputs`, `outputs`, `entry`), nodo
  (`started_by`, `steps`, `resources`, `gate`), archi `direct`/`loop`/`router`,
  risorsa, gate.
- Gestione di `x-*` (V01) secondo il §4.3.
- Script di generazione di `schema/registry.schema.json` e
  `schema/pipeline.schema.json`; i due file committati.
- Test che valida il `.lasagna/` di questo repo e le pipeline in
  `src/lasagna/builtin/`.
- Riga in `CHANGELOG.md` sotto Unreleased.

## Files involved

- `src/lasagna/core/models.py`, `src/lasagna/core/validate.py`
- `scripts/gen_schema.py` (o sotto `src/lasagna/`, a scelta del contratto)
- `schema/registry.schema.json`, `schema/pipeline.schema.json`
- `tests/core/`, `tests/shell/`

## Tests to pass

<!-- Filled in by the implementation pipeline (node contract) as a checklist:
one line per planned verification, in order. The green node checks off a test
with `[x] (green after N)`; the review node checks off checks and reviews. -->

## Contract

<!-- Filled in by the implementation pipeline (node contract), from its
contract template. -->

## Out of scope

- I vincoli che sono regole V con un ID (V02–V04, V07–V14, V17–V20, V22–V25)
  non si codificano qui come vincoli dei modelli: li implementano e li testano
  i ticket 03 e 06, ognuno con il suo `Finding`. Qui solo la forma (V01).
- `--json`, `--strict`: ticket 03 e 06.

## Definition of done

- [ ] every criterion has the verification the spec asks for: a test that fails on a plausible wrong implementation, a passing check, or a recorded review
- [ ] whole suite green
- [ ] changelog line under Unreleased
- [ ] traceability evidence filled in the tickets index; current file updated

## Log

<!-- One line per session: date | outcome | cycles used per criterion | summary of the [lasagna] lines | notes -->
