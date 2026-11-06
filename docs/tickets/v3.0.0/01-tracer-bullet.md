---
status: todo            # todo | in_progress | done | blocked
depends_on: []          # ticket numbers
criteria: [AC-V3-001, AC-V3-002, AC-V3-003, AC-V3-004, AC-V3-022]
---

# 01 — Tracer bullet: script `lasagna`, `--version`, `validate` minimo, CI

The `status` above is the only record of this ticket's state: the tickets index
and the current file never copy it.

## Goal

`uv run lasagna --version` e `uv run lasagna validate` funzionano da capo a
fondo su un progetto con una pipeline minima: CLI → shell → core → messaggio ed
exit code. La CI gira, e un test garantisce la purezza di `core/` dal primo
modulo.

## Context

- Milestone M1 della spec (§12): la via più sottile attraverso tutti gli strati.
- Spec §9.1 (layout), §9.2 (requisiti, CI), §8 (regole comuni dei comandi),
  §8.2 (`validate`), §8.10 (`--version`), §5 (V01, V05, V06 e formato dei
  messaggi: file, percorso YAML, ID della regola, correzione).
- Lo scaffold di M0 esiste già (`pyproject.toml` senza dipendenze né script,
  `src/lasagna/__init__.py`, `tests/test_smoke.py`): spec §11.2.1.4.
- Modelli **essenziali**: quanto basta per registry e pipeline minime (id,
  path, nodi, archi `direct`, entry). Il modello completo è del ticket 02.
- `docs/architecture.md`: `core/` puro, `Finding` al posto delle eccezioni,
  `ruamel.yaml`, exit code 0/1/2.
- **Rischio di red che passa subito (AC-V3-022):** con `core/` vuoto il test
  di purezza passa a vuoto. Il contratto lo ordina dopo il primo modulo di
  `core/`, o lo fa passare da un nome dichiarato nel contratto che ancora non
  esiste.
- **AC-V3-004 (check):** l'evidenza è un run della CI su GitHub, che richiede
  un push approvato dal maintainer; in locale si verifica solo la sintassi del
  workflow.
- **Da chiedere al maintainer prima di iniziare (spec §14.4):** la protezione
  di `main` va attivata insieme alla CI; è un'azione del maintainer su GitHub,
  non di questo ticket.

## Changes

- `pyproject.toml`: dipendenze `typer`, `pydantic>=2`, `ruamel.yaml`; script
  `lasagna = "lasagna.cli:app"`; `uv.lock` aggiornato.
- `src/lasagna/__init__.py`: `__version__` e `PROTOCOL_VERSION = "3.0"`.
- `src/lasagna/cli.py`: app typer con `--version` e `validate`.
- `src/lasagna/core/models.py` (essenziale), `core/validate.py` (V01, V05,
  V06), tipo `Finding`.
- `src/lasagna/shell/project.py`: ricerca della radice (`.lasagna/` salendo),
  lettura YAML con posizioni per il percorso dei messaggi.
- `.github/workflows/ci.yml`: `ruff check` + `pytest`, Python 3.11 e 3.15,
  Ubuntu e Windows.
- Test di purezza di `core/` via AST (AC-V3-022).
- Riga in `CHANGELOG.md` sotto Unreleased (chiusura).

## Files involved

- `pyproject.toml`, `uv.lock`
- `src/lasagna/__init__.py`, `src/lasagna/cli.py`
- `src/lasagna/core/__init__.py`, `src/lasagna/core/models.py`, `src/lasagna/core/validate.py`
- `src/lasagna/shell/__init__.py`, `src/lasagna/shell/project.py`
- `.github/workflows/ci.yml`
- `tests/core/`, `tests/shell/`, `tests/e2e/` (nuovi), `tests/test_smoke.py`

## Tests to pass

<!-- Filled in by the implementation pipeline (node contract) as a checklist:
one line per planned verification, in order. The green node checks off a test
with `[x] (green after N)`; the review node checks off checks and reviews. -->

## Contract

<!-- Filled in by the implementation pipeline (node contract), from its
contract template. -->

## Out of scope

- Modello completo, chiavi `x-*`, JSON Schema, auto-validazione di `.lasagna/`
  di questo repo: ticket 02.
- Regole V diverse da V01, V05, V06; `--json`; `--strict`: ticket 03 e 06.
- `--project` e la tabella degli errori §8.11: ticket 11.
- Protezione del branch `main`: azione del maintainer.

## Definition of done

- [ ] every criterion has the verification the spec asks for: a test that fails on a plausible wrong implementation, a passing check, or a recorded review
- [ ] whole suite green
- [ ] changelog line under Unreleased
- [ ] traceability evidence filled in the tickets index; current file updated

## Log

<!-- One line per session: date | outcome | cycles used per criterion | summary of the [lasagna] lines | notes -->
