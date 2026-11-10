---
status: done            # todo | in_progress | done | blocked
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
- Generatore di `schema/registry.schema.json` e `schema/pipeline.schema.json`
  (`render_schema` in `core/schema.py`, comando `python -m
  lasagna.shell.gen_schema <dir>`); i due file committati, **prodotti dal
  coordinatore creando prima la cartella `schema/` ed eseguendo il comando** nel green di T35 (l'implementer non scrive
  fuori da `src/`). Le fixture dei nodi dei test del 01 ricevono `description`
  **nel nodo contract** (fatto: 80 test verdi, ruff pulito).
- Test che valida il `.lasagna/` di questo repo e le pipeline in
  `src/lasagna/builtin/`.
- Riga in `CHANGELOG.md` sotto Unreleased.

## Files involved

- `src/lasagna/core/models.py`, `src/lasagna/core/validate.py`
- `src/lasagna/core/schema.py` (nuovo, puro: `render_schema`; scelta del contratto)
- `src/lasagna/shell/gen_schema.py` (nuovo, shell, fuori da `core/`: AC-V3-022; scelta del contratto, al posto di `scripts/`)
- `schema/registry.schema.json`, `schema/pipeline.schema.json`
- `tests/core/`, `tests/shell/`, `tests/e2e/`; fixture dei nodi del 01 (`tests/core/test_validate_v01.py`, `_v05.py`, `_v06.py`, `tests/e2e/test_validate.py`): aggiungono `description`

## Tests to pass

<!-- Filled in by the implementation pipeline (node contract) as a checklist:
one line per planned verification, in order. The green node checks off a test
with `[x] (green after N)`; the review node checks off checks and reviews. -->

Regola per questo ticket (maintainer, 2026-11-09): se un test pianificato passa
subito perché il comportamento esiste già (portato da una riga precedente), lo
spunto con la nota `passes immediately` e proseguo senza fermarmi, **purché sia
nell'elenco qui sotto e verificato con la mutazione indicata**. Mi fermo su un
passa-subito che non è nell'elenco, o se il test non verifica nulla. L'elenco
dei passa-subito va nel Log di chiusura.

Passa-subito attesi (dall'ordine delle righe; ognuno è ucciso dalla mutazione
indicata): T06 (M07), T12 (M05), T13 (M15), T14 (M16), T17 (M09), T18 (M09),
T19 (M04), T20 solo la parte `loop` (M08), T22 (M07), T24 (M01), T26 (M01),
T27 (M01), T28 (M13), T29 (M01), T31 (M11), T36–T44 (M12). Le righe di
integrazione T36–T44 sommano i comportamenti delle righe precedenti e sono
integrazione per costruzione.

**Convenzioni di tutte le righe** (`validate_project` è il seam):
- Fixture base: registry `R0 = {"lasagna": "3.0", "pipelines": [{"id": "demo", "path": "pipelines/demo"}]}`;
  pipeline `P0 = {"lasagna": "3.0", "id": "demo", "entry": "a", "nodes": [{"id": "a", "description": "A"}, {"id": "b", "description": "B"}], "edges": [{"type": "direct", "from": "a", "to": "b"}]}`.
  Ogni riga parte da `R0`/`P0`, cambia solo ciò che dice, e chiama `validate_project(R, {"pipelines/demo": P})`.
  Un oggetto di una riga che non sta in `P0` (una risorsa, un gate, un arco) si aggiunge al nodo `a` (campo `resources`, `gate`) o a `edges` (in coda: indice 1).
- `RF = ".lasagna/pipelines.yaml"`; `PF = ".lasagna/pipelines/demo/pipeline.yaml"`.
- «→ `[]`» = la funzione restituisce `[]`.
- «→ V01 `p`» = restituisce **esattamente un** finding con `(rule, file, path) == ("V01", PF, "p")`; per un percorso nel registry (comincia con `pipelines[` o è una chiave radice del registry) il file è `RF`, e la riga lo dice con `(RF)`.
  «→ V01 `p`, `q`» = esattamente due finding, uno per percorso.
- Una riga con più casi separati da «;» è **parametrizzata**: un caso di test per caso (id di parametro), non un solo test con molte asserzioni.
- Ogni test cita il suo criterio in un commento `# AC-V3-NNN`; nessun mock e nessun `monkeypatch` in `tests/core/`.
- Le fixture dei nodi dei test del 01 hanno già `description` (modifica fatta nel nodo contract, suite verde).

Nodo, risorsa, gate
- [x] (green after 1) T01 AC-V3-005 · `tests/core/test_models_node.py`: nodo senza `description` → V01 `nodes[0].description`.
- [x] (green after 1) T02 AC-V3-005 · `started_by: "agent"` → `[]`; `"human"` → `[]`; `"robot"` → V01 `nodes[0].started_by`.
- [x] (green after 1) T03 AC-V3-005 · `steps: ["a", "b"]` → `[]`; `steps: "a"` → V01 `nodes[0].steps`; `steps: ["a", 3]` → V01 `nodes[0].steps[1]`.
- [x] (green after 1) T04 AC-V3-005 · risorsa: `{type: "path", ref: "src/", access: "write", required: false, description: "d"}` → `[]`; `{type: "notion_page", ref: "x", description: "d"}` → `[]`; `{type: "doc", ref: "x"}` → `[]`; `access: "execute"` → V01 `nodes[0].resources[0].access`; senza `ref` → V01 `nodes[0].resources[0].ref`; senza `type` → V01 `nodes[0].resources[0].type`; `required: "no"` → V01 `nodes[0].resources[0].required`; `ref: 3` → V01 `nodes[0].resources[0].ref`.
- [x] (green after 1) T05 AC-V3-005 · gate: `{type: "human", message: "m"}` → `[]`; `{type: "check", run: "r"}` → `[]`; `{type: "agent", criteria: ["c"], by: "subagent", at: "entry"}` → `[]`; `{type: "agent", criteria: ["c"], by: "self", at: "exit"}` → `[]`; `type: "robot"` → V01 `nodes[0].gate.type`; senza `type` → V01 `nodes[0].gate.type`; `at: "middle"` → V01 `nodes[0].gate.at`; `by: "nobody"` → V01 `nodes[0].gate.by`; `criteria: "c"` → V01 `nodes[0].gate.criteria`; `criteria: [1]` → V01 `nodes[0].gate.criteria[0]`.
- [x] (passes immediately, expected in the declared list; killed by M07 in review) T06 AC-V3-005 · il modello non giudica la forma per tipo di gate (V14 è del ticket 06): `{type: "human"}`, `{type: "check"}`, `{type: "agent"}`, `{type: "human", run: "r", criteria: ["c"]}` (campi di un altro tipo) → `[]`.

