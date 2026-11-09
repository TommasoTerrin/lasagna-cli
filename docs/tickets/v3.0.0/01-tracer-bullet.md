---
status: done            # todo | in_progress | done | blocked
depends_on: []          # ticket numbers
criteria: [AC-V3-001, AC-V3-002, AC-V3-003, AC-V3-022]
---

# 01 — Tracer bullet: script `lasagna`, `--version`, `validate` minimo

The `status` above is the only record of this ticket's state: the tickets index
and the current file never copy it.

## Goal

`uv run lasagna --version` e `uv run lasagna validate` funzionano da capo a
fondo su un progetto con una pipeline minima: CLI → shell → core → messaggio ed
exit code. Un test garantisce la purezza di `core/` dal primo modulo.

## Context

- Milestone M1 della spec (§12): la via più sottile attraverso tutti gli strati.
- Spec §9.1 (layout), §9.2 (requisiti), §8 (regole comuni dei comandi),
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
- **CI rinviata alla 3.0.1** (decisione del maintainer, 2026-11-06): AC-V3-004
  è ritirato dalla 3.0.0, niente `.github/workflows/ci.yml` in questo ticket.
  Anche la protezione di `main` (spec §14.4) è rinviata. Nessuna domanda da
  fare prima di iniziare.

## Changes

- `pyproject.toml`: dipendenze `typer`, `pydantic>=2`, `ruamel.yaml`; script
  `lasagna = "lasagna.cli:app"`; `uv.lock` aggiornato. **Fatto nel nodo
  `contract`** (non pilotabile da un test, e senza dipendenze il primo `red`
  fallirebbe per la ragione sbagliata): `uv add typer "pydantic>=2" ruamel.yaml`
  più la voce `[project.scripts]`.
- `src/lasagna/__init__.py`: `__version__` e `PROTOCOL_VERSION = "3.0"` esistono
  già dallo scaffold M0: nessuna modifica prevista.
- `src/lasagna/cli.py`: app typer con `--version` e `validate`.
- `src/lasagna/core/models.py` (essenziale), `core/validate.py` (V01, V05,
  V06), tipo `Finding`.
- `src/lasagna/shell/project.py`: ricerca della radice (`.lasagna/` salendo),
  lettura YAML (riga e colonna solo per gli errori di sintassi).
- Test di purezza di `core/` via AST (AC-V3-022).
- Riga in `CHANGELOG.md` sotto Unreleased (chiusura).

## Files involved

- `pyproject.toml`, `uv.lock`
- `src/lasagna/__init__.py`, `src/lasagna/cli.py`
- `src/lasagna/core/__init__.py`, `src/lasagna/core/models.py`, `src/lasagna/core/validate.py`
- `src/lasagna/shell/__init__.py`, `src/lasagna/shell/project.py`
- `tests/core/`, `tests/shell/`, `tests/e2e/` (nuovi), `tests/test_smoke.py`

## Tests to pass

<!-- Filled in by the implementation pipeline (node contract) as a checklist:
one line per planned verification, in order. The green node checks off a test
with `[x] (green after N)`; the review node checks off checks and reviews. -->

Regola per questo ticket (maintainer, 2026-11-09): se un test pianificato passa
subito perché l'implementer ha già scritto quel comportamento in un ciclo
precedente, lo spunto con la nota `passes immediately` e proseguo senza
fermarmi; mi fermo solo se passa un test che non era previsto, o se il test
non verifica nulla. L'elenco va nel Log di chiusura.

Un test per riga, nell'ordine. Il test di purezza è **primo** di proposito
(vedi Contract › What is NOT frozen): è l'unico ordine in cui il suo red è
onesto, perché pretende che i moduli dichiarati `models` e `validate` esistano;
poi il tracer end-to-end.

