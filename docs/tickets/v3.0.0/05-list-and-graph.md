---
status: done                   # todo | in_progress | done | blocked
depends_on: ["02"]      # ticket numbers
criteria: [AC-V3-020, AC-V3-021]
---

# 05 — `lasagna list` e `lasagna graph`

The `status` above is the only record of this ticket's state: the tickets index
and the current file never copy it.

## Goal

`list` mostra le pipeline abilitate del progetto (`--all` anche le
disabilitate, `--builtin` quelle incluse nel pacchetto); `graph` produce il
diagramma Mermaid del §8.5, uguale a uno snapshot committato.

## Context

- Milestone M3 (§12), seconda parte.
- Spec §8.3 (`list`: id, versione, descrizione, `started_by` del nodo
  iniziale), §8.5 (forme per `started_by`, simboli `[H]`/`[C]`/`[A]`, stili
  degli archi).
- `shell/builtin.py` nasce qui (lettura delle pipeline incluse nel pacchetto,
  per `--builtin`); il ticket 09 lo riusa per `add builtin:`.
- `core/mermaid.py` è puro: riceve il modello, restituisce testo.

## Changes

- `core/view.py`: vista di `list` (markdown e `--json`).
- `core/mermaid.py`: generazione del diagramma.
- `shell/builtin.py`: elenco e lettura delle pipeline incluse.
- `cli.py`: comandi `list` e `graph` (`--output <file>`).
- Snapshot di testo del diagramma di una pipeline di prova.
- Riga in `CHANGELOG.md` sotto Unreleased.

## Files involved

- `src/lasagna/core/view.py`, `src/lasagna/core/mermaid.py`
- `src/lasagna/shell/builtin.py`, `src/lasagna/cli.py`
- `tests/core/`, `tests/e2e/`, snapshot sotto `tests/`

## Tests to pass

<!-- Filled in by the implementation pipeline (node contract) as a checklist:
one line per planned verification, in order. The green node checks off a test
with `[x] (green after N)`; the review node checks off checks and reviews. -->

Convenzioni: ogni test cita il criterio in un commento `# AC-V3-NNN`; `tests/core/`
senza mock né `monkeypatch`; e2e con `CliRunner` su progetti in `tmp_path`; test portabili
Windows/Linux. Regola del passa-subito come nei ticket 02–04: una riga che passa subito
perché il comportamento esiste già si spunta `passes immediately` solo se ha accanto
`(passa-subito atteso: Mnn)` ed è verificata da quella mutazione; negli altri casi mi fermo.

