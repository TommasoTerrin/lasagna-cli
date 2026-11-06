---
status: todo            # todo | in_progress | done | blocked
depends_on: ["08", "10"]  # ticket numbers
criteria: [AC-V3-038, AC-V3-044, AC-V3-046]
---

# 11 — Contratto della CLI su tutti i comandi: errori, `--project`, niente prompt

The `status` above is the only record of this ticket's state: the tickets index
and the current file never copy it.

## Goal

Ogni caso della tabella §8.11 esce con l'exit code indicato e un messaggio in
inglese su stderr con la correzione suggerita; `--project <path>` fa operare
ogni comando su quel progetto e `validate <id>` valida solo quella pipeline;
nessun comando chiede input (test con stdin chiuso).

## Context

- Fetta verticale "contratto d'errore end-to-end": attraversa tutti i
  comandi, quindi arriva quando esistono tutti (dopo `init`, ticket 10).
  AC-V3-044 (M2) e AC-V3-046 (M3) spostati qui: prima non tutti i comandi a cui
  si applicano esistono.
- Spec §8 (regole comuni: radice del progetto, exit 0/1/2, stderr, niente
  prompt), §8.11 (tabella dei casi), §8.2 (`validate <id>`).
- Questo ticket **possiede tutto** il lavoro sui casi del §8.11 e su
  `--project`: i ticket precedenti implementano solo quanto serve ai propri
  criteri. Un test parametrizzato per riga della tabella §8.11.
- **Rischio di red che passa subito (AC-V3-038):** se nessun comando chiede
  input, il test con stdin chiuso è verde al primo colpo. Il contratto lo fa
  passare da un nome dichiarato che ancora non esiste (per esempio l'elenco
  dei comandi da coprire o l'helper comune degli errori), oppure lo ordina
  dopo la traduzione centralizzata degli errori.

## Changes

- `cli.py`: opzione `--project` comune; traduzione centralizzata di eccezioni
  d'uso e di I/O in messaggi ed exit code.
- `shell/project.py`: errori "no .lasagna/ found", "not a directory".
- Messaggi del §8.11 mancanti nei singoli comandi.
- Test parametrizzati sulla tabella §8.11, su `--project` per ogni comando e
  con stdin chiuso.
- Riga in `CHANGELOG.md` sotto Unreleased.

## Files involved

- `src/lasagna/cli.py`, `src/lasagna/shell/project.py`, `src/lasagna/shell/run.py`
- `src/lasagna/core/validate.py` (solo per `validate <id>`)
- `tests/e2e/`

## Tests to pass

<!-- Filled in by the implementation pipeline (node contract) as a checklist:
one line per planned verification, in order. The green node checks off a test
with `[x] (green after N)`; the review node checks off checks and reviews. -->

## Contract

<!-- Filled in by the implementation pipeline (node contract), from its
contract template. -->

## Out of scope

- Nuovi comandi o opzioni non elencati nel §8.
- Pipeline incluse e README: ticket 12 e 13.

## Definition of done

- [ ] every criterion has the verification the spec asks for: a test that fails on a plausible wrong implementation, a passing check, or a recorded review
- [ ] whole suite green
- [ ] changelog line under Unreleased
- [ ] traceability evidence filled in the tickets index; current file updated

## Log

<!-- One line per session: date | outcome | cycles used per criterion | summary of the [lasagna] lines | notes -->