- [x] (green after 1) AC-V3-022 · `tests/core/test_purity.py`: `core/` si localizza con
  `Path(lasagna.__file__).parent / "core"` (non importando `lasagna.core`);
  ogni `*.py` lì dentro, `__init__.py` compreso, è pulito per l'AST (nessun
  `import os`, `import os.path`, `from os import ...`, né lo stesso per
  `subprocess`, `shutil`, `socket`, `random`; nessun `from lasagna.shell...`,
  `from lasagna import shell`, `import lasagna.shell`; nessuna chiamata al nome
  `open()`; anche gli import relativi della shell: `from ..shell import x`,
  `from . import shell`; la scansione è basata sull'AST); l'insieme dei moduli scansionati contiene `models.py` e
  `validate.py` (se la cartella o i moduli mancano è un'asserzione che fallisce,
  non un'eccezione); nessun file di
  `tests/core/` importa `unittest.mock`, `from unittest import mock`, `mock` o
  `pytest_mock`, né ha una funzione di test con un parametro chiamato
  `monkeypatch` o `mocker` (controllo AST: il file stesso nomina questi
  simboli solo in stringhe).
- [x] (green after 1) AC-V3-003 (tracer) · `tests/e2e/test_validate.py`: progetto valido minimo
  (1 pipeline, 2 nodi, 1 arco `direct`) → `validate` esce 0.
- [x] (green after 1) AC-V3-003 · e2e: arco `direct` con `to` inesistente → exit 1; l'output
  contiene `V06`, il file `.lasagna/pipelines/<id>/pipeline.yaml` e il percorso
  `edges[0].to`.
- [x] (green after 1) AC-V3-002 · `tests/e2e/test_version.py`: `--version` → exit 0, l'output
  contiene `lasagna.__version__` (letto dal pacchetto, non hard-coded) e
  `lasagna.PROTOCOL_VERSION`; il test asserisce anche `PROTOCOL_VERSION == "3.0"`.
- [x] (passes immediately, accepted by the maintainer: `from` and `to` were implemented together in cycle 3) AC-V3-003 · `tests/core/test_validate_v06.py`: `validate_project` → `[]`
  su un progetto valido; un `from` inesistente dà esattamente un `Finding` V06 con
  `path == "edges[N].from"` (N diverso da 0).
- [x] (passes immediately, accepted by the maintainer: V06 iterates every edge in cycle 3) AC-V3-003 · `tests/core/test_validate_v06.py`: un `to` inesistente dà un
  `Finding` V06 con `path == "edges[N].to"`; due archi sbagliati danno due
  finding, uno per arco, con i rispettivi indici.
- [x] (green after 1) V05 · `tests/core/test_validate_v05.py`: voce con `pipelines[path] is
  None` → V05 su `pipelines[i].path` (file del registry).
- [x] (green after 1) V05 · `tests/core/test_validate_v05.py`: id del registry ≠ id del
  `pipeline.yaml` → V05 su `pipelines[i].id` con entrambi gli id nel messaggio.
- [x] (green after 1) V05 · `tests/core/test_validate_v05.py`: chiave assente da `pipelines` →
  nessun finding per quella voce.
- [x] (green after 1) V01 · `tests/core/test_validate_v01.py`: chiave sconosciuta nel registry
  → V01 sul file del registry con il percorso della chiave (es.
  `pipelines[0].bogus`).
- [x] (green after 1) V01 · `tests/core/test_validate_v01.py`: chiave sconosciuta o tipo errato
  in una pipeline → V01 sul file della pipeline, uno per errore.
- [x] (passes immediately, accepted by the maintainer: registry-invalid short-circuit implemented with the registry V01 in cycle 9) V01 · `tests/core/test_validate_v01.py`: radice che non è un mapping →
  V01 con `path == ""`; registry non valido → solo finding del registry
  (nessun V05/V06).
- [x] (passes immediately, accepted by the maintainer: find_project_root exists from the tracer cycle; the `None` branch is covered by the e2e line below) shell · `tests/shell/test_project.py`: `find_project_root` risale da una
  sottocartella annidata, ritorna la cartella più vicina che contiene
  `.lasagna/` (uguale a `tmp_path` o al suo sottopercorso, così com'è passato:
  nessun `resolve()`), e `None` se non ce n'è.
- [x] (passes immediately, accepted by the maintainer: happy-path loading exists from the tracer cycle) shell · `tests/shell/test_project.py`: `load_project` legge registry e
  pipeline in `tmp_path` (`registry_loaded`, `registry`, `pipelines` col YAML
  caricato); `pipeline.yaml` mancante → valore `None` e `findings` vuoto.
- [x] (green after 1) shell · `tests/shell/test_project.py`: YAML malformato → finding V01 sul
  file giusto con `line <n>` nel messaggio, con `n = problem_mark.line + 1`
  (fixture in tre righe, `a: 1` / `b: [1, 2` / `c: 3`, con newline finale →
  `line 3`) e la pipeline assente da `pipelines`.
- [x] (green after 1) shell · `tests/shell/test_project.py`: `pipeline.yaml` vuoto (solo
  commenti o niente) → V01 sul file, "empty" nel messaggio, pipeline assente da
  `pipelines` (non `None`).
- [x] (green after 1) shell · `tests/shell/test_project.py`: registry mancante →
  `registry_loaded == False` e un finding V01; registry vuoto → stesso esito,
  con "empty" nel messaggio.
- [x] (green after 1) shell · `tests/shell/test_project.py`: registry YAML valido ma non un
  mapping (lista, scalare) → `registry_loaded == True`, `registry` = il valore,
  `pipelines == {}`, nessuna eccezione, `findings == ()` (lo segnala il core con
  V01 `path == ""`). Aggiunto nel ciclo 14: il contratto lo impone ma nessuna
  riga lo copriva.
- [x] (green after 1) shell · `tests/shell/test_project.py`: registry che è un mapping ma con
  `pipelines` malformato → il loader non solleva e carica solo le voci che sono
  mapping con `path: str`: con `pipelines: "oops"` → `pipelines == {}`; con
  voci `[1, {"id": "x"}, {"id": "d", "path": "pipelines/d"}]` (l'ultima con un
  file valido) → solo la chiave `"pipelines/d"`; `findings == ()` (il core dà i
  V01). Aggiunto nel ciclo 15 dalla nota dell'implementer: il contratto lo
  impone (Return shape di `load_project`) ma nessuna riga lo copriva.
- [x] (passes immediately, accepted under the ticket rule: exit-2 branch written in the tracer cycle; guard did not trigger on this machine) e2e · `validate` senza `.lasagna/` salendo dalla cartella corrente → exit
  2 e l'output nomina `.lasagna/`. Guardia di ermeticità (maintainer, 2026-11-09):
  il test salta (`pytest.skip` con messaggio) se un antenato di `tmp_path` ha una
  cartella `.lasagna/`; lo stesso vale per qualunque asserzione `None` di
  `find_project_root`, che vive solo in questo test.
- [x] (passes immediately, accepted under the ticket rule; mutation-checked: a cli ignoring data.findings fails both cases, a cli running validate_project on an unloaded registry fails `no_registry`) e2e (aggiunta dalla review) · `tests/e2e/test_validate.py`: i finding di
  caricamento contano per l'exit code: (a) `pipeline.yaml` malformato → exit 1,
  l'output contiene `V01` e `.lasagna/pipelines/<id>/pipeline.yaml`; (b)
  `.lasagna/` senza `pipelines.yaml` → exit 1 e **una sola** riga `V01`
  nell'output (il core non deve girare sul registry non caricato).
- [x] (passes immediately, accepted under the ticket rule; mutation-checked: dropping the level or the colon fails it) core (aggiunta dalla review) · `tests/core/test_format_finding.py`:
  `format_finding` produce esattamente `"<level> <rule> <file> <path>:
  <message>"`, e con `path` vuoto `"<level> <rule> <file>: <message>"` (valori
  letterali, un `Finding` costruito nel test).
- [x] (passes immediately, accepted under the ticket rule; mutation-checked: `--version` printing only `lasagna <version>` fails it) AC-V3-002 (aggiunta dalla review, 2° giro) · `tests/e2e/test_version.py`:
  l'output di `--version` è esattamente `lasagna <__version__> (protocol
  <PROTOCOL_VERSION>)` (con `