**AC-V3-020 (`list`)** — fixture e2e: progetto con `alpha` (abilitata, entry `human`,
versione 1.0.0, descrizione non ASCII con `|`), `beta` (disabilitata, entry `agent`) e
`gamma` (abilitata, senza `version`).
- [x] (green after 1) T01 e2e, tracer: `list` mostra `alpha` e `gamma` nell'ordine del registry e non `beta`; exit 0.
- [x] (green after 1) T02 e2e: `list --all` mostra anche `beta` con il marcatore `(disabled)`; le altre righe non lo hanno.
- [x] (green after 1) T03 e2e: `list --builtin` stampa esattamente gli id `implementation`, `project-manager`, `quick-fix`, ordinati, dentro un progetto con altri id (non l'elenco del progetto); nessun valore di versione/descrizione fissato nel test.
- [x] (passes immediately, approvato dal maintainer 2026-11-16: codice anticipato in T01; M01–M07 uccise, vedi Log) T04 core `list_text`: formato esatto (versione `-`, `started_by` `-`, nessuna descrizione, `|` e non ASCII invariati, `(disabled)`, titolo `# Pipelines` / `# Built-in pipelines`, `(none)` se vuoto).
- [x] (green after 1) T05 core `list_json`: forma esatta (`enabled` assente per le incluse, `null` per versione/descrizione/started_by mancanti, `indent=2`, `ensure_ascii=False`, `\n` finale).
- [x] (passes immediately, codice anticipato in T01; regola stabile approvata dal maintainer 2026-11-16; M08–M15 uccise, vedi Log) T06 core `list_item`: descrizione resa con i `params` (override del registry batte il default) `{{ inputs.* }}` lasciato com'è, righe multiple ridotte a una; `started_by` del nodo `entry`; `None` se `entry` manca o non è un nodo.
- [x] (green after 1) T07 e2e: `list --json` e `list --all --json` (`beta` con `enabled: false`); `--builtin --json` senza chiave `enabled`.
- [x] (green after 1) T08 e2e: pipeline illeggibile da mostrare (YAML malformato; `pipeline.yaml` assente; `entry` assente; `entry` che non nomina un nodo) → exit 1, stdout vuoto, finding su stderr; la stessa pipeline disabilitata è ignorata senza `--all` e ferma con `--all`.
- [x] (passes immediately, `_require_root()` anticipato nel green di T03; regola estesa dal maintainer 2026-11-16 ai passa-subito da codice anticipato da un green precedente; M16 uccisa, vedi Log) T09 e2e: `list --builtin` fuori da un progetto → exit 2, messaggio su stderr che nomina `.lasagna/`.
- [x] (passes immediately, `builtin.py` anticipato nel green di T03, regola estesa 2026-11-16; M17, M19–M21 uccise, M18 sopravvive: il filtro `pipeline.yaml` non è verificabile senza una cartella spuria nel pacchetto, rischio per la review) T10 shell `shell/builtin.py`: `builtin_ids()` ordinati e uguali alle cartelle con `pipeline.yaml`; `load_builtin(id)` restituisce un `Pipeline` con quell'`id`; id sconosciuto → `KeyError`.
- [x] (passes immediately, `_force_utf8_stdout()` anticipato nel green di T01, regola estesa 2026-11-16; M22 uccisa) T11 e2e, sottoprocesso reale: `list` con descrizione non ASCII su stdout rediretto esce UTF-8 (Windows compreso).

**AC-V3-021 (`graph`)** — snapshot `tests/snapshots/graph_demo.mmd` scritto a mano dal
contratto (mai generato eseguendo il codice) per la pipeline `tests/snapshots/graph_demo.pipeline.yaml`.
- [x] (green after 1) T12 core, tracer: `pipeline_mermaid` della pipeline di prova è uguale allo snapshot (letto con `read_text(encoding="utf-8")`). La fixture copre: nodi agent e human; gate H, C, A e nessuno; nodo senza `name`; nome con `"` e `[ ]`; archi direct; loop con `when` esplicito e predefinito; router con `when`, con `run` e con `default`; `{{ params.x }}` in un `when`.
- [x] (passes immediately, `pipeline_mermaid` completo nel green di T12, regola estesa 2026-11-16; M23–M25 uccise) T13 core: ogni nodo ha id `n1…nN` nell'ordine del file, anche per id come `end` e `a--b`.
- [x] (passes immediately, codice del green di T12, regola estesa 2026-11-16; M26–M30 uccise) T14 core: un arco direct o loop verso un nodo inesistente è saltato e un nodo senza archi resta presente; con id duplicati gli archi usano il primo.
- [x] (passes immediately, codice del green di T12, regola estesa 2026-11-16; M31–M34 uccise) T15 core: `{{ params.* }}` in `when`/`run` resi con gli override del registry; `{{ inputs.* }}` e `name` non resi.
- [x] (green after 1) T16 e2e: `graph demo` stampa lo snapshot su stdout, exit 0, anche per una pipeline disabilitata.
- [x] (green after 1) T17 e2e: `graph demo --output out.mmd` scrive lo snapshot, UTF-8 e LF (byte-per-byte, anche su Windows), stdout vuoto, sovrascrive un file esistente, percorso relativo alla cartella corrente.
- [x] (green after 1) T18 e2e: `--output` non scrivibile (cartella inesistente) → exit 1, `cannot write <path>: <causa>` su stderr, nessun file creato.
- [x] (green after 1) T19 e2e: id non presente → exit 2, `pipeline '<id>' not in the registry; known: <ids>` su stderr, nessun traceback (sovrapposizione deliberata con la riga di ticket 11, nessuna riscrittura necessaria).
- [x] (green after 1) T20 e2e: pipeline illeggibile o con `entry` non valido → exit 1 come T08, stdout vuoto.
- [x] (passes immediately, `_force_utf8_stdout()` nel comando `graph` del green di T16, regola estesa 2026-11-16; M35 uccisa) T21 e2e, sottoprocesso reale: nome non ASCII su stdout rediretto esce UTF-8.
- [x] (green after 1) T22 e2e: registry illeggibile (`pipelines.yaml` malformato; voce con chiave sconosciuta) → `list` exit 1 e `graph <id qualunque, anche sconosciuto>` exit 1, stdout vuoto, finding del registry su stderr; `list --builtin` con lo stesso registry rotto → exit 0 con le tre incluse.
- [x] (passes immediately, ramo `--builtin` del green di T03, regola estesa 2026-11-16; M36 uccisa) T23 e2e: `list --builtin --all` identico a `list --builtin`.
- [x] (passes immediately, regola estesa 2026-11-16; M37–M40 uccise) T24 core: `pipeline_mermaid` con un router che ha una route e il `default` verso nodi inesistenti: salta solo quelle righe, le altre route restano.

**Chiusura** (non test): suite intera verde, `ruff check`, riga in `CHANGELOG.md`, evidenze nell'indice, `docs/current.md`; nel riepilogo del gate di chiusura va lo snapshot, perché il maintainer lo renda una volta in Mermaid (i test offline provano l'uguaglianza, non la validità).

