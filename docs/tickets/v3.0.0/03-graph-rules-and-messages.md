---
status: done            # todo | in_progress | done | blocked
depends_on: ["02"]      # ticket numbers
criteria: [AC-V3-009, AC-V3-010, AC-V3-011, AC-V3-013, AC-V3-045]
---

# 03 — Regole del grafo (V07, V10, V12), `--json` e formato dei messaggi

The `status` above is the only record of this ticket's state: the tickets index
and the current file never copy it.

## Goal

`validate` applica V07 (entry), V10 (un solo arco in avanti) e V12 (loop
`when: fail` da nodo senza gate). Ogni messaggio ha file, percorso YAML, ID
della regola e frase di correzione. `--json` restituisce `errors` e `warnings`
con `rule`, `file`, `path`, `message`.

## Context

- Milestone M2, seconda parte (§12).
- Spec §5 (V07, V10, V12; formato dei messaggi), §6.1 (entry e nodi finali),
  §8.2 (`--json`).
- `core/graph.py` nasce qui (§9.1): archi in uscita, archi "in avanti". Il
  ticket 06 lo estende (raggiungibilità V08, nodi finali V09, cicli V23).
- Formato dei messaggi: lo usano tutte le regole, comprese V01, V05 e V06 del
  ticket 01, da riallineare qui se non lo rispettano.

## Changes

- `core/graph.py`: archi in uscita per nodo, classificazione degli archi.
- `core/validate.py`: V07, V10, V12; frase di correzione per ogni regola
  esistente.
- `cli.py`: `validate --json`; il messaggio di exit 2 passa su stderr.
- `core/models.py`: `Pipeline.entry` diventa opzionale (decisione del maintainer,
  2026-11-10: un `entry` assente è V07, non V01).
- `core/validate.py`: `render_json`; `shell/project.py`: i messaggi dei finding di
  caricamento prendono la frase di correzione nel formato F (vedi Contract).
- `schema/pipeline.schema.json`: **rigenerato dal coordinatore** con
  `uv run python -m lasagna.shell.gen_schema schema` nel green di T12 (l'implementer
  non scrive fuori da `src/`).
- Riga in `CHANGELOG.md` sotto Unreleased.
- **Fixture dei ticket precedenti, aggiornate nel nodo contract** (solo test,
  suite verde: 264 passed, ruff pulito): le nuove regole V10 e V12 le facevano
  scattare. Ognuna sposta il router da `a` a `b` (V10: `a` ha già il suo arco in
  avanti) e/o dà un gate al nodo `b` da cui parte il loop (V12). Dettaglio in Files
  involved.

## Files involved

- `src/lasagna/core/graph.py` (nuovo, puro), `src/lasagna/core/validate.py`,
  `src/lasagna/core/models.py`, `src/lasagna/shell/project.py`, `src/lasagna/cli.py`
- `schema/pipeline.schema.json` (rigenerato dal coordinatore)
- `tests/core/`, `tests/shell/`, `tests/e2e/`
- Fixture dei ticket 01 e 02 **già aggiornate nel nodo contract**:
  `tests/core/test_models_edges.py` (nodo `b` con gate, router da `b`),
  `tests/core/test_extension_keys.py` (nodo `b` con gate, `ROUTER` da `b`),
  `tests/core/test_validate_v06_edge_types.py` (router da `b`),
  `tests/core/test_models_rules_not_coded.py` (il caso V13 ha come unico arco il
  router a una route, senza il `direct` di `P0`),
  `tests/shell/test_spec_blocks.py` (T42 del 02: i nodi da cui parte un loop
  `when: fail` ricevono un gate).
- Test del 02 **da aggiornare nelle righe red** indicate: `tests/core/test_models_rules_not_coded.py`
  (caso V07, riga T11) e `tests/core/test_models_null_and_empty.py` (caso
  `nodes-and-edges-empty`, riga T11).

## Tests to pass

<!-- Filled in by the implementation pipeline (node contract) as a checklist:
one line per planned verification, in order. The green node checks off a test
with `[x] (green after N)`; the review node checks off checks and reviews. -->

Regola per questo ticket (maintainer, 2026-11-10, approvata a fine contratto: quella
del 02). Un test pianificato che
passa subito perché il comportamento esiste già lo spunto con `passes immediately`
e proseguo, **purché sia nell'elenco qui sotto e verificato con la mutazione
indicata**; mi fermo su un passa-subito fuori elenco o su un test che non verifica
nulla. L'elenco va nel Log di chiusura.

Passa-subito attesi (ognuno è ucciso dalla mutazione indicata): T04 (M01), T05
(M03), T06 (M04), T08 (M07, M08), T09 (M09, M10), T10 (M12, M13), T13 (M21), T14
(M15), T15 (M19), T16 (M20), T17 (M18), T18 (M24), T22 (M26), T23 (M26), T25
(M27), T26 (M29), T28 (M31), T29 e T30 (M32). Dove un passa-subito dipende da come
l'implementer ha scritto la riga precedente (T04, T05, T06, T08, T09, T10, T22,
T23, T25, T26) può anche non succedere: è un'altra riga rossa in più, non un
problema. Le righe T29 e T30 sono di integrazione per costruzione.

**Convenzioni di tutte le righe** (`validate_project` è il seam, salvo dove la riga
dice altro):
- Fixture base: registry `R0 = {"lasagna": "3.0", "pipelines": [{"id": "demo", "path": "pipelines/demo"}]}`;
  pipeline `P0 = {"lasagna": "3.0", "id": "demo", "entry": "a", "nodes": [A, B], "edges": [D(a, b)]}`.
  Ogni riga parte da `R0`/`P0`, cambia solo ciò che dice, e chiama
  `validate_project(R0, {"pipelines/demo": P})`.
- Abbreviazioni (si scrivono come costanti o helper nel test, non fanno parte del contratto):
  `A = {"id": "a", "description": "A"}`, `B` e `C` allo stesso modo per `b` e `c`;
  `G = {"type": "human", "message": "m"}` (un gate valido); `D(x, y) = {"type": "direct", "from": x, "to": y}`;
  `L(x, y, **k) = {"type": "loop", "from": x, "to": y, "max_iterations": 3, **k}`;
  `RT(x) = {"type": "router", "from": x, "decided_by": "agent", "routes": [{"when": "w", "to": "b"}, {"when": "w2", "to": "a"}]}`.
  Un nodo con un gate si scrive `{**A, "gate": G}`.
- Una riga che scrive `edges = [...]` sostituisce l'intera lista `edges` di `P0`;
  «P0 + X» è la lista di `P0` seguita da X (X è in posizione 1). Una riga che scrive
  `nodes = (...)` sostituisce `nodes`.