` finale), non una semplice presenza delle due
  stringhe: `__version__` (`3.0.0.dev0`) contiene già `3.0`. Mutante da
  uccidere: `--version` che stampa solo `lasagna 3.0.0.dev0`.
- [x] (passes immediately, accepted under the ticket rule; mutation-checked: `import os` in `core/sub/x.py` → `core must stay pure: {'core/sub/x.py': ['import os']}`) AC-V3-022 (aggiunta dalla review, 2° giro) · `tests/core/test_purity.py`:
  la scansione di `core/` è ricorsiva (`rglob`): un `import os` in
  `core/sub/x.py` viene visto. Mutante da uccidere: file impuro in un
  sottopacchetto.
- [x] (evidence: clean copy of tracked+new files without .venv, 2026-11-09: `uv sync` ok; `uv run pytest` 33 passed; `uv run lasagna --version` → `lasagna 3.0.0.dev0 (protocol 3.0)`, exit 0; pyproject has `[project.scripts] lasagna = "lasagna.cli:app"` and `requires-python = ">=3.11"`) AC-V3-001 (check) · in una copia pulita dell'albero (file tracciati e
  nuovi, senza `.venv/`): `uv sync && uv run pytest && uv run lasagna
  --version` escono 0; `pyproject.toml` contiene `[project.scripts]`,
  `lasagna = "lasagna.cli:app"` e `requires-python = ">=3.11"`.
- [x] (evidence: `import os` added to core/validate.py → test_purity fails with `core must stay pure: {'core/validate.py': ['import os']}`; `open()` call added to core/models.py → fails; both reverted, suite 33 passed) AC-V3-022 (review) · mutazione: aggiungere temporaneamente `import os` a
  `core/validate.py` fa fallire il test di purezza; poi ripristinare.
- [x] (evidence: `uv run ruff check` → All checks passed!) check (nessun AC) · `uv run ruff check` pulito (la CI è rinviata alla 3.0.1).

## Contract

<!-- Filled in by the implementation pipeline (node contract), from its
contract template. -->

### Seams

Tre livelli, nessuno più in basso:
- **CLI:** `typer.testing.CliRunner().invoke(lasagna.cli.app, [...])`, con la
  cartella corrente impostata su un progetto di prova in `tmp_path`
  (`monkeypatch.chdir`). Si asserisce su `exit_code` e su `result.output`
  (quale stream, stdout o stderr, **non è congelato**: lo decide il ticket 03).
- **Core:** `lasagna.core.validate.validate_project` (dati in, `Finding` fuori).
- **Shell:** `lasagna.shell.project.find_project_root` e `load_project`.

### Signatures

```python
# src/lasagna/__init__.py (esistono già)
__version__: str
PROTOCOL_VERSION: str            # "3.0"

