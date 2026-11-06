---
status: todo            # todo | in_progress | done | blocked
depends_on: ["09"]      # ticket numbers
criteria: [AC-V3-024, AC-V3-034, AC-V3-035, AC-V3-036, AC-V3-037, AC-V3-048]
---

# 10 — `lasagna init`, aggancio ad `AGENTS.md`/`CLAUDE.md`, `rules.md` definitivo

The `status` above is the only record of this ticket's state: the tickets index
and the current file never copy it.

## Goal

`lasagna init` crea `.lasagna/` (registry, `rules.md`, `pipelines/`), aggiunge
pipeline con `--with`, scrive il blocco in `AGENTS.md` e l'import in un
`CLAUDE.md` esistente, è idempotente, aggiorna un `rules.md` più vecchio e si
rifiuta su uno modificato a mano senza `--force`. Il `rules.md` del pacchetto
è definitivo: 11 sezioni in ordine, ≤ 250 righe, con la semantica dei
contatori del §6.3.4.

## Context

- Milestone M6 (§12); AC-V3-024 spostato qui da M4 perché, come AC-V3-037, è
  un test sul contenuto di `rules.md`.
- Spec §8.1 (testo esatto dei blocchi tra marcatori), D10, §7 (sezioni,
  commento di versione nella prima riga, aggiornamento e rifiuto), §6.3.4.
- `core/agents_md.py` nasce qui (inserimento idempotente, `str -> str`).
- `--with` riusa `add` del ticket 09.
- D11: si modifica solo `src/lasagna/protocol/rules.md`, **mai**
  `.lasagna/rules.md` (copia di processo, riallineata a `close_version`).
- **Rischio di red che passa subito (AC-V3-024, AC-V3-037):** il
  `src/lasagna/protocol/rules.md` di M0 ha già le 11 sezioni (circa 206
  righe) e la semantica di `max_iterations` e del reset nella sezione 5. Un
  test che legge il file passerebbe subito. Il contratto fa passare questi test
  da un nome dichiarato che ancora non esiste, per esempio un lettore delle
  sezioni di `rules.md` in `core/`.
- **Da chiedere al maintainer prima di iniziare (spec §14.8, P18):** UTF-8/LF
  e hash di `rules.md`. Decide come si riconosce un `rules.md` "modificato a
  mano" (AC-V3-036): va deciso prima del contratto.

## Changes

- `core/agents_md.py`: blocchi `<!-- lasagna:start -->` / `<!-- lasagna:end -->`.
- `shell/project.py`: creazione di `.lasagna/`, scrittura di `AGENTS.md`,
  `CLAUDE.md`, `rules.md`.
- `cli.py`: comando `init` con `--with`, `--no-agents-md`, `--force`.
- `src/lasagna/protocol/rules.md`: revisione finale contro il §7 (se serve).
- Riga in `CHANGELOG.md` sotto Unreleased.

## Files involved

- `src/lasagna/core/agents_md.py`, `src/lasagna/shell/project.py`, `src/lasagna/cli.py`
- `src/lasagna/protocol/rules.md`
- `tests/core/`, `tests/shell/`, `tests/e2e/`

## Tests to pass

<!-- Filled in by the implementation pipeline (node contract) as a checklist:
one line per planned verification, in order. The green node checks off a test
with `[x] (green after N)`; the review node checks off checks and reviews. -->

## Contract

<!-- Filled in by the implementation pipeline (node contract), from its
contract template. -->

## Out of scope

- `.lasagna/rules.md` di questo repo: si riallinea a `close_version` (D11).
- Nessun prompt interattivo e tabella §8.11 su tutti i comandi: ticket 11.
- `init` fuori dal repo da pacchetto installato (AC-V3-043): ticket 13.

## Definition of done

- [ ] every criterion has the verification the spec asks for: a test that fails on a plausible wrong implementation, a passing check, or a recorded review
- [ ] whole suite green
- [ ] changelog line under Unreleased
- [ ] traceability evidence filled in the tickets index; current file updated

## Log

<!-- One line per session: date | outcome | cycles used per criterion | summary of the [lasagna] lines | notes -->