## Contract

<!-- Filled in by the implementation pipeline (node contract), from its
contract template. -->

Aggiunge ai contratti dei ticket 01–04, che restano validi (modelli, `load_project`,
`ProjectData`, `Finding`, `format_finding`, `validate_project`, `render_text`,
`resolve_params`, `_force_utf8_stdout`). Nessun punto di quei contratti cambia.

Decisioni del maintainer, 2026-11-13: (1) una pipeline **da mostrare** illeggibile fa uscire
`list` con exit 1 e findings su stderr (le disabilitate sono ignorate senza `--all`); (2)
`list --builtin` fuori da un progetto esce 2 come tutti i comandi; (3) P18 solo per
`graph --output`: UTF-8 e LF. P08 (metà `add`) e P19 non sono toccati: `list` e `graph` non
risolvono `$pipeline/` né scrivono nel registry.

### Seams

- **Core:** `lasagna.core.view` (`list_item`, `list_text`, `list_json`, `ListItem`) e
  `lasagna.core.mermaid` (`pipeline_mermaid`), con `Pipeline.model_validate` per costruire l'input.
- **Shell:** `lasagna.shell.builtin` (`builtin_ids`, `builtin_dir`, `load_builtin`) sul pacchetto vero.
- **CLI:** `CliRunner().invoke(lasagna.cli.app, ["list", ...])` e `["graph", ...]`; un sottoprocesso
  reale per la codifica (T11, T21). Nessun test va più in basso.

### Signatures

```python
# src/lasagna/core/view.py   (esteso; puro)
@dataclass(frozen=True)
class ListItem:
    id: str
    version: str | None
    description: str | None      # già resa e ridotta a una riga
    started_by: str | None       # started_by del nodo `entry`; None se entry manca o non nomina un nodo
    enabled: bool | None         # None per le pipeline incluse

def list_item(pipeline: Pipeline, overrides: Mapping[str, str], enabled: bool | None) -> ListItem: ...
def list_text(items: Sequence[ListItem], builtin: bool) -> str: ...
def list_json(items: Sequence[ListItem]) -> str: ...

# src/lasagna/core/mermaid.py   (NUOVO; puro: solo stdlib e lasagna.core.models/render)
def pipeline_mermaid(pipeline: Pipeline, overrides: Mapping[str, str]) -> str: ...

# src/lasagna/shell/builtin.py  (NUOVO; riusato dal ticket 09)
def builtin_ids() -> list[str]: ...          # ordinati; cartelle con pipeline.yaml sotto lasagna/builtin
def builtin_dir(pipeline_id: str) -> Path: ...   # KeyError se sconosciuto
def load_builtin(pipeline_id: str) -> Pipeline: ...  # KeyError se sconosciuto
```

```text
lasagna list [--builtin] [--all] [--json]
lasagna graph <id> [--output <file>]
```

### Data types

`list_item`: `description` = `render_text(pipeline.description, params, {})` con i `params` di
`resolve_params(pipeline, overrides)`, poi `" ".join(testo.split())`; `None` se la pipeline non ha
descrizione. `{{ inputs.* }}` resta come scritto. I `params` sono la mappa `{nome: p.value}` ricavata dai `ResolvedParam` di `resolve_params`, come in `show`. `ListItem.id` = `pipeline.id` (il campo `id` di `pipeline.yaml`). `version` è il campo `version` di
`pipeline.yaml` (non `source.version`).

### Return shape