# src/lasagna/core/models.py
@dataclass(frozen=True)
class Finding:
    rule: str                    # "V01" | "V05" | "V06" in questo ticket
    file: str                    # percorso relativo alla radice del progetto, con "/"
    path: str                    # percorso YAML, es. "edges[0].to"; "" se riguarda tutto il file
    message: str                 # problema + frase di correzione, in inglese, non vuoto
    level: Literal["error", "warning"] = "error"

# modelli pydantic v2 con extra="forbid" (essenziali; il modello completo è del ticket 02)
class RegistryEntry(BaseModel):  # id: str, path: str (relativo a `.lasagna/`, es. "pipelines/demo"), enabled: bool = True
class Registry(BaseModel):       # lasagna: str, project: str | None = None,
                                 # agent_can_edit_pipelines: bool = False,
                                 # pipelines: list[RegistryEntry] = []
class Node(BaseModel):           # id: str, name: str | None = None, description: str | None = None
class Edge(BaseModel):           # type: Literal["direct"], from_: str (alias "from"), to: str;
                                 # populate_by_name=True
class Pipeline(BaseModel):       # lasagna: str, id: str, entry: str, nodes: list[Node],
                                 # edges: list[Edge] = [], name/description/version: str | None = None

# src/lasagna/core/validate.py
REGISTRY_FILE: str = ".lasagna/pipelines.yaml"