Pipeline e registry
- [x] (green after 1) T07 AC-V3-005 · `params: {"p": {"default": "d", "description": "x"}}` → `[]`; `{"p": {"default": "d"}}` → `[]`; `{"p": {"description": "x"}}` → V01 `params.p.default`; `{"p": {"default": 3}}` → V01 `params.p.default`; `{"loop": {"default": 3}}` → V01 `params.loop.default` (un parametro che si chiama come un tipo di arco non deve perdere il segmento).
- [x] (green after 1) T08 AC-V3-005 · `inputs: {"i": {"description": "d", "required": false}}` → `[]`; `{"i": {}}` → `[]`; `{"i": {"required": "false"}}` → V01 `inputs.i.required`.
- [x] (green after 1) T09 AC-V3-005 · `outputs: {"o": {"description": "d"}}` → `[]`; `{"o": {}}` → `[]`; `{"o": {"description": 3}}` → V01 `outputs.o.description`.
- [x] (green after 1) T10 AC-V3-005 · voce del registry con `source: {"from": "builtin:demo", "version": "1.0.0"}` → `[]`; `source: {"from": "src/x"}` → `[]`; `source: {"version": "1.0.0"}` → V01 `pipelines[0].source.from` (RF); `source: {"from": "x", "version": 1}` → V01 `pipelines[0].source.version` (RF).
- [x] (green after 1) T11 AC-V3-005 · voce con `params: {"tickets_dir": "t"}` → `[]`; `{"tickets_dir": 3}` → V01 `pipelines[0].params.tickets_dir` (RF); `params: ["a"]` → V01 `pipelines[0].params` (RF).
- [x] (green after 1; 3 of 5 cases passed immediately, expected in the declared list, M05) T12 AC-V3-005 · booleani rigidi (modo strict): `enabled: false` → `[]`; `enabled: "false"` → V01 `pipelines[0].enabled` (RF); registry con `agent_can_edit_pipelines: true` → `[]`; con `"yes"` → V01 `agent_can_edit_pipelines` (RF); registry con `project: "x"` e senza `pipelines` → `[]`.
- [x] (passes immediately, expected in the declared list; killed by M15 in review) T13 AC-V3-005 · assente ≠ `null`, escluso gli archi: `project: None` nel registry → `[]`; `name: None` e `description: None` nel pipeline → `[]`; `source: None` → `[]`; `enabled: None` → V01 `pipelines[0].enabled` (RF); nodo con `steps: None` → V01 `nodes[0].steps`; `started_by: None` → V01 `nodes[0].started_by`.
- [x] (passes immediately, expected in the declared list; killed by M16 in review) T14 AC-V3-005 · il vuoto è valido per la forma (non equivale ad assente), esclusi gli archi: nodo con `description: ""` → `[]`; `steps: []` → `[]`; risorsa con `ref: ""` → `[]`; gate agent con `criteria: []` → `[]`; `edges: []` → `[]`; `nodes: []` insieme a `edges: []` → `[]` (con l'arco di `P0` sarebbero due V06).

Archi (le righe T15–T22 usano archi di tipo diverso da `direct`, che nascono qui)
- [x] (green after 1) T15 AC-V3-005 · arco `loop` (in posizione 1, `{type: "loop", from: "b", to: "a", ...}`): `max_iterations: 3` senza `when` → `[]`; con `when: "fail"` → `[]`; `"pass"` → `[]`; `"free text condition"` → `[]`; `max_iterations: 0` → `[]` (V11 è del ticket 06); senza `max_iterations` → V01 `edges[1].max_iterations`; `max_iterations: "3"` → V01 `edges[1].max_iterations`; `True` → idem; `2.5` → idem; `when: None` → V01 `edges[1].when`. Il percorso **non** contiene il nome del tipo di arco.
- [x] (green after 1) T16 AC-V3-005 · arco `router` (in posizione 1): `{type: "router", from: "a", decided_by: "agent", routes: [{when: "w", to: "b"}, {when: "w2", to: "a"}], default: "b"}` → `[]`; `decided_by: "human"` → `[]`; `decided_by: "check"` con route `{run: "r", to: "b"}` → `[]`; senza `default` → `[]`; `routes: []` → `[]` (V13 è del ticket 06); `decided_by: "robot"` → V01 `edges[1].decided_by`; senza `routes` → V01 `edges[1].routes`; route senza `to` → V01 `edges[1].routes[0].to`; route con `when: 3` → V01 `edges[1].routes[1].when`.
- [x] (passes immediately, expected in the declared list; killed by M09 in review) T17 AC-V3-005 · una chiave di un altro tipo di arco è sconosciuta: `direct` con `when: "fail"` → V01 `edges[0].when`; `direct` con `max_iterations: 1` → V01 `edges[0].max_iterations`; `router` con `to: "b"` → V01 `edges[1].to`; `loop` con `routes: []` → V01 `edges[1].routes`.
- [x] (green after 1; not a passes-immediately after all) T18 AC-V3-005 · tipo di arco non valido → un solo V01 con percorso `edges[0].type`: `type: "teleport"`; senza `type`; `type: 3`.
- [x] (passes immediately, expected in the declared list; killed by M04 in review) T19 AC-V3-005 · `from_` al posto di `from` (l'alias non si ammette col nome Python): arco `direct` `{type: "direct", from_: "a", to: "b"}` → esattamente due V01: `edges[0].from` e `edges[0].from_`; `source: {"from_": "x"}` (RF) → esattamente due V01: `pipelines[0].source.from` e `pipelines[0].source.from_`.
- [x] (passes immediately, expected in the declared list; killed by M08 in review) T20 AC-V3-003 · V06 sugli archi `loop`: `from` e `to` inesistenti (arco in posizione 1) → due V06 con percorsi `edges[1].from` e `edges[1].to`, file `PF`.
- [x] (green after 1; 2 of 4 cases passed immediately, negatives killed by M08) T21 AC-V3-003 · V06 sugli archi `router`: `from` inesistente → un V06 `edges[1].from`; route in posizione 1 con `to` inesistente → un V06 `edges[1].routes[1].to`; route valide → `[]`; `default: "ghost"` con route valide → `[]` (V06 non guarda `default`: è V13, ticket 06).
- [x] (passes immediately, expected in the declared list; killed by M07 in review) T22 AC-V3-005 · il modello non giudica ciò che spetta alle regole V con ID: pipeline con `lasagna: "9.9"` (V02); nodo `b` con `id: "Bad_ID"`, con l'arco di `P0` che lo cita allo stesso modo (V03); `version: "banana"` (V04); `entry: "ghost"` (V07); `router` con una sola route (V13); → in ogni caso `[]`.

Chiavi `x-*` (AC-V3-006). I **14 oggetti a chiavi fisse**: `Registry` (radice di `R`), `RegistryEntry` (`pipelines[0]`), `Source` (`pipelines[0].source`), `Pipeline` (radice di `P`), `ParamDef` (`params.p`), `InputDef` (`inputs.i`), `OutputDef` (`outputs.o`), `Node` (`nodes[0]`), `Resource` (`nodes[0].resources[0]`), `Gate` (`nodes[0].gate`), `DirectEdge` (`edges[0]`), `LoopEdge` (`edges[1]`), `RouterEdge` (`edges[1]`), `Route` (`edges[1].routes[0]`). Per ognuno la riga costruisce l'oggetto minimo valido.
- [x] (green after 1) T23 AC-V3-006 · `x-foo: "v"` aggiunta a ciascuno dei 14 oggetti → `[]` (un caso per oggetto).
- [x] (passes immediately, expected in the declared list; killed by M01 in review) T24 AC-V3-006 · il valore di una `x-*` è libero: `"s"`, `3`, `True`, `None`, `[1, "a"]`, `{"k": {"n": [None]}}` nel nodo → `[]`.
- [x] (green after 1) T25 AC-V3-006 · `x-foo` **come nome** in una mappa a chiavi scelte dall'utente → esattamente un V01, con il nome nel percorso: `params.x-foo` (valore `{"default": "d"}`); `inputs.x-foo` (valore `{}`); `outputs.x-foo` (valore `{}`); `pipelines[0].params.x-foo` (valore `"v"`, RF); il percorso è quello scritto, es. `params.x-foo`.
- [x] (passes immediately, expected in the declared list; killed by M01 in review) T26 AC-V3-006 · una chiave sconosciuta `bogus` aggiunta a ciascuno dei 14 oggetti è V01 con la chiave in fondo al percorso (`bogus`, `pipelines[0].bogus`, `pipelines[0].source.bogus`, `bogus`, `params.p.bogus`, `inputs.i.bogus`, `outputs.o.bogus`, `nodes[0].bogus`, `nodes[0].resources[0].bogus`, `nodes[0].gate.bogus`, `edges[0].bogus`, `edges[1].bogus`, `edges[1].bogus`, `edges[1].routes[0].bogus`; il file è `RF` per i primi tre).
- [x] (passes immediately, expected in the declared list; killed by M01 in review) T27 AC-V3-006 · quasi-`x-`: `X-foo`, `x_foo`, `xfoo`, `x` nella radice del pipeline → V01 con la chiave come percorso; `x-` (solo il prefisso) → `[]`.
- [x] (passes immediately, expected in the declared list; killed by M13 in review) T28 AC-V3-006 · chiave non stringa (`{1: "a"}` aggiunta alla radice del pipeline) → un solo V01 con `file == PF`, nessuna eccezione; il `path` non è congelato.
- [x] (passes immediately, expected in the declared list; killed by M01 in review) T29 AC-V3-006 · le `x-*` non entrano nel modello: `Registry.model_validate(R)` e `Pipeline.model_validate(P)` con `x-foo` in tutti i 14 oggetti → `model_dump()` non contiene, a nessuna profondità, una chiave che inizia con `x-`.

JSON Schema (AC-V3-014). I due schemi si caricano con `json.loads(render_schema(kind))`. Nello schema `registry`: la radice è `Registry`, in `$defs` ci sono `RegistryEntry` e `Source`. Nello schema `pipeline`: la radice è `Pipeline`, in `$defs` ci sono `ParamDef`, `InputDef`, `OutputDef`, `Node`, `Resource`, `Gate`, `DirectEdge`, `LoopEdge`, `RouterEdge`, `Route`.
- [x] (green after 1) T30 AC-V3-014 · `tests/core/test_schema.py`: `render_schema("registry")` e `render_schema("pipeline")` → una `str` che termina con esattamente un `"\n"`, senza `"\r"`, il cui `json.loads` ha `title` `"Registry"` / `"Pipeline"`, e che è identica a `json.dumps(json.loads(testo), indent=2, sort_keys=True, ensure_ascii=False) + "\n"`.
- [x] (passes immediately, expected in the declared list; killed by M11 in review) T31 AC-V3-014 · nello schema `pipeline` le definizioni `DirectEdge`, `LoopEdge`, `RouterEdge` hanno `from` in `properties` e in `required`, e nessun oggetto dello schema ha `from_` in `properties`; nello schema `registry`, `Source` ha `from` in `properties` e in `required` e nessun `from_`.
- [x] (green after 1) T32 AC-V3-014 · ognuno dei 14 oggetti (radice o `$defs[<classe>]`, nello schema dove vive) ha `patternProperties == {"^x-": {}}` e `additionalProperties is False`.
- [x] (green after 1) T33 AC-V3-014 · mappe a chiavi scelte dall'utente: `properties["params"]`, `properties["inputs"]`, `properties["outputs"]` nella radice dello schema `pipeline` e `properties["params"]` in `$defs["RegistryEntry"]` dello schema `registry` hanno `propertyNames == {"not": {"pattern": "^x-"}}`.
- [x] (green after 1) T34 AC-V3-014 · `tests/e2e/test_gen_schema.py`: `subprocess.run([sys.executable, "-m", "lasagna.shell.gen_schema", str(out)], cwd=tmp_path)` con `out` cartella esistente in `tmp_path` → exit 0; `out` contiene `registry.schema.json` e `pipeline.schema.json` e nient'altro; i loro **byte** sono uguali a `render_schema(kind).encode("utf-8")` (quindi LF anche su Windows).
- [x] (green after 1; files produced by the coordinator with the regeneration command) T35 AC-V3-014 · stesso file di T34: i file committati `<repo>/schema/registry.schema.json` e `<repo>/schema/pipeline.schema.json` (`Path(__file__).parents[2] / "schema"`), letti come **byte**, sono uguali a `render_schema(kind).encode("utf-8")`. Il green di questa riga è creare `schema/` ed eseguire il comando di rigenerazione (a cura del coordinatore, vedi Changes): al nodo green l'implementer riceve l'istruzione di fermarsi dopo aver consegnato `render_schema` e `gen_schema`, perché T35 non si chiude con codice suo.

Integrazione (passano subito per costruzione: vedi la regola in testa)
- [x] (passes immediately, integration row in the declared list; killed by M12 in review) T36 §11.2.5 · `tests/shell/test_self_validation.py`: `load_project(<repo>)` (`Path(__file__).parents[2]`): `registry_loaded is True`, `findings == ()`, le chiavi di `pipelines` sono esattamente `{"pipelines/project-manager", "pipelines/implementation", "pipelines/quick-fix"}` e nessun valore è `None`; `validate_project(data.registry, data.pipelines) == []`.
- [x] (passes immediately, integration row in the declared list; killed by M12 in review) T37 §11.2.5 · stesso file: le pipeline di `<repo>/src/lasagna/builtin/*/pipeline.yaml` (gli id letti dai nomi delle cartelle devono essere esattamente `{"project-manager", "implementation", "quick-fix"}`, altrimenti il test fallisce) si copiano in un progetto in `tmp_path` (`.lasagna/pipelines/<id>/pipeline.yaml` e un `.lasagna/pipelines.yaml` con `lasagna: "3.0"` e una voce `{id, path: pipelines/<id>}` per id) e si caricano con `load_project`: stesse asserzioni di T36.
- [x] (passes immediately, integration row in the declared list; killed by M12 in review) T38 AC-V3-005 · `tests/shell/test_spec_blocks.py`: il registry del §4.3 con la pipeline del §10.1 come `pipelines/project-manager` → `validate_project(...) == []` (blocchi estratti dalla spec: vedi Contract › Return shape).
- [x] (passes immediately, integration row in the declared list; killed by M12 in review) T39 AC-V3-005 · il registry del §11.1 con le pipeline dei §10.1, §10.2, §10.3 (chiavi `pipelines/project-manager`, `pipelines/implementation`, `pipelines/quick-fix`) → `[]`.
- [x] (passes immediately, integration row in the declared list; killed by M12 in review) T40 AC-V3-005 · frammento del §4.4: la mappa estratta, con `nodes` ed `edges` sostituiti da `[{"id": "a", "description": "A"}]` e `[]`, con `entry` sostituito da `"a"` e con `id` sostituito da `demo`, come pipeline `pipelines/demo` di `R0` → `[]`.
- [x] (passes immediately, integration row in the declared list; killed by M12 in review) T41 AC-V3-005 · frammento del §4.5 (lista con un nodo `green`): il nodo, in una pipeline `{lasagna: "3.0", id: "demo", entry: <id del nodo>, nodes: [nodo]}` → `[]`.
- [x] (passes immediately, integration row in the declared list; killed by M12 in review) T42 AC-V3-005 · frammento del §4.6 (mappa con `edges`: un `direct`, un `loop`, un `router`): in una pipeline `demo` i cui nodi (con `description`) sono tutti gli id citati (`from`, `to`, `to` delle route, `default`), con `entry` il primo id citato e `edges` il frammento → `[]`.
- [x] (passes immediately, integration row in the declared list; killed by M12 in review) T43 AC-V3-005 · frammento del §4.7 (lista con una risorsa): la risorsa dentro un nodo → `[]`.
- [x] (passes immediately, integration row in the declared list; killed by M12 in review) T44 AC-V3-005 · frammento del §4.8 (mappa con `gate`; `type` è la stringa `human | check | agent`, che non è un valore): il gate con `type` sostituito, in tre casi, da `human`, `check`, `agent` (gli altri campi restano: `at`, `message`, `run`, `criteria`, `by`), dentro un nodo → `[]` in ognuno.

Mutazioni da provare nel nodo review (ognuna: modifica temporanea del codice di produzione → i test indicati falliscono → si ripristina; evidenza nella riga)
- [x] (evidence: each of Gate, Resource, RouterEdge, Route, ParamDef, Source made to keep x-* → 2 failed each: test_extension_key_is_accepted_in_every_fixed_key_object (T23) and test_extension_keys_never_enter_the_model (T29); reverted) M01 AC-V3-006 · togliere l'ammissione di `x-*` a un solo oggetto per volta (Gate, Resource, RouterEdge, Route, ParamDef, Source) → T23, T24, T26, T27, T29 falliscono in modo coerente (T23 sempre).
- [x] (evidence: UserKey = str → 4 failed (T25, all four maps); reverted) M02 AC-V3-006 · lasciar passare `x-foo` come nome in `params` (pipeline), poi in `inputs`, poi in `pipelines[0].params` → T25 fallisce.
- [x] (evidence: Gate without patternProperties → T32 and T35 fail; Gate with extra=ignore → T32, T26 (Gate) and T35 fail; reverted) M03 AC-V3-014 · togliere `patternProperties` da un solo oggetto dello schema; togliere `additionalProperties: false` da uno → T32 fallisce.
- [x] (evidence: populate_by_name=True on Source and DirectEdge → T19 (both cases) and the Source row of T10 fail; reverted) M04 AC-V3-005 · `populate_by_name=True` sugli archi e su `Source` → T19 fallisce.
- [x] (evidence: strict removed from the base → 6 failed (T12, T15, T04, T08); reverted) M05 AC-V3-005 · togliere `strict` (modo lax) → T12, T15 falliscono.
- [x] (evidence: Node.description optional → T01 and T35 fail; reverted) M06 AC-V3-005 · `Node.description` opzionale → T01 fallisce.
- [x] (evidence: max_iterations ge=1 → T15 fails; id pattern on Node → T22 fails; message required for human gate → T06 (plus T23/T29) fail; reverted) M07 AC-V3-005 · codificare un vincolo che è di un'altra regola (`message` obbligatorio per il gate `human`; `max_iterations` con `ge=1`; `id` con pattern) → T06, T15, T22 falliscono.
- [x] (evidence: router skipped in V06 → T21 fails (plus crash-dependent rows); router default checked → T21 fails; loop skipped → T20 fails; reverted) M08 AC-V3-003 · V06 che salta le route dei router; V06 che controlla anche `default`; V06 che ignora gli archi `loop` → T21 (e T20) falliscono.
- [x] (evidence: type tag kept in the path → 18 failed (T15, T17, T16, T19, T26...); tag stripped anywhere → T07 (params.loop.default) fails; reverted) M09 AC-V3-005 · il percorso V01 degli archi che contiene il nome del tipo (`edges[1].loop.max_iterations`); lo stripping di **ogni** segmento chiamato `loop`/`direct`/`router` (rompe il parametro `loop`) → T15, T17, T18 falliscono (T07 per lo stripping troppo largo).
- [x] (evidence: extra field in Node without regenerating → T35 fails; one byte changed in pipeline.schema.json → T35 fails; both reverted) M10 AC-V3-014 · aggiungere un campo a `Node` senza rigenerare → T35 fallisce; cambiare un byte di uno dei due file committati → T35 fallisce.
- [x] (evidence: write_text (CRLF on Windows) → T34 fails; by_alias=False → T31 (and T35) fail; sort_keys=False → T30 (and T35) fail; reverted) M11 AC-V3-014 · lo script che scrive in modalità testo (CRLF su Windows) → T34 fallisce; `by_alias=False` → T31 fallisce; senza `sort_keys` → T30 fallisce.
- [x] (evidence: required foo: str in Pipeline → 155 failed incl. T36–T44; reverted) M12 AC-V3-005 · aggiungere un campo obbligatorio `foo: str` a `Pipeline` → T36–T44 falliscono (le righe di integrazione sono vive).
- [x] (evidence: k.startswith on a non-str key → T28 fails; reverted) M13 AC-V3-006 · una rimozione di `x-*` che solleva su una chiave intera → T28 fallisce.
- [x] (evidence: propertyNames removed → T33 fails (4 cases); reverted) M14 AC-V3-014 · togliere `propertyNames` da una delle quattro mappe → T33 fallisce.
- [x] (evidence: enabled: bool | None and when: str | None → T13 and T15 fail; reverted) M15 AC-V3-005 · `enabled: bool | None`, `when: str | None` (None accettato dove il default non è None) → T13, T15 falliscono.
- [x] (evidence: Node.description min_length=1 → T14 fails; reverted) M16 AC-V3-005 · `description: str = Field(min_length=1)` (il vuoto trattato come assente) → T14 fallisce.

Check del nodo review
- [x] (evidence: uv run pytest 264 passed; uv run ruff check All checks passed (after fixing an unsorted import, a subprocess check= argument in a test and the field order of Pipeline; schema hash unchanged)) C01 · `uv run pytest` verde e `uv run ruff check` pulito.
- [x] (evidence: sha256 of schema/*.json identical before and after `uv run python -m lasagna.shell.gen_schema schema` (2026-11-10)) C02 AC-V3-014 · `sha256` dei due file in `schema/` prima e dopo `uv run python -m lasagna.shell.gen_schema schema` (dalla radice del repo) uguale.
- [x] (evidence: clean copy of tracked+new files without .venv (2026-11-10): uv sync ok; uv run pytest 264 passed; uv run ruff check All checks passed) C03 AC-V3-005 (check) · copia pulita dell'albero (file tracciati e nuovi, senza `.venv/`): `uv sync && uv run pytest && uv run ruff check` escono 0.

## Contract

<!-- Filled in by the implementation pipeline (node contract), from its
contract template. -->

Questo contratto **sostituisce** i punti del contratto del 01 che riguardano i
modelli (Signatures di `Node`, `Edge`, `Pipeline`, `Registry`, `RegistryEntry`,
«Data types» su `Edge.type` e su `x-*`, il «modo lax»). Restano validi, senza
cambiare: `Finding`, `REGISTRY_FILE`, `pipeline_file`, `format_finding`,
`ProjectData`, `find_project_root`, `load_project`, la CLI, le regole di
composizione di `validate_project` (registry non valido → solo V01 del registry;
pipeline non valida → solo V01 della pipeline) e la regola V05.

### Cosa cambia rispetto al 01

| Limite dichiarato nel 01 | Esito in questo ticket | Test del 01 da aggiornare |
|---|---|---|
| archi `loop` e `router` danno V01 | sono validi (T15–T16); V06 li copre (T20–T21) | nessuno li asserisce |
| chiavi `x-*` danno V01 | ammesse nei 14 oggetti a chiavi fisse, V01 come nome nelle mappe (T23–T29) | nessuno le asserisce |
| `Node` con solo `id` | `description` è **obbligatoria** (§4.5): un nodo senza è V01 (T01) | le fixture dei nodi di `test_validate_v01.py`, `_v05.py`, `_v06.py` e `tests/e2e/test_validate.py` hanno ricevuto `description` **nel nodo contract** (suite verde: 80 passed) |
| modo pydantic lax | modo **strict** su tutti i modelli (T12, T15) | nessuno: i test del 01 non coercono (quotano `lasagna: "3.0"`) |
| `Edge` classe unica, `populate_by_name=True` | tre classi, alias `from` **solo** con quel nome (T19) | nessuno usa `from_` |

### Seams

- **Core:** `lasagna.core.validate.validate_project(registry, pipelines)` per
  tutto il comportamento dei modelli (i modelli si osservano come finding V01,
  e come `[]` quando validi). Le classi `lasagna.core.models.Registry` e
  `Pipeline` solo per T29 (`model_validate`, `model_dump`).
- **Core, schema:** `lasagna.core.schema.render_schema(kind)`.
- **Shell:** `lasagna.shell.project.load_project` (auto-validazione, T36–T37).
- **Generatore:** `python -m lasagna.shell.gen_schema <OUT_DIR>` eseguito come
  processo (T34–T35).
- Nessun test va più in basso (niente funzioni private, niente campi interni
  di pydantic).

### Signatures

```python
# src/lasagna/core/models.py — tutti i modelli: ConfigDict(extra="forbid", strict=True),
# populate_by_name NON attivo. Nomi di classe e di campo congelati (le classi sono
# le chiavi di `$defs` dello schema JSON). `Finding` è invariato.
# Un campo senza default è RICHIESTO: se manca è V01. Solo i limiti di valore sono
# delle regole V (vedi Data types).
class Registry:       lasagna: str
                      project: str | None = None
                      agent_can_edit_pipelines: bool = False
                      pipelines: list[RegistryEntry] = []
class RegistryEntry:  id: str; path: str
                      enabled: bool = True
                      source: Source | None = None
                      params: dict[str, str] = {}          # solo stringhe (§4.3)
class Source:         from_: str  (alias "from")           # `builtin:<id>` o percorso
                      version: str | None = None
class Pipeline:       lasagna: str; id: str; entry: str; nodes: list[Node]
                      name: str | None = None; version: str | None = None
                      description: str | None = None
                      params: dict[str, ParamDef] = {}
                      inputs: dict[str, InputDef] = {}
                      outputs: dict[str, OutputDef] = {}
                      edges: list[Edge] = []
class ParamDef:       default: str; description: str | None = None
class InputDef:       description: str | None = None; required: bool = True
class OutputDef:      description: str | None = None
class Node:           id: str
                      description: str                     # obbligatoria (§4.5)
                      name: str | None = None
                      started_by: Literal["agent", "human"] = "agent"
                      steps: list[str] = []
                      resources: list[Resource] = []
                      gate: Gate | None = None
class Resource:       type: str                            # tipo aperto: `notion_page` è ammesso
                      ref: str
                      access: Literal["read", "write"] = "read"
                      required: bool = True
                      description: str | None = None
class Gate:           type: Literal["human", "check", "agent"]
                      at: Literal["entry", "exit"] = "exit"
                      message: str | None = None
                      run: str | None = None
                      criteria: list[str] | None = None
                      by: Literal["self", "subagent"] = "self"
class DirectEdge:     type: Literal["direct"]; from_: str (alias "from"); to: str
class LoopEdge:       type: Literal["loop"]; from_: str (alias "from"); to: str
                      when: str = "fail"
                      max_iterations: int                  # richiesto (§4.6 «obbligatorio»); ≥ 1 è V11
class RouterEdge:     type: Literal["router"]; from_: str (alias "from")
                      decided_by: Literal["agent", "human", "check"]
                      routes: list[Route]
                      default: str | None = None
class Route:          to: str; when: str | None = None; run: str | None = None
Edge = Annotated[DirectEdge | LoopEdge | RouterEdge, Field(discriminator="type")]

# src/lasagna/core/schema.py   (NUOVO, puro: solo stdlib e pydantic)
def render_schema(kind: Literal["registry", "pipeline"]) -> str: ...
    # kind "registry" → Registry, "pipeline" → Pipeline. Ricetta congelata:
    # json.dumps(Model.model_json_schema(mode="validation", by_alias=True),
    #            indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    # Le aggiunte di x-* allo schema vivono nei modelli, non qui. Nessun'altra
    # post-elaborazione, nessun `$schema`.

# src/lasagna/shell/gen_schema.py   (NUOVO, shell: scrive file; FUORI da `core/`: AC-V3-022)
def write_schema(out_dir: Path) -> None: ...
    # scrive `registry.schema.json` e `pipeline.schema.json` in `out_dir` (che
    # esiste), contenuto = render_schema(kind), codifica UTF-8 e fine riga LF
    # scritti esplicitamente (scrittura di byte, o newline="\n"). Nessun altro file.
def main(argv: Sequence[str] | None = None) -> int: ...
    # uso: python -m lasagna.shell.gen_schema OUT_DIR   (OUT_DIR obbligatorio;
    # senza: exit diverso da 0, non congelato). Chiama write_schema, exit 0.
    # Il modulo ha `if __name__ == "__main__": raise SystemExit(main())`.
    # Comando di rigenerazione dei file committati, dalla radice del repo:
    #   uv run python -m lasagna.shell.gen_schema schema

# src/lasagna/core/validate.py   (cambiano solo V06 e la conversione dei percorsi)
# validate_project, format_finding, pipeline_file, REGISTRY_FILE: firme invariate.
```

L'implementer non cambia nomi, parametri né tipi. Dove scrive chi: i file in
`src/` li scrive l'implementer (compreso `shell/gen_schema.py`); i due file
`schema/*.json` **non sono scrivibili dall'implementer** (fuori da `source_dir`)
e li produce il coordinatore eseguendo il comando di rigenerazione nel green di
T35 (non si scrivono a mano); `tests/` li scrive il test-writer.

### Data types

- **Assente, `null` e vuoto sono tre cose diverse.** `None` nei campi `X | None`
  significa «chiave assente»; un `null` YAML esplicito su un campo `X | None` è
  accettato ed equivale ad assente. Su un campo il cui default non è `None`
  (`enabled`, `required`, `steps`, `resources`, `params`, `started_by`, `access`,
  `at`, `by`, `when`, `edges`, …) un `null` è V01. Un campo richiesto assente è
  V01. Il vuoto (`""`, `[]`, `{}`) è **valido per la forma**: lo giudicano
  eventuali regole V con ID, non i modelli (T13, T14, T16).
- **Modo strict.** Nessuna coercione: un intero dove serve una stringa, una
  stringa dove serve un booleano o un intero (`"false"`, `"3"`), un booleano dove
  serve un intero (`True` per `max_iterations`), un float dove serve un intero
  sono V01. Le stringhe dei test che devono restare stringhe si quotano.
- **Registry `params` e `default` dei param sono stringhe** (si inseriscono nei
  testi: D9). Un numero senza virgolette (`retries: 3`) è V01: è una scelta che
  l'utente vede, indicata al gate umano di chiusura.
- **Chiavi `x-*` (§4.3).** Una chiave è `x-*` se è una `str` che inizia con i
  due caratteri `x-` (`x-` da solo compreso; `X-foo`, `x_foo`, `xfoo`, `x` no).
  - **Ammesse**, con qualunque valore YAML (anche `null`, liste, mappe annidate
    qualunque), e **scartate** dal modello (non compaiono in `model_dump()`), in
    **tutti i 14 oggetti a chiavi fisse**: `Registry`, `RegistryEntry`, `Source`,
    `Pipeline`, `ParamDef`, `InputDef`, `OutputDef`, `Node`, `Resource`, `Gate`,
    `DirectEdge`, `LoopEdge`, `RouterEdge`, `Route`. *(Decisione del maintainer,
    2026-11-09: il §4.3 elenca sette oggetti, il resto della documentazione dice
    «oggetti a chiavi fisse»; si segue quest'ultimo, come `rules.md` §3.)*
  - **V01 come nome** (percorso con la chiave) nelle quattro mappe a chiavi
    scelte dall'utente: `Pipeline.params`, `Pipeline.inputs`, `Pipeline.outputs`,
    `RegistryEntry.params` (T25). `x-foo` *dentro* una definizione (`params.p`)
    è invece un'estensione ammessa (T23).
  - Una chiave **non stringa** (es. `1`) in un oggetto a chiavi fisse non è mai
    `x-*`: è un V01 e non solleva eccezioni (T28).
- **Alias `from`.** Il nome YAML è `from`; l'attributo Python è `from_`. `from_`
  scritto nel YAML è una chiave sconosciuta (T19).
- **JSON Schema, rappresentazione di `x-*`.** Dallo schema di ognuno dei 14
  oggetti: `"additionalProperties": false` e `"patternProperties": {"^x-": {}}`.
  Le quattro mappe a chiavi utente hanno `"propertyNames": {"not": {"pattern":
  "^x-"}}`. Nello schema una proprietà si chiama `from`, mai `from_`. La radice
  dello schema è l'oggetto del modello radice (`Registry`/`Pipeline`); gli altri
  sono in `$defs` con il nome della classe, nello schema in cui vivono (elenco in
  Tests to pass › JSON Schema). Gli archi sono `oneOf` discriminato da `type` (la
  forma esatta di pydantic non è congelata, solo le tre definizioni in `$defs`).
- **Percorsi YAML dei V01 (rinnova e completa il 01).** Chiavi con `.`, indici
  `[n]` base 0, mai segmenti che non sono nel file: né il nome del tipo di arco
  (`edges[1].max_iterations`, non `edges[1].loop.max_iterations`), né il segno
  `[key]` che pydantic usa per gli errori sulle chiavi di una mappa
  (`params.x-foo`). Si toglie solo il segmento del tipo di arco che pydantic
  inserisce dopo l'indice di un arco: un parametro o una chiave che si chiama
  `loop` resta (`params.loop.default`). Un arco con `type` mancante o
  sconosciuto ha percorso `edges[n].type`.
- **Regole V non codificate nei modelli** (sono dei ticket 03 e 06): formato di
  `id` (V03), semver di `version` (V04), compatibilità di `lasagna` (V02),
  `entry` che nomina un nodo (V07: `entry` resta però un campo richiesto come nel
  01, quindi un `entry` assente è V01; il ticket 03 decide se diventa V07),
  `max_iterations` ≥ 1 (V11), numero di route (V13), campi per tipo di gate
  (V14) (T06, T15, T16, T22).
- **V06 (cambia).** Per ogni arco, nell'ordine del file: `from` di qualunque tipo
  di arco; `to` di `direct` e `loop`; `to` di ogni route di un `router`
  (percorso `edges[j].routes[k].to`). `default` di un `router` **non** si
  controlla qui. Il file è `pipeline_file(path)`; un finding per riferimento
  sbagliato.

### Error types

Stile del progetto: nessuna eccezione, `Finding`. Per questo ticket:

| Caso | Esito |
|---|---|
| chiave sconosciuta; tipo, enum o valore errato; campo richiesto mancante; `x-*` come nome in una mappa a chiavi utente; chiave non stringa | `Finding` V01, uno per errore, file del registry o della pipeline, percorso come in Data types |
| `from`/`to`/route `to` che non è un id di nodo | `Finding` V06 (vedi sopra) |
| `render_schema` con un `kind` diverso da `registry`/`pipeline` | non congelato |
| generatore senza `OUT_DIR`, con `OUT_DIR` inesistente o non scrivibile | non congelato |

### Return shape

- `validate_project` → `list[Finding]`, `[]` se tutto è valido, ordine non
  congelato (i test filtrano per `rule`/`path`, come nel 01).
- `render_schema(kind)` → `str`: JSON con indentazione di 2 spazi, chiavi
  ordinate, non-ASCII non escapati, un solo `"\n"` finale, mai `"\r"`.
  Deterministico: stessa stringa a ogni chiamata, indipendente dalla data,
  dall'ordine di inserimento delle chiavi (`sort_keys`) e dalla piattaforma;
  dipende dall'ordine dei campi solo nelle liste `required` (ordine di
  Signatures) e dalla versione di pydantic (fissata da `uv.lock`).
- File committati: `schema/registry.schema.json` e `schema/pipeline.schema.json`
  con byte **uguali** a `render_schema(kind).encode("utf-8")`. Il confronto è
  tra byte (nessun `read_text`, nessuna normalizzazione). `.gitattributes`
  (`eol=lf`) tiene LF al checkout. Quando i modelli o la versione di pydantic
  cambiano, si rigenerano con il comando di Signatures.
- Auto-validazione: il progetto è `<repo>` (cartella con `.lasagna/`);
  `validate_project(data.registry, data.pipelines)` con i dati di `load_project`
  e `data.findings == ()`.
- Blocchi YAML della spec: nella sezione che comincia con la riga
  `### <numero> ` (fino alla prossima riga che comincia con `##`) c'è **un solo**
  blocco recintato ```yaml: il test lo estrae e fallisce se ne trova un numero
  diverso da uno. Sezioni: `4.3`, `4.4`, `4.5`, `4.6`, `4.7`, `4.8`, `10.1`,
  `10.2`, `10.3`, `11.1`. Il parsing è `ruamel.yaml` `typ="safe"`. Il §4.4 ha
  `nodes: [ ... ]` e `edges: [ ... ]` (che il parser legge come `["..."]`): T40
  li sostituisce. Il §4.5 e il §4.7 sono liste; il §4.6 è una mappa con `edges`;
  il §4.8 è una mappa con `gate`.

### External dependencies

| Dependency | How the code reaches it | How tests control it |
|---|---|---|
| File system: `.lasagna/` del repo, `src/lasagna/builtin/`, `schema/` | solo `shell/project.py` (`load_project`) e `shell/gen_schema.py` (scrive); `core/` mai | i test leggono il repo con `Path(__file__).parents[N]` (`tests/shell/x.py` e `tests/e2e/x.py` → `parents[2]`); le scritture solo in `tmp_path` |
| File system: `docs/specs/v3.0.0.md` | solo test (lettura UTF-8) | letto dal repo reale; estrazione dei blocchi come in Return shape |
| Processo `python -m lasagna.shell.gen_schema` | `subprocess.run([sys.executable, "-m", "lasagna.shell.gen_schema", out], cwd=tmp_path)` solo in `tests/e2e/test_gen_schema.py` | `sys.executable` è il python dell'ambiente di test (il pacchetto `lasagna` è installato editable); cartella corrente = `tmp_path` per non dipendere da essa |
| Generatore dello schema JSON | `pydantic.BaseModel.model_json_schema` in `core/schema.py` | versione fissata da `uv.lock`; il test confronta con l'output della stessa funzione e con i file committati |
| Parsing YAML | `ruamel.yaml` in `shell/project.py` e nei test che leggono la spec | file veri; nessun mock |
| Orologio, rete, variabili d'ambiente, casualità | non usati | — |
| Sorgenti di `core/` (test di purezza del 01) | invariato | vale anche per `core/schema.py` |

### What is NOT frozen

- Testi dei `message` (restano «problema + correzione»); l'ordine dei finding;
  nomi privati e divisione in funzioni interne dei moduli; come si implementa
  l'ammissione di `x-*` (classe base, validatore `before`, o altro) purché
  l'esito sia quello di Data types; l'ordine in cui si scrivono i due file; cosa
  stampa il generatore; la forma esatta dello schema di pydantic oltre a quanto
  elencato in «JSON Schema, rappresentazione di `x-*`» e ai test T30–T33; il
  percorso V01 di una chiave non stringa (T28).
- Lo schema JSON **non** viene validato con un validatore JSON Schema vero (non
  c'è la dipendenza): lo si verifica strutturalmente (T30–T33). Limite noto.
- Se pydantic cambia il suo output, T35 fallisce finché non si rigenera: è il
  comportamento voluto.

## Out of scope

- I vincoli che sono regole V con un ID (V02–V04, V07–V14, V17–V20, V22–V25)
  non si codificano qui come vincoli dei modelli: li implementano e li testano
  i ticket 03 e 06, ognuno con il suo `Finding`. Qui solo la forma (V01).
- `--json`, `--strict`: ticket 03 e 06.
- Validare lo schema JSON con un validatore JSON Schema vero (dipendenza non
  aggiunta): solo controlli strutturali (T30–T33).
- Modificare `rules.md` (§3 e il testo su `x-*`): già coerente con la decisione
  sui 14 oggetti; il §4.3 della spec elenca solo sette oggetti, da riallineare
  a `close_version`.

## Definition of done

- [x] every criterion has the verification the spec asks for: a test that fails on a plausible wrong implementation, a passing check, or a recorded review
- [x] whole suite green (264 passed, `uv run ruff check` clean)
- [x] changelog line under Unreleased
- [x] traceability evidence filled in the tickets index; current file updated

## Log

<!-- One line per session: date | outcome | cycles used per criterion | summary of the [lasagna] lines | notes -->

2026-11-10 | done | all 44 planned tests green after 1 attempt; review passed at the first round (0 of 2 loops back to red); contract gate failed once (T14: `nodes: []` with the edge of P0 gives two V06) and passed on the 2nd | contract (fail, pass) → red/green ×44 rows → review (pass) → close | Decisions (maintainer, 2026-11-09): spec P19 (blocks extracted from the spec at test time, no spec↔file comparison); `x-*` admitted in all 14 fixed-key objects, V01 only as a name in the four user-key maps (spec §4.3 lists seven: realign at close_version); passes-immediately rule = ticket 01 rule plus a declared list. Passed immediately as declared (killed by mutation in review): T06, T13, T14, T17, T19, T20 (loop part), T22, T24, T26, T27, T28, T29, T31, T36–T44; partly: T12 (3 of 5 cases), T21 (2 of 4); T18 was expected to pass immediately and did not. Production code written by the coordinator: none except `schema/*.json`, produced by running `uv run python -m lasagna.shell.gen_schema schema`; the fixtures of ticket 01 received `description` in the contract node. Open gaps (not blocking, from the reviewer): the free-form value of `x-*` is proven only on `Node`; `x-` alone as a name in a user-key map is untested; the JSON Schema is checked structurally, not with a JSON Schema validator; the generator without arguments has no test (not frozen). Choices the user will see: registry `params` and `default` of params are strings only; `Node.description` and `max_iterations` are required; `entry` stays required (V07 is ticket 03).