**`list_text`** (finisce con `\n`; elementi nell'ordine ricevuto):

```text
# Pipelines                         <- `# Built-in pipelines` se builtin=True

- alpha 1.0.0 started_by=human: Descrizione | con barra è è.
- beta 2.0 started_by=agent (disabled): Altro.
- gamma - started_by=-
```

Titolo, riga vuota, poi una riga per elemento: `- <id> <version o "-"> started_by=<started_by o "-">`,
poi ` (disabled)` solo se `enabled is False`, poi `: <description>` solo se la descrizione non è
`None` (una descrizione vuota dà `: `). Elenco vuoto: titolo, riga vuota, `(none)`.

**`list_json`**: `json.dumps(doc, indent=2, ensure_ascii=False) + "\n"` con
`{"pipelines": [{"id", "version", "description", "started_by", "enabled"}, ...]}`; le chiavi in
quest'ordine, `null` per i valori `None`; la chiave `enabled` è **assente** quando `enabled is None`.

**CLI `list`**: stdout = `list_text(...)` o `list_json(...)`, exit 0. Progetto: voci del registry
nell'ordine del file, solo `enabled` (o tutte con `--all`), `list_item(pipeline, entry.params,
entry.enabled)`. `--builtin`: `builtin_ids()` in ordine, `list_item(load_builtin(id), {}, None)`;
`--all` è ignorato. Si richiede sempre la radice del progetto (exit 2 senza, stesso messaggio degli
altri comandi), ma `--builtin` **non legge** il registry: funziona anche con un registry rotto. Pipeline da mostrare illeggibile → exit 1, stdout vuoto, ogni finding su stderr con
`format_finding`, senza doppioni, in questo ordine: `_unreadable(data, id)` **invariato** (`show` non cambia), più i finding V05
che riguardano la sua voce (`path` che inizia con `pipelines[i]`) e V07 della sua pipeline, presi da
`validate_project` (un helper nuovo nella CLI, non una modifica di `_unreadable`). Questo vale per
ogni voce da mostrare, e per `graph` solo per la voce scelta. L'`entry` non valido (V07) rientra nella decisione (1).

**`pipeline_mermaid`**: testo che finisce con `\n`, indentazione di 4 spazi, righe in quest'ordine:

1. `flowchart TD`
2. una riga per nodo, in ordine di file, con id **`n1`, `n2`, …** (indice base 1): `    n1["<label>"]`
   per `started_by: agent`, `    n1("<label>")` per `human`;
3. una riga per arco, in ordine di file (un `router` dà una riga per route, nell'ordine, poi quella
   di `default`).

`<label>` = (`name` se non è `None` e non è vuoto, altrimenti `id`: `name or id`) + `" [H]"`, `" [C]"` o `" [A]"` per gate `human`/`check`/`agent`
(nessun suffisso senza gate; `at` ed `by` non contano), ridotto a una riga con
`" ".join(testo.split())` e con ogni `"` sostituito da `#quot;`. Archi (la tabella che segue è **normativa carattere per carattere**: spazio prima e dopo la freccia nelle righe senza etichetta, nessuno spazio tra freccia ed etichetta e tra etichetta e nodo di arrivo, ad es. `-.->|"x"| n1` ma `n1 --> n2`; etichette sempre tra virgolette, stessa riduzione e stessa sostituzione):

| Arco | Riga |
|---|---|
| direct | `    n1 --> n2` |
| loop | `    n2 -.->|"<when>, max <n>"| n1` (`<when>` reso; il default è `fail`) |
| router, route con `when` | `    n1 -->|"<when>"| n2` |
| router, route senza `when` ma con `run` | `    n1 -->|"<run>"| n2` |
| router, route senza `when` né `run` | `    n1 --> n2` |
| router, `default` | `    n1 -->|"default"| n2` |

(Nella tabella la barra `|` è quella letterale di Mermaid.) `when` e `run` sono resi con i soli
`params` (inputs invariati, come `show`); `name` non è reso. Un arco il cui `from` o `to` non è un
nodo è saltato (la validazione è di `validate`); per un `router` la regola vale **per route** (e per `default`): si salta solo la riga con il destino inesistente. Con id di nodo duplicati vale il primo. Chiarimenti del 2026-11-16 (non cambiano decisioni): ogni nodo, duplicati compresi, ha la sua riga `nK[...]`; per `when` e `run` di una route la stringa vuota conta come presente (`is not None`).

**CLI `graph`**: stdout = `pipeline_mermaid(pipeline, entry.params)`, exit 0, anche per una pipeline
disabilitata. Con `--output <file>`: il file (percorso relativo alla cartella corrente, sovrascritto)
contiene lo stesso testo scritto con `write_text(..., encoding="utf-8", newline="\n")`; stdout vuoto.
Fixture di T12/T16/T17 (chiarimento 2026-11-16): `graph_demo.pipeline.yaml` ha `id: demo`; l'e2e la installa come voce di registry `id: demo` senza `params`, così lo snapshot vale sia per il test core (override `{}`) sia per l'e2e.

### Error types

Stile del progetto: nessuna eccezione verso l'utente, la CLI traduce in messaggi su stderr ed exit code.

| Caso | Esito |
|---|---|
| Nessun `.lasagna/` salendo da qui (`list`, `graph`) | exit 2, messaggio esistente (nomina `.lasagna/`) |
| `graph`: ordine dei controlli | registry/pipeline scelta illeggibile (exit 1) prima; poi id sconosciuto (exit 2) |
| `graph` con id non nel registry | exit 2, `error: pipeline '<id>' not in the registry; known: <id1>, <id2>` (ids nell'ordine del registry; registry senza voci: `known: (none)`) |
| Registry illeggibile (assente, vuoto, YAML malformato, V01 sul registry) con `list` senza `--builtin` o con `graph` | exit 1, stdout vuoto, solo i finding del registry su stderr (`_unreadable`), anche se l'id di `graph` è sconosciuto |
| Pipeline illeggibile o `entry` non valido (`list` da mostrare, `graph`) | exit 1, stdout vuoto, finding su stderr (come sopra) |
| `--output` non scrivibile (`OSError`) | exit 1, `error: cannot write <path>: <causa>` su stderr, stdout vuoto (`<path>` = l'argomento così com'è scritto; `<causa>` = `e.strerror` o, se vuoto, `str(e)`; i test asseriscono che stderr contiene `cannot write <path>: `, preceduto da `error: `; chiarimento 2026-11-16) |
| `builtin_dir` / `load_builtin` con id sconosciuto | `KeyError` (non raggiungibile dalla CLI) |

### External dependencies

| Dipendenza | Come ci arriva il codice | Come la controllano i test |
|---|---|---|
| File system del progetto | `load_project(root)`, `find_project_root(Path.cwd())` | `tmp_path` + `monkeypatch.chdir` (solo e2e/shell, come i ticket 03–04) |
| Pipeline incluse | `importlib.resources.files("lasagna") / "builtin"` | il pacchetto vero; test su id, mai su versioni o descrizioni (le riscrive il ticket 12) |
| File di `--output` | `Path.write_text` | `tmp_path`; non scrivibile = cartella inesistente |
| stdout / codifica | `_force_utf8_stdout()` all'inizio di `list` e `graph` | `CliRunner` + sottoprocesso reale (T11, T21) con `PYTHONIOENCODING`/`PYTHONUTF8` tolti dall'ambiente, come `tests/e2e/test_show_utf8.py` |
| Orologio, rete | non usati | — |

### What is NOT frozen

Nomi di helper privati, la scomposizione interna di `list_item`/`pipeline_mermaid`, i messaggi dei
finding (solo che sono su stderr e nominano il file), l'ordine di `builtin_ids` oltre a «ordinato»,
la scelta di `importlib.resources` rispetto a `Path(__file__)` purché non dipenda dalla cartella
corrente. Tutti i formati di testo sopra **sono** congelati.

## Out of scope

- `--project` su questi comandi: ticket 11.
- Il contenuto definitivo delle pipeline incluse: ticket 12.

## Definition of done

- [x] every criterion has the verification the spec asks for: a test that fails on a plausible wrong implementation, a passing check, or a recorded review
- [x] whole suite green
- [x] changelog line under Unreleased
- [x] traceability evidence filled in the tickets index; current file updated

## Log

<!-- One line per session: date | outcome | cycles used per criterion | summary of the [lasagna] lines | notes -->

2026-11-16 | done (pending maintainer approval of the commits) | 30 test rows (T01-T24 planned; review added 6 groups): T01-T03, T05, T07, T08, T12, T16-T20, T22 green after 1; the others passes-immediately with hand mutations (rule extended by the maintainer); the review-added test for duplicate registry ids was red, then green | contract (done earlier; gate re-run with a separate Opus subagent, clarified 2026-11-16: `cannot write` stderr, fixture `id: demo` without `params`, empty `when`/`run` counts as present, one line per node) -> red/green T01-T24 -> review (1 of 2 back to red) -> close | Mutations M01-M40 killed except M18 (`pipeline.yaml` filter in `builtin_ids`), later covered by the extracted `_ids_in` helper and its test. Review fixes: ruff (SIM102, UP012 x2), V05 id mismatch test, duplicate-finding checks, empty `name`/`when`, `graph` ignores a broken sibling, `list` KeyError with duplicate registry ids fixed in `_unreadable_to_list` (maintainer's choice, 2026-11-16; V03 itself stays in ticket 06). Unresolved contract ambiguities 4 and 6 left untested. The test file is `tests/e2e/test_graph_command.py` (basename clash with `test_graph.py`). Incident: a mutation script rewrote `view.py` and `cli.py` as CRLF; restored to LF, later scripts use bytes. Not done by choice: the shared print-findings-and-exit helper and moving the `list`/`graph` assembly to `shell/` (nits). 614 tests, ruff clean.