def pipeline_file(entry_path: str) -> str: ...
    # f".lasagna/{entry_path}/pipeline.yaml"

def validate_project(
    registry: object,                        # YAML già caricato di pipelines.yaml
    pipelines: Mapping[str, object | None],  # chiave = `path` della voce, come scritto nel registry
) -> list[Finding]: ...

def format_finding(finding: Finding) -> str: ...
    # "<level> <rule> <file> <path>: <message>"; con path vuoto: "<level> <rule> <file>: <message>"

# src/lasagna/shell/project.py
@dataclass(frozen=True)
class ProjectData:
    root: Path
    registry_loaded: bool
    registry: object | None
    pipelines: dict[str, object | None]
    findings: tuple[Finding, ...]            # solo problemi di caricamento: YAML malformato, file vuoto, registry mancante o vuoto
                                             # (un `pipeline.yaml` mancante NON è un finding: lo segnala V05 nel core)

def find_project_root(start: Path) -> Path | None: ...
def load_project(root: Path) -> ProjectData: ...

# src/lasagna/cli.py
app: typer.Typer                 # un gruppo (con callback per `--version`) e il comando `validate`:
                                 # `lasagna validate` e `lasagna --version` funzionano entrambi
```

L'implementer non cambia nomi, parametri né tipi.

### Data types

- `Finding` è immutabile. `file` usa sempre `/`, anche su Windows. `message` non
  è mai vuoto e contiene una frase di correzione dopo il problema.
- Percorsi YAML: chiavi con `.`, indici con `[n]` a base 0 (`pipelines[0].id`,
  `edges[1].from`, `nodes[2].id`). Per un errore pydantic il percorso è la
  `loc` convertita; per una chiave sconosciuta include la chiave. Un finding V01
  per ogni errore pydantic (non uno per file).
- `Edge.type` diverso da `direct`: in questo ticket un arco `loop` o
  `router` è V01 (tipo sconosciuto al modello essenziale). Limite noto e
  temporaneo: la validazione del `.lasagna/` di questo repo è del ticket 02.
- `pipelines` (argomento): `None` = la cartella o il `pipeline.yaml` non
  esistono; chiave **assente** = già segnalata dal caricamento, il core la salta
  in silenzio.
- Modo pydantic predefinito (lax), nessuna coercione in più: `lasagna: str` rifiuta
  un `3.0` senza virgolette (float) con V01; le fixture dei test quotano
  `lasagna: "3.0"`.
- Chiavi `x-*`: in questo ticket sono V01 (`extra="forbid"`), come `loop` e
  `router`; la spec §5 le ammette, lo sistema il ticket 02. Non si testano.
- File YAML **vuoto** (nessun contenuto, o solo commenti): per il caricamento è
  come un file malformato: finding V01 con "empty" nel messaggio, non è `None`.
  `None` in `pipelines` significa solo "il file non esiste".
- I file sono letti come UTF-8, YAML con `ruamel.yaml` (loader sicuro, tipi
  semplici in uscita: `dict`, `list`, `str`, ...).

### Error types

Stile del progetto: la validazione non solleva, restituisce `Finding`.

| Caso | Esito |
|---|---|
| Regola V01 (YAML malformato, chiave sconosciuta, tipo errato, radice non mapping) | `Finding` V01 |
| V05: `pipelines[path] is None` | `Finding` V05, file = registry, path = `pipelines[i].path` |
| V05: id del registry ≠ id della pipeline | `Finding` V05, file = registry, path = `pipelines[i].id`, messaggio con entrambi gli id |
| V06: `from` o `to` non è un id di nodo | `Finding` V06, file = `pipeline_file(path)`, path = `edges[j].from` / `edges[j].to` |
| Nessun `.lasagna/` salendo dalla cartella corrente | `find_project_root` → `None`; la CLI esce 2 con un messaggio che nomina `.lasagna/` (una riga della tabella §8.11; il resto è del ticket 11) |
| Errori di I/O (permessi, codifica) | non congelati: fuori scope (ticket 11) |

Regole di composizione di `validate_project`:
1. Se `registry` non passa il modello `Registry`: solo finding V01 del registry
   (file = `REGISTRY_FILE`), nessun'altra regola.
2. Altrimenti, per ogni voce nell'ordine del registry (anche `enabled: false`):
   chiave assente in `pipelines` → salta; valore `None` → V05 sul `path`; altrimenti la
   pipeline passa il modello `Pipeline`: se no, finding V01 con
   `file = pipeline_file(path)` e nessun V05-id né V06 per quella pipeline; se sì,
   V05-id e poi V06 sugli archi.

### Return shape

- `validate_project` → `list[Finding]`; `[]` se tutto è valido. L'ordine tra
  finding non è congelato: i test filtrano per `rule`/`path`.
- `load_project(root)` → `ProjectData`: `root` = l'argomento; `registry` il
  YAML caricato (`None` se non caricato); `pipelines` ha una chiave per ogni
  voce del registry che sia un mapping con `path: str`, con il YAML caricato, o
  `None` se `<root>/.lasagna/<path>/pipeline.yaml` non esiste, o nessuna chiave
  se il file esiste ma è malformato (e `findings` ha un V01 con `file` giusto e
  `line <n>` nel messaggio, con `n = problem_mark.line + 1` dell'eccezione
  ruamel, non `context_mark`). Registry mancante o malformato →
  `registry_loaded=False`, `registry=None`, `pipelines={}`, un V01 (vale anche
  per un registry vuoto).
- Registry che è YAML valido ma non un mapping (lista, scalare):
  `registry_loaded=True`, `registry` = il valore, `pipelines={}`; il core dà un V01
  con `path == ""`.
- `find_project_root(start)` → la prima cartella tra `start` e i suoi genitori
  che contiene una **cartella** `.lasagna`, altrimenti `None`.
- CLI `validate`: stampa ogni finding con `format_finding` (una riga ciascuno);
  se non ce ne sono errori stampa una riga di conferma (testo libero); exit 0 se
  nessun finding di livello `error`, 1 altrimenti, 2 se manca `.lasagna/`.
  Sequenza: `find_project_root(Path.cwd())` → `load_project` → se
  `registry_loaded`, `validate_project` → unione dei finding (caricamento
  prima). L'output si scrive con `typer.echo` su testo semplice (niente rich né
  markup, niente a capo automatici: i percorsi restano interi). `lasagna --version` stampa `lasagna <__version__> (protocol
  <PROTOCOL_VERSION>)` ed esce 0.

### External dependencies

| Dependency | How the code reaches it | How tests control it |
|---|---|---|
| File system (registry, pipeline) | solo `shell/project.py` (`pathlib`, UTF-8) | `tmp_path` con file scritti dal test |
| Cartella corrente | `Path.cwd()` solo in `cli.py` | `monkeypatch.chdir(tmp_path)` nei test e2e; `find_project_root` riceve `start` esplicito |
| Parsing YAML | `ruamel.yaml` solo in `shell/project.py` | file veri in `tmp_path`; nessun mock |
| stdout/stderr, exit code | typer | `CliRunner` |
| Versioni | costanti `lasagna.__version__`, `lasagna.PROTOCOL_VERSION` | lette dal pacchetto nel test |
| Orologio, rete, variabili d'ambiente, casualità | non usati | — |
| Sorgenti di `core/` (test di purezza) | `Path(lasagna.__file__).parent / "core"` | letti dal file system reale, parsati con `ast`; nessun mock |

### What is NOT frozen

- Quale stream (stdout o stderr) riceve i finding e la conferma; il testo
  della conferma; la formulazione esatta di `message` oltre a "non vuoto, con
  correzione"; l'ordine dei finding; i nomi privati e la divisione in funzioni
  interne; i messaggi di `--help`; la struttura di typer (callback, comandi).
- **Perché il test di purezza è primo (e non il tracer):** con `core/` vuoto un
  test di purezza passerebbe a vuoto, ma non appena esiste un modulo il suo red
  passerebbe subito e il nodo `red` si bloccherebbe (la riga "il test passa
  subito"). Il contratto lo risolve col nome dichiarato: il test pretende che
  `models.py` e `validate.py` esistano, quindi fallisce per asserzione sui
  moduli mancanti; il suo green è la creazione di `core/__init__.py`,
  `core/models.py` e `core/validate.py` come scheletri: `models.py` contiene
  solo `Finding`, `validate.py` solo il docstring del modulo. I test seguenti li riempiono. Da qui in poi la scansione
  copre ogni modulo e ogni test di `core/` aggiunto.
- Gli scheletri non anticipano logica: i test seguenti portano ciascuno la
  propria. Il test di purezza non importa `lasagna.core`: localizza i file dal
  pacchetto `lasagna`, così il suo red è un'asserzione sui moduli mancanti.

## Out of scope

- Modello completo, chiavi `x-*`, JSON Schema, auto-validazione di `.lasagna/`
  di questo repo: ticket 02.
- Regole V diverse da V01, V05, V06; `--json`; `--strict`: ticket 03 e 06.
- `--project` e la tabella degli errori §8.11: ticket 11.
- CI (`.github/workflows/ci.yml`) e protezione del branch `main`: 3.0.1.

## Definition of done

- [x] every criterion has the verification the spec asks for: a test that fails on a plausible wrong implementation, a passing check, or a recorded review
- [x] whole suite green (34 passed, `uv run ruff check` clean)
- [x] changelog line under Unreleased
- [x] traceability evidence filled in the tickets index; current file updated

## Log

<!-- One line per session: date | outcome | cycles used per criterion | summary of the [lasagna] lines | notes -->

2026-11-09 | done | every planned test green after 1 attempt; review→red used 2 of 2 (round 1: loading findings vs exit code and `format_finding` format; round 2: `--version` exact output and recursive purity scan) | contract (gate failed 3 times on contract ambiguities, passed on the 4th) → red/green ×22 cycles → review (fail ×2, pass) → close | CI/main protection moved out of this ticket to 3.0.1 (maintainer, 2026-11-06). Tests accepted although they passed immediately (ticket rule, all mutation-checked unless noted): V06 on `from`, V06 on `to` with two bad edges, V01 registry-invalid short-circuit, `find_project_root`, `load_project` happy path, e2e exit 2, loading findings vs exit code, `format_finding`, exact `--version`, recursive purity scan. Open gaps (not blocking): purity detector only exercised on `import os` snippets (relative-import and other forbidden forms are unproven against synthetic input), `__init__.py` skip and no-mock check lack synthetic positive tests, `[project.scripts]` wiring covered only by the AC-V3-001 check. Production code written ahead of its test by the implementer: `format_finding`, the exit-2 branch, V06 on `from` (reviewed).
