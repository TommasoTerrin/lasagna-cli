# Architettura e convenzioni — lasagna v3

Il file di architettura del progetto, letto dalle pipeline (`architecture_file`).
Dettagli del layout: `docs/specs/v3.0.0.md` §9.

## Livello di separazione

**Modulare** (guida: `src/lasagna/builtin/project-manager/assets/architecture-guide.md`).

- `src/lasagna/core/`: **puro**. Riceve dati, restituisce dati. Niente `os`,
  `subprocess`, `shutil`, `socket`, `random`, niente `open()`, niente orologio,
  niente variabili d'ambiente, niente import da `lasagna.shell`. Librerie ammesse:
  standard library e `pydantic`. (AC-V3-022 lo verifica.)
- `src/lasagna/shell/`: I/O (file system, git, esecuzione di comandi, ambiente).
  Sottile: raccoglie i fatti, chiama il core, applica.
- `src/lasagna/cli.py`: solo parsing con `typer` e chiamate alla shell.
- Organizzazione per funzionalità dentro `core/` (validate, render, graph,
  view…), nomi di file che dicono il comportamento.

## Convenzioni

- **Errori:** la validazione non solleva eccezioni ma restituisce liste di
  `Finding` (`rule`, `file`, `path`, `message`, livello). Le eccezioni sono per
  errori d'uso e di I/O, tradotte in messaggi ed exit code dalla CLI (0 ok, 1
  contenuto, 2 uso).
- **YAML:** `ruamel.yaml` in round-trip quando la CLI riscrive file
  dell'utente; mai PyYAML.
- **Path:** `pathlib`; nei file YAML sempre `/`.
- **Tipi:** annotazioni ovunque; modelli `pydantic` v2 con `extra="forbid"`
  (le chiavi `x-*` sono gestite esplicitamente).
- **Lingua:** codice, docstring, messaggi in inglese.

## Test

- `tests/core/`: unit test senza mock, solo valori.
- `tests/shell/`: `tmp_path`, niente rete.
- `tests/e2e/`: `typer.testing.CliRunner` su progetti di prova in `tmp_path`.
- Il criterio della spec va in un commento accanto al test: `# AC-V3-NNN`.

## Comandi

Ambiente e dipendenze con `uv` (crea `.venv/` da solo):

```bash
uv sync
uv run pytest
uv run ruff check
uv run lasagna --version
```

Lo scaffold minimo (`pyproject.toml`, `src/lasagna/__init__.py`,
`tests/test_smoke.py`, `.python-version`, `uv.lock`) esiste già dal bootstrap
M0 (spec §11.2.1, P25), così il primo `red` fallisce per la ragione giusta. Lo
script `lasagna`, `--version`, le dipendenze e la CI arrivano con il primo
ticket (M1).