- `RF = ".lasagna/pipelines.yaml"`; `PF = ".lasagna/pipelines/demo/pipeline.yaml"`.
- «→ `[]`»: restituisce `[]`. «→ X `p`»: restituisce **esattamente un** finding con
  `(rule, file, path) == (X, PF, p)`. «→ X `p`, Y `q`»: esattamente due finding, uno per
  coppia (confronto ordinato, l'ordine non è congelato). Il file è `PF` salvo `(RF)`.
- **F** (formato della frase di correzione; vedi Contract › Data types): dato
  `message`, `problem, fix = message.rsplit("; ", 1)` riesce (il separatore c'è),
  `problem.strip()` non è vuoto e `re.fullmatch(r"[a-z]\S*( \S+)+\.", fix)` riesce.
  «message in F» nei test è questa asserzione, scritta una volta come helper.
- Una riga con più casi separati da «;» è **parametrizzata**: un caso di test per
  caso, non un solo test con molte asserzioni.
- Ogni test cita il suo criterio in un commento `# AC-V3-NNN`; nessun mock e nessun
  `monkeypatch` in `tests/core/`.

Grafo (AC-V3-010; `tests/core/test_graph.py`; `Pipeline.model_validate(P)` per costruire l'oggetto)
- [x] (green after 1) T01 AC-V3-010 · `outgoing_edges(pipeline)`: (a) `P0` → chiavi esattamente `{"a", "b"}`; `"a"` ha una sola coppia `(0, e)` con `e is pipeline.edges[0]`; `"b"` ha `[]`; (b) `nodes = (A, B, C)`, `edges = [D(a, b), L(b, a), RT(b), D(c, a)]` → `"a"`: indici `[0]`; `"b"`: indici `[1, 2]` in quest'ordine; `"c"`: `[3]`, e ogni arco è lo stesso oggetto di `pipeline.edges[i]`; (c) `P0 + D("ghost", "b")` → le chiavi restano `{"a", "b"}` (nessuna chiave `ghost`) e `"a"` ha ancora la sola coppia di indice 0; (d) `nodes = (A, A, B)` → chiavi `{"a", "b"}`, e `"a"` ha una sola coppia (non una per nodo duplicato).
- [x] (green after 1) T02 AC-V3-010 · `is_forward(edge)` sugli archi di `edges = [D(a, b), RT(a), L(b, a), L(b, a, when="pass"), L(b, a, when="testo libero")]` (modelli di `pipeline.edges`): `True, True, False, False, False`.

V10 (AC-V3-010)
- [x] (green after 1) T03 AC-V3-010 · V10 scatta: `edges = [D(a, b), D(a, b)]` → V10 `edges[1]`; `[D(a, b), RT(a)]` → V10 `edges[1]`; `[RT(a), D(a, b)]` → V10 `edges[1]`; `[RT(a), RT(a)]` → V10 `edges[1]`; `[D(a, b), D(a, b), D(a, b)]` → V10 `edges[1]` (un solo finding per nodo); `[D(a, b), L(a, a, when="pass"), D(a, b)]` → V10 `edges[2]` (l'indice è quello nel file, il `loop` in mezzo non si salta). In ogni caso il `message` è in F e contiene `'a'` (l'id del nodo tra apici).
- [x] (passes immediately, expected in the declared list; killed by M01 in review) T04 AC-V3-010 · V10 non scatta → `[]`: `edges = [D(a, b), L(a, a, when="pass")]`; `[D(a, b), L(a, a, when="pass"), L(a, a, when="testo libero")]`; `[RT(a), L(a, a, when="pass")]`; `nodes = (A, B, C)`, `edges = [D(a, b), D(b, c)]`; `edges = []`.
- [x] (passes immediately, expected in the declared list; killed by M03 in review) T05 AC-V3-010 · un finding per nodo: `nodes = (A, B, C)`, `edges = [D(a, b), D(a, b), D(b, c), D(b, c)]` → V10 `edges[1]`, V10 `edges[3]`.
- [x] (passes immediately, expected in the declared list; killed by M04 in review) T06 AC-V3-010 · un arco da un nodo inesistente non conta per V10: `edges = [D(a, b), D("ghost", "b"), D("ghost", "b")]` → V06 `edges[1].from`, V06 `edges[2].from` (e nient'altro).

V12 (AC-V3-011)
- [x] (green after 1) T07 AC-V3-011 · V12 scatta (nodi senza gate): `edges = [D(a, b), L(b, a, when="fail")]` → V12 `edges[1]`; `[D(a, b), L(b, a)]` (`when` assente: il default è `fail`) → V12 `edges[1]`; `[D(a, b), L(a, a)]` (self-loop) → V12 `edges[1]`. In ogni caso il `message` è in F e contiene l'id del nodo da cui parte il loop tra apici (`'b'`, `'b'`, `'a'`).
- [x] (passes immediately, expected in the declared list; killed by M07, M08 in review) T08 AC-V3-011 · V12 guarda `when`, esatto e sensibile alle maiuscole: `edges = [D(a, b), L(b, a, when="pass")]` → `[]`; `[D(a, b), L(b, a, when="Tests to pass has an unchecked line.")]` → `[]`; `[D(a, b), L(b, a, when="Fail")]` → `[]`.
- [x] (passes immediately, expected in the declared list; killed by M09, M10 in review) T09 AC-V3-011 · V12 non scatta se il nodo ha un gate di qualunque tipo e momento: `nodes = (A, {**B, "gate": X})`, `edges = [D(a, b), L(b, a)]` con `X` = `G`; `{"type": "check", "run": "r"}`; `{"type": "agent", "criteria": ["c"]}`; `{**G, "at": "entry"}` → `[]` in ognuno.
- [x] (passes immediately, expected in the declared list; killed by M12, M13 in review) T10 AC-V3-011 · V12 per arco e solo su nodi esistenti: `edges = [D(a, b), L(b, a), L(a, a)]` → V12 `edges[1]`, V12 `edges[2]`; `edges = [D(a, b), L("ghost", "a")]` → V06 `edges[1].from` (e nient'altro).

V07 (AC-V3-009)
- [x] (green after 1; also updated the two 02 tests as the row says) T11 AC-V3-009 · V07 `entry` che non nomina un nodo: `entry = "ghost"` → V07 `entry`; `entry = ""` → V07 `entry`; `entry = "A"` (il confronto è esatto) → V07 `entry`; `entry = " a"` e `entry = "a "` (nessuno `strip`) → V07 `entry`; per ogni caso il `message` è in F e contiene l'entry tra apici (`'ghost'`, `''`, `'A'`, `' a'`, `'a '`). **Nella stessa riga** si aggiornano due test del 02, che altrimenti restano rossi: in `tests/core/test_models_rules_not_coded.py` si toglie il caso `entry-names-no-node-v07` (V07 nasce qui: non è più «ciò che il modello non giudica»); in `tests/core/test_models_null_and_empty.py` il caso `nodes-and-edges-empty` ha come esito atteso esattamente V07 `entry` (file `PF`) invece di `[]`: continua a provare che `nodes` ed `edges` vuoti sono validi per la forma (nessun V01, nessun V06), perché un `entry: "a"` senza nodi è per definizione V07.
- [x] (green after 1; schema/pipeline.schema.json regenerated by the coordinator with the generator command) T12 AC-V3-009 · V07 `entry` assente: `P0` senza la chiave `entry` → V07 `entry` (non V01); `entry = None` (`null` YAML) → V07 `entry`; per ogni caso il `message` è in F. Il green di questa riga è `Pipeline.entry: str | None = None` e **la rigenerazione di `schema/pipeline.schema.json` a cura del coordinatore** (`uv run python -m lasagna.shell.gen_schema schema`): senza, la riga del 02 che confronta i file committati (`test_committed_schema_file_is_byte_identical_to_the_rendered_schema[pipeline]`) resta rossa e la suite non è verde.
- [x] (passes immediately, expected in the declared list; killed by M21 in review) T13 AC-V3-009 · un `entry` di tipo sbagliato resta del modello: `entry = 3` → V01 `entry` (e nient'altro: niente V07).
- [x] (passes immediately, expected in the declared list; killed by M15 in review) T14 AC-V3-009 · `entry` valido → `[]`: `P0`; `entry = "b"` con `edges = [D(b, a)]`; `nodes = ({**A, "gate": G}, B)`, `edges = [D(a, b), L(a, a)]` (loop `when: fail` sul primo nodo, che ha un gate).
- [x] (passes immediately, expected in the declared list; killed by M19 in review) T15 AC-V3-009 · V07 e le altre regole del grafo si sommano: `P0` senza `entry` con `edges = [D(a, b), D(a, b)]` → V07 `entry`, V10 `edges[1]`; `entry = "ghost"` con `edges = [D(a, "ghost")]` → V06 `edges[0].to`, V07 `entry`.
- [x] (passes immediately, expected in the declared list; killed by M20 in review) T16 AC-V3-009 · un pipeline che non passa il modello dà solo V01 (come per V05-id e V06): `P0` senza `entry` e con una chiave `bogus: 1` → V01 `bogus` (nessun V07); `entry = "ghost"` con `edges = [{"type": "teleport", "from": "a", "to": "b"}]` → V01 `edges[0].type` (nessun V07).
- [x] (passes immediately, expected in the declared list; killed by M18 in review) T17 AC-V3-014 · `tests/core/test_schema.py`: in `json.loads(render_schema("pipeline"))`, `"entry"` è in `properties` e **non** è in `required`; `"lasagna"`, `"id"` e `"nodes"` sono ancora in `required`.

Formato dei messaggi (AC-V3-045)
- [x] (passes immediately, expected in the declared list; killed by M24 in review) T18 AC-V3-045 · `tests/core/test_message_format.py`: ogni regola esistente ha il messaggio in F, `level == "error"` e un `file` che comincia con `.lasagna/`; esattamente un finding per caso: registry con chiave `bogus` (V01); `P0` con `edges = [{"type": "teleport", "from": "a", "to": "b"}]` (V01); radice del pipeline che non è un mapping (`["x"]`, V01); radice del registry che non è un mapping (`validate_project(["x"], {})`, V01); `pipelines = {"pipelines/demo": None}` (V05); id del pipeline ≠ id del registry (V05); `edges = [D(a, "ghost")]` (V06; l'arco sostituisce quello di `P0`, quindi nessun V10).
- [x] (green after 1) T19 AC-V3-045 · `tests/shell/test_loading_messages.py` (`load_project` su un progetto in `tmp_path`): ogni finding di caricamento ha il messaggio in F, `rule == "V01"`, e `data.findings` ne ha esattamente uno: `pipeline.yaml` malformato (`a: 1\nb: [1, 2\nc: 3\n`, e il messaggio contiene `line 3`); `pipeline.yaml` con un carattere di controllo non valido (i byte di `a: \x01\n`: l'errore del parser non ha posizione, il messaggio non ha `line`); `pipeline.yaml` vuoto (solo un commento, e il messaggio contiene `empty`); `pipelines.yaml` malformato (`a: [1\n`); `pipelines.yaml` vuoto (solo un commento, `empty`); `pipelines.yaml` assente.

`--json`: `render_json` (AC-V3-013; `tests/core/test_render_json.py`; `Finding` costruiti nel test)
- [x] (green after 1) T20 AC-V3-013 · `render_json([])` è esattamente `'{\n  "errors": [],\n  "warnings": []\n}\n'`.
- [x] (passes immediately, NOT in the declared list: the implementer of T20 wrote the whole contract recipe; accepted by the maintainer 2026-11-10; killed by M26 in review) T21 AC-V3-013 · `render_json([Finding("V06", "f.yaml", "edges[0].to", "m1"), Finding("V22", "g.yaml", "nodes[1]", "m2", level="warning")])` è esattamente il testo in Contract › Return shape (indentazione di 2 spazi, chiavi nell'ordine `rule, file, path, message`, nessuna chiave `level`, un solo `"\n"` finale).
- [x] (passes immediately, expected in the declared list; killed by M26 in review) T22 AC-V3-013 · la classificazione è per `level`, non per id di regola, e l'ordine di ingresso si conserva in ogni lista: `[Finding("V22", "a.yaml", "p1", "m1"), Finding("V06", "b.yaml", "p2", "m2", level="warning"), Finding("V06", "c.yaml", "p3", "m3")]` → `json.loads` ha `errors` = i finding 1 e 3 in quest'ordine e `warnings` = il 2.
- [x] (passes immediately, expected in the declared list; killed by M26 in review) T23 AC-V3-013 · `Finding("V01", "f.yaml", "", "è; fix it.")` → il testo contiene il carattere `è` (non `è`) e un elemento con `"path": ""` (stringa vuota, non `null`).

CLI (`tests/e2e/`, `CliRunner` di typer, cartella corrente su un progetto in `tmp_path`; `result.stdout` e `result.stderr` sono separati). Il progetto «valido» è quello del primo test di `tests/e2e/test_validate.py` (entry `first`, nodi `first` e `second` con `description`, un `direct` `first` → `second`)
- [x] (green after 1) T24 AC-V3-013 · `validate --json` sul progetto valido → exit 0, `result.stdout == '{\n  "errors": [],\n  "warnings": []\n}\n'`, `result.stderr == ""`.
- [x] (passes immediately, expected in the declared list; killed by M27 in review) T25 AC-V3-013 · `validate --json` con l'arco `direct` `first` → `ghost` (progetto del secondo test di `test_validate.py`) → exit 1; `json.loads(result.stdout)` ha esattamente le chiavi `errors` e `warnings`; `warnings == []`; `errors` ha un solo elemento, con le chiavi in quest'ordine `["rule", "file", "path", "message"]`, `rule == "V06"`, `file == ".lasagna/pipelines/demo/pipeline.yaml"`, `path == "edges[0].to"`, `message` in F; `result.stdout == json.dumps(parsed, indent=2, ensure_ascii=False) + "\n"` (niente altro su stdout); `result.stderr == ""`.
- [x] (passes immediately, expected in the declared list; killed by M29 in review) T26 AC-V3-013 · i finding di caricamento stanno in `errors`: `validate --json` con `pipeline.yaml` malformato (`a: 1\nb: [1, 2\nc: 3\n`) → exit 1, `errors` ha un solo elemento `V01` con `file == ".lasagna/pipelines/demo/pipeline.yaml"` e `path == ""`; con `.lasagna/` senza `pipelines.yaml` → exit 1, un solo elemento `V01` con `file == ".lasagna/pipelines.yaml"`; in entrambi `warnings == []` e lo stdout è solo il JSON (`json.loads` riesce e `result.stdout` termina con `"}\n"`).
- [x] (green after 1; import order of the new test file fixed by the coordinator with `ruff check --fix`) T27 AC-V3-013 · nessun `.lasagna/` risalendo dalla cartella corrente (stessa guardia di `pytest.skip` del test esistente): `validate` e `validate --json` → exit 2, `".lasagna/"` in `result.stderr`, `result.stdout == ""` (il messaggio d'uso esce su stderr in entrambe le modalità: così stdout, con `--json`, è sempre JSON o vuoto).
- [x] (passes immediately, expected in the declared list; killed by M31 in review) T28 AC-V3-045 · in modalità umana l'esito esce su stdout e stderr resta vuoto: sul progetto con l'arco verso `ghost` → exit 1, `result.stderr == ""`, e **esattamente una** riga di `result.stdout` comincia con `error V06 .lasagna/pipelines/demo/pipeline.yaml edges[0].to: `; sul progetto valido → exit 0, `result.stderr == ""`, `result.stdout` non comincia con `{`.
- [x] (passes immediately, integration row in the declared list; killed by M32 in review) T29 AC-V3-009/010/011/045 · integrazione (modalità umana), tre casi sul progetto valido modificato: `entry: ghost`; un secondo `direct` `first` → `second` in coda; un `loop` `first` → `first` con `max_iterations: 3` in coda (senza gate su `first`) → exit 1 e **esattamente una** riga di `result.stdout` comincia con `error V07 .lasagna/pipelines/demo/pipeline.yaml entry: `, `error V10 .lasagna/pipelines/demo/pipeline.yaml edges[1]: `, `error V12 .lasagna/pipelines/demo/pipeline.yaml edges[1]: ` rispettivamente.
- [x] (passes immediately, integration row in the declared list; killed by M32 in review) T30 AC-V3-009/010/011/013 · integrazione (`--json`), gli stessi tre casi di T29 → exit 1, `errors` ha un solo elemento con `(rule, file, path)` = `("V07", PF, "entry")`, `("V10", PF, "edges[1]")`, `("V12", PF, "edges[1]")`, `warnings == []`.

Righe aggiunte dalla review (1° giro, maintainer 2026-11-10: emendamento al contratto sulla codifica di stdout + 8 righe). Passa-subito dichiarati per queste righe, uccisi dalla mutazione indicata: T32 (M34), T33 (M35), T34 (M36), T35 (M37), T36 (M17b), T37 (M38, M39), T38 (M40); T31 è rossa su Windows (stdout in cp1252 su pipe) e passa subito altrove (M33)
- [x] (green after 1; red on Windows: real UnicodeEncodeError in a subprocess; found by the adversarial reviewer) T31 AC-V3-013/045 · `tests/e2e/test_validate_utf8.py`: sottoprocesso reale, non `CliRunner`: `subprocess.run([sys.executable, "-c", "from lasagna.cli import app; app()", "validate", *args], cwd=<progetto in tmp_path>, capture_output=True, env=<os.environ senza PYTHONUTF8 e senza PYTHONIOENCODING>)`, con `args` = `["--json"]` e `[]` (due casi). Il progetto è quello valido con `entry: "café✓"` scritto in UTF-8 (non nomina nessun nodo: V07). Esito: exit code 1; `proc.stdout.decode("utf-8")` non solleva; nel caso `--json`, `json.loads(...)["errors"]` ha un solo elemento con `rule == "V07"`, `path == "entry"` e `"café✓"` nel `message`; nel caso umano la riga V07 contiene `'café✓'`.
- [x] (passes immediately, declared with the review rows; killed by M34 in review) T32 AC-V3-011 · `tests/core/test_validate_v12.py`: `edges = [D(a, b), L(b, a, when="fail ")]` (spazio finale: non è `fail`) → `[]`.
- [x] (passes immediately, declared with the review rows; killed by M35 in review) T33 AC-V3-010 · `tests/core/test_graph.py`: `nodes = (B, A)` con gli archi di `P0`: `list(outgoing_edges(pipeline)) == ["b", "a"]` (l'ordine delle chiavi è quello di prima comparsa in `nodes`).
- [x] (passes immediately, declared with the review rows; killed by M36 in review) T34 AC-V3-009 · `tests/core/test_validate_v07.py`: registro con la voce `{"id": "demo", "path": "pipelines/demo", "enabled": False}` e `entry = "ghost"` → V07 `entry` (V07 si applica anche alle pipeline disabilitate).
- [x] (passes immediately, declared with the review rows; killed by M37 in review) T35 AC-V3-009 · `tests/core/test_validate_v07.py`: id del pipeline `"other"` (≠ id del registry) con `entry = "ghost"` → esattamente `("V05", RF, "pipelines[0].id")` e `("V07", PF, "entry")` (V05-id non nasconde le regole del grafo).
- [x] (passes immediately, declared with the review rows; killed by M17b in review) T36 AC-V3-009 · `tests/core/test_validate_v07.py`: con `entry` assente (chiave assente; `None`) il `message` del finding V07 non contiene apici singoli (non nomina un valore).
- [x] (passes immediately, declared with the review rows; killed by M38, M39 in review) T37 AC-V3-045 · `tests/e2e/test_validate_streams.py`: in modalità umana, progetto valido → le righe non vuote di `result.stdout` sono esattamente una e comincia con `ok`; progetto con l'arco verso `ghost` → nessuna riga di `result.stdout` comincia con `ok`.
- [x] (passes immediately, declared with the review rows; killed by M40 in review) T38 AC-V3-009/010/011 · `tests/core/test_validate_v07.py`: registry con due voci (`demo` e `second`, path `pipelines/second`), pipeline `demo` = `P0`, pipeline `second` = `P0` con `id = "second"` e `entry = "ghost"` → esattamente `("V07", ".lasagna/pipelines/second/pipeline.yaml", "entry")` (le regole del grafo girano su ogni voce, col file giusto).

Mutazioni da provare nel nodo review (ognuna: modifica temporanea del codice di produzione → i test indicati falliscono → si ripristina; evidenza nella riga)
- [x] (evidence: killed: T03, T04, T07, T10, T14, T30 and the self-validation rows; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M01 AC-V3-010 · V10 che conta ogni arco in uscita, `loop` compresi → T04.
- [x] (evidence: killed: T02, T03; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M02 AC-V3-010 · V10 che ignora i `router` (solo `direct`) → T03.
- [x] (evidence: killed: T05; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M03 AC-V3-010 · V10 che si ferma al primo nodo con due archi in avanti → T05.
- [x] (evidence: killed: T01, T06 (outgoing_edges variant); restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M04 AC-V3-010 · V10 che raggruppa anche gli archi con `from` inesistente → T06.
- [x] (evidence: killed: T03; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M05 AC-V3-010 · V10 con un finding per ogni arco in avanti dopo il primo (tre `direct` → due finding) → T03.
- [x] (evidence: killed: T03, T05, T15, T29, T30; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M06 AC-V3-010 · V10 con percorso sul primo arco in avanti, o sull'indice tra i soli archi in avanti → T03.
- [x] (evidence: killed: T03, T04, T08; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M07 AC-V3-011 · V12 che ignora `when` (ogni `loop` da un nodo senza gate) → T08.
- [x] (evidence: killed: T08; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M08 AC-V3-011 · V12 che confronta `when` senza distinguere maiuscole (`"Fail"`) → T08.
- [x] (evidence: killed: T09, T14 and others; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M09 AC-V3-011 · V12 che ignora il gate (scatta anche con un gate) → T09.
- [x] (evidence: first variant (entry gates added to `ungated`) was equivalent because `ungated - gated` cancels it; the effective variant (entry-gated nodes flagged) killed: T09; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M10 AC-V3-011 · V12 che conta solo i gate `at: exit` → T09.
- [x] (evidence: killed: T07, T10, T29, T30; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M11 AC-V3-011 · V12 solo per `when: fail` scritto, non per il default → T07.
- [x] (evidence: killed: T10 (and the V06 loop test); restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M12 AC-V3-011 · V12 che solleva o segnala su un `loop` con `from` inesistente → T10.
- [x] (evidence: killed: T10; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M13 AC-V3-011 · V12 che si ferma al primo arco colpevole → T10.
- [x] (evidence: killed: T11, T15, T29, T30 and the null/empty case; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M14 AC-V3-009 · V07 che controlla solo che `entry` sia presente, non che nomini un nodo → T11.
- [x] (evidence: killed: T14 (and the null/empty case); restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M15 AC-V3-009 · V07 che confronta `entry` solo col primo nodo → T14.
- [x] (evidence: killed: T11 (3 cases); restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M16 AC-V3-009 · V07 che confronta senza distinguere maiuscole o con `strip` → T11.
- [x] (evidence: killed: T12, T15; restored (variant M17b, missing message naming 'None', killed by T36 added by the review); mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M17 AC-V3-009 · V07 che salta `entry` assente → T12.
- [x] (evidence: killed: T12, T15, T16, T17 and the committed-schema byte test; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M18 AC-V3-009 · `Pipeline.entry: str` richiesto di nuovo → T12, T17 (e la riga del 02 che confronta lo schema committato).
- [x] (evidence: killed: T15; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M19 AC-V3-009 · V07 che esce subito dopo il suo finding (nasconde V10 e V06) → T15.
- [x] (evidence: killed: T13, T16, T18 and a 02 test; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M20 AC-V3-009 · le regole del grafo che girano sul dizionario grezzo anche se il modello fallisce → T16.
- [x] (evidence: first variant (`coerce_numbers_to_str=True`) was ineffective under strict mode; the effective variant (before validator turning 3 into '3') killed: T13; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M21 AC-V3-009 · `entry` che accetta `3` coercendolo a stringa (es. `coerce_numbers_to_str=True` o un validatore `before`; il solo modo lax non basta, pydantic rifiuta comunque un `int` per `str`) → T13 (dà V07 al posto di V01).
- [x] (evidence: killed: T01 (a: unknown from also T06; b: duplicate ids); restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M22 AC-V3-010 · `outgoing_edges` che include archi da nodi inesistenti, o raddoppia le liste per id duplicato → T01.
- [x] (evidence: killed: T02 (a: always true; b: router false, also T03); restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M23 AC-V3-010 · `is_forward` vero per `loop`, o falso per `router` → T02.
- [x] (evidence: killed: T18 (V06 also T25; V05; V01 also T13), one at a time; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M24 AC-V3-045 · un messaggio V01, V05 o V06 senza la frase di correzione (uno alla volta) → T18.
- [x] (evidence: killed: T19 (malformed, empty, not found, one at a time); restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M25 AC-V3-045 · un messaggio di caricamento con `: ` al posto di `; `, o senza correzione (uno alla volta) → T19.
- [x] (evidence: killed: T20-T26 (swap: T21, T22, T23, T25, T26, T30; level: T21, T22, T23, T25; sort_keys: T21, T25; ensure_ascii: T23; no newline: T20, T21, T24, T25, T26; indent None: T20, T21, T24, T25; by rule id: T22); restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M26 AC-V3-013 · `render_json` con `errors` e `warnings` scambiati; con `level` nell'elemento; con `sort_keys=True`; con `ensure_ascii` di default; senza `"\n"` finale; con `indent=None` (uno alla volta) → T20–T23.
- [x] (evidence: killed: T25, T26, T30; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M27 AC-V3-013 · `validate --json` che esce 0 con errori → T25.
- [x] (evidence: killed: T24, T25, T26, T30; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M28 AC-V3-013 · `validate --json` che stampa anche le righe umane o la riga `ok:` → T24, T25.
- [x] (evidence: killed: T26; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M29 AC-V3-013 · `validate --json` che scarta i finding di caricamento → T26.
- [x] (evidence: killed: T27; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M30 AC-V3-013 · il messaggio di exit 2 su stdout → T27.
- [x] (evidence: killed: T28, T29; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M31 AC-V3-045 · i finding in modalità umana su stderr → T28.
- [x] (evidence: killed: T29, T30; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M32 AC-V3-009/010/011 · la CLI (umana e JSON) che stampa solo le regole V01, V05, V06 → T29, T30.

- [x] (evidence: killed: T31 (both cases); restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M33 AC-V3-013 · togliere la forzatura UTF-8 di stdout da `cli.py` → T31 (su Windows).
- [x] (evidence: killed: T32; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M34 AC-V3-011 · V12 con `edge.when.strip() == "fail"` (o `startswith("fail")`) → T32.
- [x] (evidence: killed: T33; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M35 AC-V3-010 · `outgoing_edges` che ordina le chiavi (`dict(sorted(...))`) → T33.
- [x] (evidence: killed: T34 (and T11); restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M36 AC-V3-009 · le regole del grafo saltano le pipeline con `enabled: false` → T34.
- [x] (evidence: killed: T35; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M37 AC-V3-009 · `continue` dopo il V05-id (nasconde V07, V10, V12) → T35.
- [x] (evidence: killed: T37; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M38 AC-V3-045 · la CLI non stampa nulla su un progetto valido → T37.
- [x] (evidence: killed: T37; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M39 AC-V3-045 · la CLI stampa `ok:` anche con errori → T37.
- [x] (evidence: killed: T38; restored; mutation runner in the scratchpad, production files backed up and sha256 verified identical after the run, 2026-11-10) M40 AC-V3-009 · le regole del grafo girano solo sulla prima voce del registry (`break` a fine ciclo) → T38.

Check del nodo review
- [x] (evidence: uv run pytest 351 passed; uv run ruff check All checks passed) C01 · `uv run pytest` verde e `uv run ruff check` pulito.
- [x] (evidence: sha256 of schema/*.json identical before and after `uv run python -m lasagna.shell.gen_schema schema`) C02 AC-V3-014 · `sha256` dei due file in `schema/` prima e dopo `uv run python -m lasagna.shell.gen_schema schema` (dalla radice del repo) uguale.
- [x] (evidence: `uv run lasagna validate` from the repo root: `ok: no problems found`, exit 0) C03 AC-V3-005 (check) · il `.lasagna/` del repo e le pipeline in `src/lasagna/builtin/` restano valide con V07, V10, V12: `uv run lasagna validate` esce 0 dalla radice del repo.
- [x] (evidence: clean copy of tracked+new files without .venv (UV_LINK_MODE=copy, 2026-11-10): uv sync ok; uv run pytest 351 passed; uv run ruff check All checks passed; uv run lasagna validate exit 0) C04 · copia pulita dell'albero (file tracciati e nuovi, senza `.venv/`): `uv sync && uv run pytest && uv run ruff check` escono 0.
- [x] (evidence: independent adversarial reviewer (Opus), 1 blocker (Windows stdout encoding, fixed in T31 with a contract amendment) and 7 gaps (T32-T38), 3 notes deferred: exit code with warnings only (ticket 06), non-UTF-8 YAML files (ticket 11), router route with `when: fail` (V12 covers loop edges only, by contract)) R01 · revisore indipendente con il ruolo `adversarial-reviewer`, senza il ragionamento del coordinatore.

Tracciabilità dei criteri (comprese le righe della review): AC-V3-009 → T11–T16, T34–T36, T38, M14–M21, M36, M37, M40; AC-V3-014 → T12, T17, M18; AC-V3-010 → T01–T06, T29–T30, T33, T38, M01–M06, M22–M23, M35; AC-V3-011 → T07–T10, T29–T30, T32, T38, M07–M13, M34; AC-V3-013 → T20–T27, T30, T31, M26–M30, M33; AC-V3-045 → T03, T07, T11, T12, T18, T19, T25, T28, T29, T31, T37, M24, M25, M31, M38, M39.

## Contract

<!-- Filled in by the implementation pipeline (node contract), from its
contract template. -->

Questo contratto **aggiunge** al contratto del 02 (che resta valido per i modelli,
`validate_project`, `render_schema`, il generatore). Cambiano solo i punti della
tabella.

### Cosa cambia rispetto al 02 e al 01

| Punto | Esito in questo ticket | Test da aggiornare |
|---|---|---|
| `Pipeline.entry` campo richiesto (il 02 rimandava la scelta a questo ticket) | **opzionale**: un `entry` assente o `null` è V07, non V01. Un `entry` di tipo sbagliato (es. `3`) resta V01 (strict) | `test_models_rules_not_coded.py` (caso V07) e `test_models_null_and_empty.py` (caso `nodes-and-edges-empty`): riga T11 |
| V07, V10, V12 non esistono | nascono qui; V13 e V14 restano del ticket 06 (V14: `test_models_node.py` non si tocca qui) | solo le fixture già aggiornate nel nodo contract |
| Stream dei finding (lasciato al 03 dal contratto del 01) | finding e riga `ok:` su **stdout**; il messaggio di exit 2 su **stderr** | `test_validate_exits_2_naming_lasagna_dir_when_no_project_found` usa `result.output` (stdout+stderr): resta verde |
| Messaggi di caricamento (`shell/project.py`) `problema: correzione` | formato F `problema; correzione.` | nessuno: i test del 01 asseriscono solo `line 3` e `empty` |
| Schema `pipeline.schema.json` | `entry` esce da `required`; file rigenerato dal coordinatore | la riga del 02 sui file committati torna verde dopo la rigenerazione |

Non cambiano: V01, V05, V06 (percorsi e semantica), la composizione di
`validate_project` (registry non valido → solo V01 del registry; pipeline che non
passa il modello → solo V01 della pipeline), exit code 0/1/2, `format_finding`.

### Seams

- **Core:** `lasagna.core.validate.validate_project` per V07, V10, V12 e per i messaggi;
  `lasagna.core.validate.render_json`; `lasagna.core.graph.outgoing_edges` e
  `is_forward` (T01–T02, con `lasagna.core.models.Pipeline.model_validate` per
  costruire l'oggetto); `lasagna.core.schema.render_schema` (T17).
- **Shell:** `lasagna.shell.project.load_project` (T19).
- **CLI:** `typer.testing.CliRunner().invoke(lasagna.cli.app, [...])` con la cartella
  corrente su un progetto in `tmp_path`; si asserisce su `exit_code`, `result.stdout`,
  `result.stderr` (separati: verificato con typer 0.28 installato).
- Nessun test va più in basso.

### Signatures

```python
# src/lasagna/core/models.py — cambia solo Pipeline:
class Pipeline:  entry: str | None = None      # prima: str (richiesto). Il resto invariato.

# src/lasagna/core/graph.py   (NUOVO, puro: solo stdlib e lasagna.core.models)
def is_forward(edge: Edge) -> bool: ...
    # True per DirectEdge e RouterEdge, False per LoopEdge.
def outgoing_edges(pipeline: Pipeline) -> dict[str, list[tuple[int, Edge]]]: ...
    # Una chiave per ogni id presente in `pipeline.nodes` (id ripetuto: una sola
    # chiave), nell'ordine di prima comparsa. Il valore sono le coppie
    # (indice nel file, arco) degli archi con `from` uguale a quell'id, in ordine
    # di file; vuota se non ne ha. Gli archi con `from` che non è un id di nodo non
    # compaiono. L'arco è lo stesso oggetto di `pipeline.edges[indice]`.

# src/lasagna/core/validate.py   (validate_project, format_finding, pipeline_file,
# REGISTRY_FILE: firme invariate; V07, V10, V12 si aggiungono dentro validate_project)
def render_json(findings: Sequence[Finding]) -> str: ...   # NUOVO, puro

# src/lasagna/cli.py
def validate(json_output: bool = typer.Option(False, "--json")) -> None: ...
    # il comando resta `lasagna validate`; l'opzione si chiama `--json`
```

L'implementer non cambia nomi, parametri né tipi. `graph.py` è nuovo: il ticket 06
lo estende (V08, V09, V23), quindi qui solo le due funzioni.

### Data types

- **V07 (§5, §6.1).** Si applica a ogni pipeline che passa il modello (anche con V05-id
  o V06 già segnalati, anche se `enabled: false`). Un finding V07, percorso `entry`,
  file `pipeline_file(path)`, se `pipeline.entry` è `None` (chiave assente o `null`:
  stessa cosa) oppure non è uguale **esattamente** (stringa identica, nessuna
  normalizzazione di maiuscole né spazi) all'`id` di almeno un elemento di `nodes`
  (`entry: ""` è un valore: non nomina nessun nodo, V07). Mai più di un V07 per pipeline.
  `message`: in F; se `entry` è presente contiene il valore tra apici singoli
  (`'ghost'`, `''`); se è assente non nomina un valore.
- **V10 (§5).** Per ogni id di nodo (nell'ordine di prima comparsa in `nodes`), gli
  archi in avanti sono quelli di `edges` con `from` uguale a quell'id e tipo `direct`
  o `router`, in ordine di file (i `loop` non sono archi in avanti). Se sono almeno
  due: **esattamente un** finding V10 per quel nodo, percorso `edges[j]` con `j`
  l'indice nel file del **secondo** arco in avanti, file `pipeline_file(path)`.
  `message`: in F, con l'id del nodo tra apici singoli. Gli archi con `from` che non è
  un id di nodo non partecipano (li segnala V06). Con id di nodo ripetuti (V03,
  ticket 06) il comportamento non è congelato.
- **V12 (§5).** Per ogni arco `edges[j]` di tipo `loop` con `when == "fail"`
  (confronto esatto: `Fail`, `fail ` e il testo libero non sono `fail`; il default
  `fail` conta, anche se `when` non è scritto) il cui `from` è l'id di un nodo con
  `gate is None`: **un** finding V12, percorso `edges[j]`, file `pipeline_file(path)`.
  Un gate di qualunque tipo e momento (`at: entry` compreso) vale come gate. Un `loop`
  con `from` inesistente non dà V12 (lo segnala V06). `message`: in F, con l'id del
  nodo da cui parte il loop tra apici singoli. Con id di nodo ripetuti non è congelato.
- **Ordine di applicazione** dentro una pipeline che passa il modello: V05-id, V06,
  V07, V10, V12 (l'ordine tra finding non è congelato, i test confrontano insiemi
  ordinati). Nessuna regola nasconde un'altra.
- **F, formato di ogni `message` (AC-V3-045; §5: «una frase di correzione»).**
  `<problema>; <correzione>.`: il separatore è `"; "` e la correzione è **l'ultimo**
  segmento dopo l'ultimo `"; "`; comincia con una lettera minuscola, ha almeno due
  parole e finisce con un punto. Vale per tutti i finding che `validate_project` e
  `load_project` producono, V01 di caricamento compresi (che oggi usano `: `):
  `malformed YAML at line 3; fix the syntax.` (senza posizione: `malformed YAML; fix the
  syntax.`), `empty YAML file; add the pipeline definition.`, `registry file not found;
  create .lasagna/pipelines.yaml.`. I testi sono liberi oltre a F e alle sottostringhe
  nominate dalle righe (`line 3`, `empty`, l'id o l'entry tra apici).
- **JSON di `validate --json` (AC-V3-013, §8.2).** Un oggetto con le due chiavi
  `errors` e `warnings` (sempre presenti, nell'ordine), ognuna una lista di oggetti
  con le chiavi `rule`, `file`, `path`, `message` in quest'ordine, tutte stringhe
  (`path` è `""` per un problema che riguarda tutto il file; mai `null`). `errors`
  raccoglie i finding con `level == "error"`, `warnings` quelli con `level == "warning"`,
  ciascuna lista nell'ordine di ingresso. Nessuna chiave `level`. Ricetta del testo:
  `json.dumps(doc, indent=2, ensure_ascii=False) + "\n"` (senza `sort_keys`).
- **CLI `validate [--json]`.** Sequenza invariata (radice → `load_project` → se
  `registry_loaded`, `validate_project` → unione, caricamento prima). Modalità
  umana (invariata): una riga `format_finding` per finding e, se non ci sono errori,
  la riga `ok: no problems found`, tutto su stdout; stderr vuoto. Modalità `--json`:
  su stdout **solo** `render_json(findings)` (nessuna riga `ok:`, nessuna riga umana),
  stderr vuoto. Exit code uguale nelle due modalità: 0 se nessun finding `error`, 1
  altrimenti. Nessun `.lasagna/`: exit 2 in entrambe, stdout vuoto, il messaggio
  `error: no .lasagna/ folder found here or in any parent folder` su stderr (il testo
  del §8.11 è del ticket 11). `--strict` e `validate <id>`: non qui.
- **Codifica di stdout (emendamento della review, 2026-11-10).** I byte che
  `validate` scrive su stdout, in entrambe le modalità, sono UTF-8 qualunque sia la
  codifica predefinita della piattaforma o della pipe (su Windows con stdout in
  pipe Python usa cp1252 e `--json` con un `entry` non ASCII cadrebbe in
  `UnicodeEncodeError`). Lo garantisce la shell, cioè `cli.py`, all'inizio del
  comando; `render_json` resta `ensure_ascii=False`. La conversione dei fine riga
  non è congelata (CRLF su Windows è ammesso). Test: T31.

### Error types

Stile del progetto: nessuna eccezione, `Finding`.

| Caso | Esito |
|---|---|
| `entry` assente, `null` o che non nomina un nodo | `Finding` V07 `entry` |
| nodo con due o più archi in avanti | `Finding` V10 `edges[j]` (secondo arco in avanti) |
| `loop` con `when: fail` da un nodo senza gate | `Finding` V12 `edges[j]` |
| `entry` di tipo non stringa; ogni altro errore di forma | `Finding` V01 (come nel 02) |
| `from`/`to` che non è un id di nodo | `Finding` V06 (come nel 02) |
| nessun `.lasagna/` | exit 2, messaggio su stderr (nessun `Finding`) |

### Return shape

- `validate_project` → `list[Finding]`, `[]` se tutto è valido; ogni `message` in F;
  ordine non congelato.
- `outgoing_edges` / `is_forward`: come in Signatures.
- `render_json` → `str`. Esempio esatto (T21), con `"\n"` finale e nessun `"\r"`:

```
{
  "errors": [
    {
      "rule": "V06",
      "file": "f.yaml",
      "path": "edges[0].to",
      "message": "m1"
    }
  ],
  "warnings": [
    {
      "rule": "V22",
      "file": "g.yaml",
      "path": "nodes[1]",
      "message": "m2"
    }
  ]
}
```

  Senza finding: `{`, `  "errors": [],`, `  "warnings": []`, `}` e `"\n"` finale.
- CLI: per ogni caso, stdout, stderr ed exit code come in Data types › CLI.
- `schema/pipeline.schema.json`: byte uguali a `render_schema("pipeline").encode("utf-8")`
  dopo la rigenerazione; `entry` in `properties`, non in `required`.

### External dependencies

| Dependency | How the code reaches it | How tests control it |
|---|---|---|
| File system (`.lasagna/` letto, `schema/` scritto) | `shell/project.py` (`load_project`), `shell/gen_schema.py`; `core/` mai | `tmp_path` con file scritti dal test; i file committati di `schema/` solo dalla riga del 02 |
| Cartella corrente | `Path.cwd()` solo in `cli.py` | `monkeypatch.chdir(tmp_path)` nei test e2e (non in `tests/core/`) |
| Parsing YAML | `ruamel.yaml` solo in `shell/project.py` | file veri in `tmp_path`; il carattere di controllo di T19 si scrive come byte |
| stdout, stderr, exit code | typer (`typer.echo`, `typer.Exit`) | `CliRunner`: `result.stdout`, `result.stderr`, `result.exit_code` |
| Serializzazione JSON | `json` della stdlib dentro `core/validate.py` (puro) | confronto col testo esatto e con `json.loads` |
| Codifica di stdout (locale/pipe della piattaforma) | `sys.stdout` riconfigurato in `cli.py` (shell) | T31: sottoprocesso reale (`sys.executable -c "from lasagna.cli import app; app()" validate ...`) con `PYTHONUTF8` e `PYTHONIOENCODING` tolti dall'ambiente; si decodificano i byte di stdout come UTF-8 |
| Generatore di schema | `render_schema` (pydantic) | la rigenerazione la fa il coordinatore col comando; il test confronta i byte |
| Orologio, rete, variabili d'ambiente, casualità | non usati | — |
| Sorgenti di `core/` (test di purezza) | invariato | vale anche per `core/graph.py` |

### What is NOT frozen

- Il testo dei `message` oltre a F e alle sottostringhe nominate (`line 3`, `empty`,
  l'id o l'entry tra apici); l'ordine dei finding; nomi privati e divisione in funzioni
  interne; come V10 e V12 usano `graph.py` internamente; i messaggi di `--help`;
  il testo della riga `ok:` e del messaggio di exit 2 (il §8.11 è del ticket 11);
  il comportamento con id di nodo ripetuti (V03, ticket 06); l'ordine dei file
  scritti dal generatore; la forma dello schema oltre a `entry` in `properties` e
  fuori da `required`.
- Lo schema JSON resta controllato in modo strutturale (limite noto del 02).
- Colonna del YAML malformato nei finding di caricamento (§8.11 dice «riga e
  colonna»): ticket 11.

## Out of scope

- Tutte le altre regole V, la matrice di AC-V3-007, avvisi e `--strict`
  (AC-V3-008), prestazioni (AC-V3-049): ticket 06.
- `validate <id>` e `--project` (AC-V3-046): ticket 11.

## Definition of done

- [x] every criterion has the verification the spec asks for: a test that fails on a plausible wrong implementation, a passing check, or a recorded review
- [x] whole suite green (351 passed, `uv run ruff check` clean)
- [x] changelog line under Unreleased
- [x] traceability evidence filled in the tickets index; current file updated

## Log

<!-- One line per session: date | outcome | cycles used per criterion | summary of the [lasagna] lines | notes -->

2026-11-10 | done | all 38 planned rows green after 1 attempt (T01-T38); contract gate failed once (T18: ambiguous whether the edge replaces or extends P0) and passed on the 2nd; review went back to red once (1 of 2): T31 (blocker) and T32-T38 (gaps) | contract (fail, pass) → red/green x30 → review (fail: 8 rows added) → red/green x8 → review (pass) → close | Decisions (maintainer, 2026-11-10): an absent `entry` is V07, not V01 (Pipeline.entry optional, schema regenerated); passes-immediately rule = ticket 02 rule with a declared list, plus T21 accepted as out-of-list; contract amended by the review: stdout is UTF-8 on every platform (`validate` reconfigures sys.stdout), found by the adversarial reviewer as a real UnicodeEncodeError with `--json` and a non-ASCII `entry` when stdout is piped on Windows. Choices the user sees: findings and the `ok:` line on stdout, the exit-2 message on stderr; every message is `<problem>; <fix>.` (the three loading messages of the shell were realigned); V10 is one finding per node at the second forward edge; V12 only for a `loop` whose `when` is exactly `fail` (the default counts) from a node without any gate. Passed immediately as declared (killed by mutation in review): T04, T05, T06, T08, T09, T10, T13, T14, T15, T16, T17, T18, T22, T23, T25, T26, T28, T29, T30, and the review rows T32-T38; out of the declared list, accepted by the maintainer: T21 (the implementer of T20 wrote the whole render_json recipe). Mutations: M10 and M21 first variants were equivalent/ineffective, killed by M10x and M21x; M17b killed by T36. Production code written by the coordinator: none except schema/pipeline.schema.json (regenerated with the generator command) and one revert of a mutated graph.py after a failed restore (a temporary file lock, content restored to the original and checked against a baseline hash); `ruff check --fix` on the import order of a new test file. Fixtures of tickets 01 and 02 updated in the contract node (5 files) and two 02 tests updated in the T11 row. Open gaps (not blocking, deferred): exit code with only warnings (ticket 06, when V22 exists); non-UTF-8 YAML files and the column of a malformed YAML (ticket 11, spec 8.11); a router route with `when: fail` gives no V12 (V12 covers loop edges, by contract); `validate_project` is about 110 lines and V12 keeps a redundant `gated`/`ungated` pair, to simplify when ticket 06 extends graph.py.
