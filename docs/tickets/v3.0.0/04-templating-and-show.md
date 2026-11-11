---
status: done            # todo | in_progress | done | blocked
depends_on: ["02"]      # ticket numbers
criteria: [AC-V3-015, AC-V3-016, AC-V3-017, AC-V3-018, AC-V3-019]
---

# 04 — Templating, `$pipeline/` e `lasagna show`

The `status` above is the only record of this ticket's state: the tickets index
and the current file never copy it.

## Goal

`lasagna show <id>` e `lasagna show <id> <node> --input k=v` mostrano la
pipeline e il nodo renderizzati: parametri risolti con la loro origine
(registry o default), `{{ params.* }}` e `{{ inputs.* }}` sostituiti solo nei
campi di testo, `$pipeline/` risolto.

## Context

- Milestone M3 (§12), la parte "lettura per agenti".
- Spec D9 (templating minimo: campi di testo, spazi opzionali, ogni altro `{{`
  invariato), §6.7, §8.4 (`show` con e senza nodo; input mancanti restano
  `{{ inputs.x }}`), §4.4 (precedenza registry > default).
- `core/render.py` nasce qui. Il ticket 06 ne riusa lo scanner dei segnaposto
  (V17, V24) e la risoluzione di `$pipeline/` (V20): esporli come funzioni
  pure. Il ticket 07 riusa `render_text` e `parse_input_args`.
- `core/view.py` nasce qui (testo e JSON di `show`); il ticket 05 lo estende
  per `list`.
- **Decisione del maintainer, 2026-11-11 (spec §14.8/P08, metà `$pipeline/`):**
  `show` rifiuta un `ref` `$pipeline/...` il cui percorso risolto esce dalla
  cartella della pipeline, sia per `..` sia per symlink o junction, con errore
  esplicito ed exit 1. La metà `add` di P08 resta aperta (ticket 09).

## Changes

- `core/render.py`: sostituzione D9, risoluzione dei parametri, `$pipeline/`
  (con il rifiuto testuale di `..` che esce), lettura di `--input`.
- `core/view.py`: vista di `show` (testo e `--json`).
- `shell/project.py`: `containment_check` (esce dalla cartella? verifica col
  file system, symlink e junction compresi).
- `cli.py`: comando `show` con `--input` e `--json`; stdout in UTF-8 anche per `show`.
- Riga in `CHANGELOG.md` sotto Unreleased.
- **Fixture dei ticket precedenti: nessuna da aggiornare** (verificato nel nodo
  contract: `show` non cambia il comportamento di nessuna funzione esistente; la
  suite resta a 351 test verdi).

## Files involved

- `src/lasagna/core/render.py`, `src/lasagna/core/view.py`, `src/lasagna/cli.py`
- `src/lasagna/shell/project.py`
- `tests/core/`, `tests/shell/`, `tests/e2e/`

## Tests to pass

<!-- Filled in by the implementation pipeline (node contract) as a checklist:
one line per planned verification, in order. The green node checks off a test
with `[x] (green after N)`; the review node checks off checks and reviews. -->

Regola per questo ticket (maintainer, 2026-11-11, approvata a fine contratto: quella
del 02/03). Un test pianificato che passa subito perché il comportamento esiste già lo
spunto con `passes immediately` e proseguo, **purché abbia accanto
`(passa-subito atteso: Mnn)` e sia verificato con quella mutazione**; mi fermo su un
passa-subito fuori elenco o su un test che non verifica nulla. L'elenco va nel Log di
chiusura. Dove un passa-subito dipende da come l'implementer ha scritto la riga
precedente può anche non succedere: è un'altra riga rossa in più, non un problema.
Scelte di prodotto dove la spec taceva (confermate dal maintainer, 2026-11-11): `run`
con soli `params`; sostituzione prima di `$pipeline/`; `--input` non dichiarato o senza
`=` exit 2, ultimo valore vince; `show` su pipeline disabilitate e non fermato da altre
pipeline illeggibili né dalle regole di `validate`; id/nodo inesistenti al ticket 11. La
spec §14.8 resta com'è.

**Convenzioni di tutte le righe** (`tests/core/`: nessun mock e nessun `monkeypatch`;
ogni test cita il suo criterio in un commento `# AC-V3-NNN`; una riga con più casi
separati da «;» è **parametrizzata**: un caso di test per caso):
- Costanti: `PD = ".lasagna/pipelines/demo"`; `ALL = lambda path: True` (il predicato
  `is_contained` di un test che non lo esercita); `A = {"id": "a", "description": "A"}`,
  `B` e `C` allo stesso modo; `D(x, y) = {"type": "direct", "from": x, "to": y}`;
  `L(x, y, **k) = {"type": "loop", "from": x, "to": y, "max_iterations": 3, **k}`;
  `Q0 = {"lasagna": "3.0", "id": "demo", "entry": "a", "nodes": [A, B], "edges": [D("a", "b")]}`.
  Ogni riga parte da `Q0`, cambia solo ciò che dice; «`edges = [...]`» o «`nodes = [...]`» (sempre **liste**, mai tuple: i modelli sono strict)
  **sostituisce** l'intera lista di `Q0`; **Una riga che nomina un arco o una route senza scrivere `edges = [...]` non lo aggiunge a `Q0`: scrive sempre la lista intera.** `Q1` = `Q0` con `params = {"p": {"default": "d"}, "d": {"default": "dd"}}` e `inputs = {"i": {}, "f": {}}`: le righe T22–T27 partono da `Q1` (i parametri e gli input che usano sono dichiarati). Un campo che la riga aggiunge (`params`, `inputs`,
  `outputs`, `name`, ...) si aggiunge come chiave del dizionario.
- Chiamate: `SJ(Q, ov, inp, node)` = `json.loads(show_json(Pipeline.model_validate(Q), ov, inp, PD, node, ALL))`;
  `ST(Q, ov, inp, node)` = `show_text(Pipeline.model_validate(Q), ov, inp, PD, node, ALL)`;
  `ov` = override del registry (`Mapping[str, str]`), `inp` = input (`Mapping[str, str]`),
  `node` = id del nodo oppure `None`. Se una riga non dice `ov`, `inp`, `node`: `{}`, `{}`, `None`.
- `S`: il pipeline della sezione Contract › Fixture, caricato dal test con
  `ruamel.yaml.YAML(typ="safe")` e poi `Pipeline.model_validate`. `OVS = {"cmd": "pytest -q"}`,
  `INS = {"ticket": "a.md"}`. `N`: il pipeline N di Contract › Fixture, costruito con `Pipeline.model_validate(N)`.
  `G_A`, `G_B`, `G_C`, `G_D`, `G_E`, `G_N`, `G_EMPTY_TEXT`,
  `G_EMPTY_JSON`: i testi esatti di Contract › Output di riferimento, copiati nel test.
  Un testo si confronta con `==`, byte per byte, finali `"\n"` compresi.
- `X = "<{{ params.p }}|{{ inputs.i }}>"` (con `p`, `i` dichiarati e `ov = {"p": "P"}`,
  `inp = {"i": "I"}`) rende `"<P|I>"`.
- **F** (formato della frase di correzione): dato `message`,
  `problem, fix = message.rsplit("; ", 1)` riesce, `problem.strip()` non è vuoto e
  `re.fullmatch(r"[a-z]\S*( \S+)+\.", fix)` riesce. «in F» nei test è questa asserzione,
  scritta una volta come helper.
- CLI (`tests/e2e/`): `typer.testing.CliRunner().invoke(lasagna.cli.app, [...])` con la cartella
  corrente su un progetto in `tmp_path` (`monkeypatch.chdir`, ammesso fuori da `tests/core/`);
  `result.stdout` e `result.stderr` sono separati. Il «progetto S» è: `.lasagna/pipelines.yaml`
  e `.lasagna/pipelines/demo/pipeline.yaml` della sezione Fixture, scritti in UTF-8.
  «stdout vuoto» significa `result.stdout == ""`.

Segnaposto (AC-V3-015; `tests/core/test_render_text.py`; `render_text` e `find_placeholders`)
- [x] (green after 1) T01 AC-V3-015 · `render_text(t, {"x": "X"}, {"y": "Y"})` con `t` = `{{ params.x }}` → `X`; `{{params.x}}` → `X`; `{{   params.x   }}` → `X`; `{{\tparams.x\t}}` → `X`; `{{ inputs.y }}` → `Y`; `{{inputs.y}}` → `Y`; `a {{ params.x }} b {{ inputs.y }} c` → `a X b Y c`; `{{ params.x }}{{ params.x }}` → `XX`.
- [x] (passes immediately, mutation check done in review) T02 AC-V3-015 · restano **invariati** (stesso testo in uscita) con `params = {"x": "X", "x.y": "XY"}` e `inputs = {"y": "Y"}`: `{{ foo }}`; `${{ github.event.x }}`; `{% if x %}`; `{{ params }}`; `{{ params. x }}`; `{{ params.x.y }}`; `{{ Params.x }}`; `{{ INPUTS.y }}`; `{{ params.x`; `{ { params.x } }`; `{{ params.x }`; `{{ params.x\n}}` (a capo dentro le graffe); `{{ params.x } }`; `{{}}`; testo senza graffe. (passa-subito atteso: M03, M09, M10)
- [x] (passes immediately, mutation check done in review) T03 AC-V3-015 · un nome non fornito resta com'è: con `params = {"x": "X"}`, `inputs = {"y": "Y"}`: `{{ params.zzz }}`, `{{ inputs.zzz }}`, `{{ params.y }}` (esiste solo tra gli input), `{{ inputs.x }}` (esiste solo tra i params) restano invariati; con mappe vuote `{{ params.x }}` e `{{ inputs.y }}` restano invariati; un testo con un segnaposto noto e uno ignoto (`{{ params.x }} {{ inputs.zzz }}`) → `X {{ inputs.zzz }}`. (passa-subito atteso: M04, M05)
- [x] (passes immediately, mutation check done in review) T04 AC-V3-015 · un solo passaggio: con `params = {"a": "{{ params.b }}", "b": "B"}` → `{{ params.a }}` rende `{{ params.b }}`; con `inputs = {"y": "{{ params.a }}"}` → `{{ inputs.y }}` rende `{{ params.a }}`; con `params = {"a": "{{ inputs.y }}"}`, `inputs = {"y": "Y"}` → `{{ params.a }}` rende `{{ inputs.y }}`. (passa-subito atteso: M06)
- [x] (passes immediately, mutation check done in review) T05 AC-V3-015 · `${{ params.x }}` con `params = {"x": "X"}` → `$X` (il `$` resta, il segnaposto si sostituisce). (passa-subito atteso: M08)
- [x] (passes immediately, mutation check done in review) T06 AC-V3-015 · il valore si inserisce alla lettera: `params = {"x": "a\\1b\\g<0>c$&d"}` (i caratteri `a`, `\`, `1`, `b`, `\`, `g<0>`, `c`, `$&`, `d`) e `{{ params.x }}` → esattamente quel valore; valore vuoto `""` → `{{ params.x }}` rende `""`. (passa-subito atteso: M07)
- [x] (green after 1) T07 AC-V3-015 · `find_placeholders("{{ params.a }} x {{inputs.b}} {{ foo }} ${{ params.a }} {{ params.q.r }}")` → `[("params", "a"), ("inputs", "b"), ("params", "a")]` (nell'ordine di comparsa, ripetizioni comprese, nessun doppione tolto); `find_placeholders("")` → `[]`; `find_placeholders("{{ foo }}")` → `[]`. (passa-subito atteso: M11)

`$pipeline/` (AC-V3-017; `tests/core/test_pipeline_ref.py`; `resolve_pipeline_ref(ref, PD)`; `PipelinePathError`)
- [x] (green after 1) T08 AC-V3-017 · risolve nel percorso della cartella della pipeline: `$pipeline/assets/x.md` → `.lasagna/pipelines/demo/assets/x.md`; `$pipeline/x.md` → `.lasagna/pipelines/demo/x.md`; `$pipeline/assets/../x.md` → `.lasagna/pipelines/demo/x.md`; `$pipeline/./a.md` → `.lasagna/pipelines/demo/a.md`; `$pipeline/a//b.md` → `.lasagna/pipelines/demo/a/b.md`; `$pipeline/assets/` → `.lasagna/pipelines/demo/assets`; `$pipeline/` → `.lasagna/pipelines/demo`; `$pipeline/../demo/x.md` → `.lasagna/pipelines/demo/x.md` (il percorso normalizzato torna dentro la cartella: ammesso).
- [x] (passes immediately, mutation check done in review) T09 AC-V3-017 · non è un `$pipeline/` all'inizio: tornano identici `$pipeline`, `$pipelines/x`, `x/$pipeline/y`, ` $pipeline/x` (spazio iniziale), `$PIPELINE/x`, `$Pipeline/x`, `docs/a.md`, `""`. (passa-subito atteso: M16, M17)
- [x] (green after 1) T10 AC-V3-017 · esce dalla cartella → solleva `PipelinePathError` con `error.ref ==` il `ref` passato: `$pipeline/..`; `$pipeline/../x`; `$pipeline/../../x`; `$pipeline/assets/../../x`; `$pipeline/assets/../..`; `$pipeline/a/../../..`; `$pipeline/../demo2/x.md` (cartella sorella con lo stesso prefisso di testo). (passa-subito atteso: M14)

Parametri (AC-V3-016; `tests/core/test_resolve_params.py`; `resolve_params(pipeline, overrides)`)
- [x] (green after 1) T11 AC-V3-016 · precedenza registry > default: pipeline `Q0` con `params = {"b": {"default": "db"}, "a": {"default": "da"}}`: `overrides = {"a": "ra"}` → `{"b": ResolvedParam("db", "default"), "a": ResolvedParam("ra", "registry")}` e `list(result) == ["b", "a"]` (ordine di dichiarazione); `overrides = {}` → entrambi `"default"`; `overrides = {"a": "da"}` (uguale al default) → `ResolvedParam("da", "registry")`.
- [x] (passes immediately, mutation check done in review) T12 AC-V3-016 · casi limite: `overrides = {"a": ""}` → `ResolvedParam("", "registry")`; `overrides = {"zzz": "v"}` → le chiavi restano `["b", "a"]` (un override non dichiarato è ignorato: lo segnala V18, ticket 06); pipeline senza `params` e `overrides = {"a": "v"}` → `{}`. (passa-subito atteso: M21, M22)

Input (AC-V3-019; `tests/core/test_parse_inputs.py`; `parse_input_args(args, declared)`, `InputError`)
- [x] (green after 1) T13 AC-V3-019 · con `declared = {"ticket", "note"}`: `["ticket=a.md"]` → `{"ticket": "a.md"}`; `["ticket=a.md", "note=n"]` → entrambi; `["ticket=a=b"]` → `{"ticket": "a=b"}` (si divide sul primo `=`); `["ticket="]` → `{"ticket": ""}`; `["ticket=a", "ticket=b"]` → `{"ticket": "b"}` (l'ultimo vince); `["ticket= x "]` → `{"ticket": " x "}` (nessun `strip`); `["ticket={{ params.p }}"]` → il valore alla lettera; `[]` → `{}`.
- [x] (green after 1) T14 AC-V3-019 · solleva `InputError`, con `str(error)` in F e che contiene tra apici singoli l'argomento (primi due casi) o la chiave (altri): `["ticket"]` (nessun `=`: `'ticket'`); `["=v"]` (chiave vuota: `'=v'`); `["ghost=1"]` (non dichiarato: `'ghost'`); `["ticket=a", "ghost=1"]` (`'ghost'`); `["Ticket=a"]` (il confronto distingue le maiuscole: `'Ticket'`); `["ticket=a"]` con `declared = set()` (`'ticket'`). (passa-subito atteso: M26, M27)

Vista di `show` (`tests/core/test_show_json.py` per le righe che leggono il JSON, `tests/core/test_show_text.py` per quelle che leggono il testo)
- [x] (green after 1) T15 AC-V3-018, AC-V3-016 · `show_json(S, OVS, INS, PD, None, ALL) == G_D` (testo esatto: elenca nome, versione, descrizione, nodo iniziale, parametri con origine `registry` per `cmd` e `default` per `area`, input, output, nodi, archi; i segnaposto già sostituiti dove D9 lo vuole).
- [x] (green after 1) T16 AC-V3-018 · `show_text(S, OVS, INS, PD, None, ALL) == G_A`. (passa-subito atteso: M43)
- [x] (green after 1) T17 AC-V3-019 · `show_json(S, OVS, INS, PD, "first", ALL) == G_E` (nodo completo renderizzato, archi in uscita, nodi di destinazione; `$pipeline/assets/guide.md` risolto). (passa-subito atteso: M43)
- [x] (green after 1) T18 AC-V3-019 · `show_text(S, OVS, INS, PD, "first", ALL) == G_B`. (passa-subito atteso: M43)
- [x] (green after 1) T19 AC-V3-019 · senza input: `show_text(S, OVS, {}, PD, "first", ALL) == G_C` (`{{ inputs.ticket }}` e `{{inputs.ticket}}` restano com'erano scritti, anche in `ref` e nella descrizione della risorsa; il `run` mostra `pytest -q {{ inputs.ticket }}`). (passa-subito atteso: M62)
- [x] (passes immediately, mutation check done in review) T20 AC-V3-015 · campi di testo **sostituiti** (parametrizzata: un caso per campo; `Q0` con `params = {"p": {"default": "d"}}`, `inputs = {"i": {}}`, `outputs = {"o": {}}`; `ov = {"p": "P"}`, `inp = {"i": "I"}`; il campo vale `X`; atteso `"<P|I>"` nel punto indicato): `description` del pipeline → `SJ(...)["description"]`; `description` di `params.p` → `["params"]["p"]["description"]`; `description` di `inputs.i` → `["inputs"]["i"]["description"]`; `description` di `outputs.o` → `["outputs"]["o"]["description"]`; (con `node = "a"`) `description` del nodo `a` → `["node"]["description"]`; `steps = ["s0", X]` → `["node"]["steps"][1]`; risorsa `{"type": "doc", "ref": "r.md", "description": X}` → `["node"]["resources"][0]["description"]`; risorsa `{"type": "doc", "ref": X}` → `["node"]["resources"][0]["ref"]`; gate `{"type": "human", "message": X}` → `["node"]["gate"]["message"]`; gate `{"type": "agent", "criteria": ["c0", X]}` → `["node"]["gate"]["criteria"][1]`; `edges = [L("a", "a", when=X)]` con `node = "a"` → `["edges"][0]["when"]`; `edges = [D("a", "b"), L("a", "a", when=X)]` con `node = None` → `["edges"][1]["when"]`; route `{"to": "b", "when": X}` di un `router` `decided_by: agent` (`edges = [{"type": "router", "from": "a", "decided_by": "agent", "routes": [{"to": "b", "when": X}, {"to": "a", "when": "w"}]}]`, `node = "a"`) → `["edges"][0]["routes"][0]["when"]`. (passa-subito atteso: M30)
- [x] (passes immediately, mutation check done in review) T21 AC-V3-015 · **non sostituiti** (D9: id, enum, `from`/`to`, numeri e ogni altro campo): con `Y0 = "{{ params.p }}"` (`p` dichiarato, `ov = {"p": "P"}`) il valore resta `Y0` (parametrizzata): senza nodo, `Q0` con `id = Y0` → `["id"]`; `name = Y0` → `["name"]`; `entry = Y0` → `["entry"]`; `nodes = [{"id": Y0, "name": Y0, "description": "A"}, B]` → `["nodes"][0]["id"]` e `["nodes"][0]["name"]`; `edges = [D(Y0, "b")]` → `["edges"][0]["from"]`; `edges = [D("a", Y0)]` → `["edges"][0]["to"]`; `edges = [L(Y0, "a")]` → `["edges"][0]["from"]`; `edges = [L("a", Y0)]` → `["edges"][0]["to"]`; `edges = [{"type": "router", "from": "a", "decided_by": "agent", "routes": [{"to": Y0, "when": "w"}, {"to": "a", "when": "w2"}], "default": Y0}]` → `["edges"][0]["routes"][0]["to"]` e `["edges"][0]["default"]`; `params = {"p": {"default": "d"}, "q": {"default": Y0}}` → `["params"]["q"]["value"]` (il valore di default non si renderizza); `ov = {"p": "P", "q": Y0}` con `q` dichiarato → `["params"]["q"]["value"]`. Con `node = "a"`: risorsa `{"type": Y0, "ref": "r", "description": "d"}` (tipo proprio) → `["node"]["resources"][0]["type"]`; nodo `{"id": "a", "name": Y0, "description": "A"}` → `["node"]["name"]`; `pipeline` (campo `["pipeline"]`) con `id = Y0` → `Y0`. E `$pipeline/x` resta alla lettera fuori da `ref`: `steps = ["$pipeline/x"]`, gate `check` con `run = "$pipeline/x"`, risorsa con `description = "$pipeline/x"`, criterio `"$pipeline/x"` → `$pipeline/x` in ognuno. (passa-subito atteso: M29, M36)
- [x] (passes immediately, mutation check done in review) T22 AC-V3-015 · nel `run` si sostituiscono solo i `params`, mai gli `inputs` (D9, V24): con `ov = {"p": "P"}`, `inp = {"i": "I"}`, `run = "{{ params.p }} {{ inputs.i }}"` il valore reso è `"P {{ inputs.i }}"` in: gate `check` (`node = "a"` → `["node"]["gate"]["run"]`); `edges = [{"type": "router", "from": "a", "decided_by": "check", "routes": [{"to": "b", "run": "{{ params.p }} {{ inputs.i }}"}, {"to": "a", "run": "r"}]}]` con `node = "a"` → `["edges"][0]["routes"][0]["run"]`. Nelle altre posizioni dei `when` e dei testi `{{ inputs.i }}` si sostituisce (T20). (passa-subito atteso: M31, M32)
- [x] (passes immediately, mutation check done in review) T23 AC-V3-015, AC-V3-019 · input dichiarato ma non fornito resta com'è: `Q0` con `params = {"p": {"default": "d"}}`, `inputs = {"i": {}}`, `ov = {}`, nodo `a` con `description = "{{ params.zz }} {{ inputs.zz }} {{ inputs.i }} {{ params.p }}"`: con `inp = {}` → `"{{ params.zz }} {{ inputs.zz }} {{ inputs.i }} d"`; con `inp = {"i": "I"}` → `"{{ params.zz }} {{ inputs.zz }} I d"` (un nome non dichiarato non si sostituisce mai; `show_json` usa gli input come gli arrivano, i dichiarati li controlla `parse_input_args`). (passa-subito atteso: M04)
- [x] (passes immediately, mutation check done in review) T24 AC-V3-015, AC-V3-016 · un solo passaggio anche in `show`: `ov = {"p": "{{ inputs.i }}"}`, `inp = {"i": "I"}`, nodo `a` con `description = "{{ params.p }}"` → `"{{ inputs.i }}"`; `inp = {"i": "{{ params.p }}"}`, `description = "{{ inputs.i }}"` → `"{{ params.p }}"`. (passa-subito atteso: M06)
- [x] (passes immediately, mutation check done in review) T25 AC-V3-017 · `$pipeline/` nei `ref` si risolve **dopo** la sostituzione, per ogni tipo di risorsa (`node = "a"`, `["node"]["resources"][0]["ref"]`): `ref = "$pipeline/assets/x.md"` → `.lasagna/pipelines/demo/assets/x.md`; `ref = "$pipeline/{{ inputs.f }}"` con `inp = {"f": "assets/x.md"}` → `.lasagna/pipelines/demo/assets/x.md`; `ref = "{{ params.d }}/x.md"` con `ov = {"d": "$pipeline/assets"}` → `.lasagna/pipelines/demo/assets/x.md`; `ref = "{{ inputs.f }}"` con `inp = {"f": "docs/a.md"}` → `docs/a.md` (non `$pipeline/`: invariato); `ref = "docs/$pipeline/a.md"` → invariato; risorsa `{"type": "url", "ref": "$pipeline/u"}` → `.lasagna/pipelines/demo/u`. (passa-subito atteso: M33; aggiunto 2026-11-11 con l'approvazione del maintainer: era stato omesso)
- [x] (green after 1) T26 AC-V3-017 · un `ref` che esce dalla cartella solleva `PipelinePathError` (`show_json` e `show_text`, `node = "a"`), con `error.ref` uguale al `ref` **dopo la sostituzione**: `ref = "$pipeline/../x.md"` (`error.ref == "$pipeline/../x.md"`); `ref = "$pipeline/{{ inputs.f }}"` con `inp = {"f": "../../x"}` (`"$pipeline/../../x"`: il caso di un input che scavalca); `ref = "{{ inputs.f }}"` con `inp = {"f": "$pipeline/../x"}`; `ref = "{{ params.d }}/x"` con `ov = {"d": "$pipeline/.."}`. Con predicato `lambda path: False` e `ref = "$pipeline/assets/link/s.md"` solleva anche (`error.ref == "$pipeline/assets/link/s.md"`); con `lambda path: True` non solleva. (passa-subito atteso: M15, M33)
- [x] (passes immediately, mutation check done in review) T27 AC-V3-017 · il predicato `is_contained` riceve il percorso **risolto**, solo per i `ref` `$pipeline/`: un test (con `SJ`, e uguale con `ST`) registra le chiamate in una lista (`calls = []` e `def inside(path): calls.append(path); return True`), con `node = "a"` e risorse `[{"type": "doc", "ref": "$pipeline/assets/x.md"}, {"type": "doc", "ref": "docs/a.md"}, {"type": "doc", "ref": "$pipeline/{{ inputs.f }}"}]` con `inp = {"f": "y.md"}`: `calls == [".lasagna/pipelines/demo/assets/x.md", ".lasagna/pipelines/demo/y.md"]`. (passa-subito atteso: M34, M35)
- [x] (passes immediately, mutation check done in review) T28 AC-V3-017 · solo i `ref` del nodo richiesto: `nodes = [{**A, "resources": [{"type": "doc", "ref": "$pipeline/../x"}]}, B]`: senza nodo (`node = None`) non solleva (il JSON si produce) e `node = "b"` non solleva; `node = "a"` solleva `PipelinePathError` (V20 è del ticket 06). Con `inside = lambda path: False` e `node = None` o `node = "b"` non solleva. (passa-subito atteso: M37, M38)
- [x] (green after 1) T29 AC-V3-018 · archi in forma compatta (`ST(...)`, righe della sezione `## Edges` in ordine di file, ognuna preceduta da `- `): `nodes = [A, B, C]`, `edges = [D("a","b"), L("b","a"), L("b","a", when="pass"), {"type": "router", "from": "a", "decided_by": "agent", "routes": [{"to": "b", "when": "w"}, {"to": "c", "when": "w2"}], "default": "c"}, {"type": "router", "from": "c", "decided_by": "check", "routes": [{"to": "a", "run": "r"}, {"to": "a", "run": "r2"}]}]` → le cinque righe esatte `- a -> b`, `- b -> a [loop when: fail, max: 3]`, `- b -> a [loop when: pass, max: 3]`, `- a -> b, c [router decided_by: agent, default: c]`, `- c -> a, a [router decided_by: check]` (un `to` ripetuto si ripete; `default` assente: nessun `, default:`).
- [x] (passes immediately, mutation check done in review) T30 AC-V3-018 · campi assenti: `Q0` con `nodes = [A]` e `edges = []` → `show_text(...) == G_EMPTY_TEXT` e `show_json(...) == G_EMPTY_JSON` (nessun `name`, `version`, `description`, `params`, `inputs`, `outputs`, archi: `null`, `{}`, `[]` nel JSON, `(none)` nel testo). (passa-subito atteso: M43)
- [x] (passes immediately, mutation check done in review) T31 AC-V3-018 · `entry` assente: `Q0` senza la chiave `entry` (e con `entry = None`) → `["entry"]` è `None` nel JSON e la riga è `entry: (none)` nel testo (il testo contiene `\nentry: (none)\n`); nessuna eccezione (V07 è di `validate`). (passa-subito atteso: M46)
- [x] (passes immediately, mutation check done in review) T32 AC-V3-018 · tipo di gate nell'elenco dei nodi: `nodes = [A, {**B, "gate": {"type": "human", "message": "m"}}, {**C, "gate": {"type": "check", "run": "r"}}, {"id": "d", "description": "D", "started_by": "human", "gate": {"type": "agent", "criteria": ["c"]}}]`, `edges = []` → nel testo le righe `- a (a) started_by=agent gate=none`, `- b (b) started_by=agent gate=human`, `- c (c) started_by=agent gate=check`, `- d (d) started_by=human gate=agent`; nel JSON `["nodes"]` ha `gate` `None`, `"human"`, `"check"`, `"agent"` e `started_by` `"agent"`, `"agent"`, `"agent"`, `"human"` in quest'ordine. (passa-subito atteso: M47)
- [x] (passes immediately, mutation check done in review) T33 AC-V3-018, AC-V3-019 · spazi ai margini: pipeline con `description = "  L1\n  L2\n"`: nel testo senza nodo la descrizione compare come le due righe `L1` e `  L2` (il blocco è `"L1\n  L2"`: `strip()` ai margini, righe interne intatte); nel JSON `["description"] == "  L1\n  L2\n"`. Lo stesso per la `description` di un nodo (`node = "a"`). (passa-subito atteso: M41)
- [x] (passes immediately, mutation check done in review) T34 AC-V3-019 · `show_text(N, {}, {}, PD, "b", ALL) == G_N` (nodo con `name`, `steps`, gate `agent` con `at: entry`, `by: subagent` e `criteria`, nessuna risorsa, un `router` con `default` inesistente e un `loop` in uscita). (passa-subito atteso: M43)
- [x] (passes immediately, mutation check done in review) T35 AC-V3-019 · archi in uscita e nodi di destinazione (JSON, `N` di G_N): con `node = "b"` `["edges"]` ha esattamente due elementi, il `router` e il `loop` di `b` (non quelli di `a` né di `c`) e `["next"] == [{"id": "c", "name": None}, {"id": "a", "name": None}]` (destinazioni nell'ordine di prima comparsa, senza doppioni, `default` inesistente omesso); con `node = "c"` `["edges"]` è quello di `c` e `["next"] == [{"id": "a", "name": None}]`; con `node = "a"` e `edges = []` `["edges"] == []` e `["next"] == []`; con `c` che ha `name = "Gamma"` (N modificato) il `next` di `b` è `[{"id": "c", "name": "Gamma"}, {"id": "a", "name": None}]`. (passa-subito atteso: M39, M40)
- [x] (passes immediately, mutation check done in review) T36 AC-V3-018, AC-V3-019 · forma del JSON: per ogni caso di G_D, G_E, G_EMPTY_JSON il testo è `json.dumps(json.loads(testo), indent=2, ensure_ascii=False) + "\n"` (senza `sort_keys`), termina con un solo `"\n"` e non contiene `"\r"`; con `description = "è✓"` il testo contiene `è✓` e non `\u00e8`. (passa-subito atteso: M42)

`containment_check` (AC-V3-017; `tests/shell/test_containment.py`, file system in `tmp_path`). Cartella: `root = tmp_path` con `.lasagna/pipelines/demo/assets/x.md` (file) e `PD`. Helper del test `make_dir_link(link, target)`: `os.symlink(target, link, target_is_directory=True)`; su `OSError` (Windows senza privilegio di symlink, come su questa macchina: WinError 1314) `subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True)`; solo se anche questo fallisce `pytest.skip`
- [x] (green after 1) T37 AC-V3-017 · `check = containment_check(root, PD)`: `check(".lasagna/pipelines/demo/assets/x.md")` è `True`; un file che non esiste dentro (`.lasagna/pipelines/demo/assets/nuovo.md`) `True`; la cartella stessa (`.lasagna/pipelines/demo`) `True`; `check(".lasagna/pipelines/demo/../../x")` `False`; `check("x")` `False`.
- [x] (passes immediately, mutation check done in review) T38 AC-V3-017 · un collegamento che esce: `make_dir_link(root / PD / "assets" / "link", root / "outside")` con `root / "outside" / "s.md"` esistente: `check(".lasagna/pipelines/demo/assets/link/s.md")` è `False`; `check(".lasagna/pipelines/demo/assets/link")` è `False`; un file `x.md` normale resta `True`. (passa-subito atteso: M48, M49 — corretto 2026-11-11 con l'approvazione del maintainer: era «nessuno», ma l'implementer di T37 ha scritto `resolve()` per `..`; M48 e M49 devono essere uccisi **su questa macchina**, dove il test usa la junction)
- [x] (passes immediately, mutation check done in review) T39 AC-V3-017 · altri casi del file system: cartella sorella `root / ".lasagna/pipelines/demo2/x.md"` esistente → `check(".lasagna/pipelines/demo2/x.md")` `False` (stesso prefisso di testo); un collegamento che resta dentro (`assets/inner` → `assets/real`, con `assets/real/f.md`) → `check(".lasagna/pipelines/demo/assets/inner/f.md")` `True`; la cartella della pipeline raggiunta tramite un collegamento (in una `root` propria di questo caso, non quella della cartella reale: `root / ".lasagna/pipelines/demo"` è essa stessa un collegamento verso `root / "elsewhere/demo"`, con `elsewhere/demo/assets/x.md`) → `check(".lasagna/pipelines/demo/assets/x.md")` `True`. (passa-subito atteso: M50, M51)

CLI (`tests/e2e/test_show.py`; progetto S)
- [x] (green after 1) T40 AC-V3-018, AC-V3-016 · `show demo --input ticket=a.md` → exit 0, `result.stdout == G_A`, `result.stderr == ""` (il `cmd` del registry arriva a `show`: origine `registry`). (passa-subito atteso: M59)
- [x] (passes immediately, mutation check done in review) T41 AC-V3-019 · `show demo first --input ticket=a.md` → exit 0, `result.stdout == G_B`, stderr vuoto; `show demo first` (senza input) → `result.stdout == G_C`, stderr vuoto, exit 0. (passa-subito atteso: M62)
- [x] (green after 1) T42 AC-V3-018, AC-V3-019 · `show demo --json --input ticket=a.md` → `result.stdout == G_D`; `show demo first --json --input ticket=a.md` → `result.stdout == G_E`; exit 0, stderr vuoto in entrambi (nessuna riga umana su stdout).
- [x] (passes immediately, mutation check done in review) T43 AC-V3-016 · origine dei parametri: registro senza `params` → `show demo --json` ha `params.cmd == {"value": "pytest", "source": "default", "description": None}`; registro con `params: {zz: "v"}` (non dichiarato) → exit 0 e `list(params) == ["area", "cmd"]`. (passa-subito atteso: M59, M60 — aggiunto 2026-11-11 con l'approvazione del maintainer: era stato omesso)
- [x] (passes immediately, mutation check done in review) T44 AC-V3-018 · `show` legge pipeline che `validate` giudicherebbe in modo diverso, e non si ferma per colpe altrui: (a) la voce `demo` con `enabled: false` → exit 0 e `result.stdout == G_A` (con `--input ticket=a.md`); (b) il registro con una seconda voce `other` (`path: pipelines/other`) il cui `pipeline.yaml` è malformato (`a: 1\nb: [1, 2\nc: 3\n`) → `show demo --input ticket=a.md` exit 0, `result.stdout == G_A`, stderr vuoto; (c) `demo` con due archi `direct` da `first` (V10) e con `entry: ghost` (V07) → exit 0, stdout contiene la riga `entry: ghost` e due righe `- first -> second`. (passa-subito atteso: M54, M55, M56)
- [x] (passes immediately, mutation check done in review) T45 AC-V3-019 · `--input` ripetuto e con `=`: `show demo first --input ticket=a.md --input ticket=b.md` → stdout contiene `Read b.md.` e non contiene `a.md`; `show demo first --input ticket=x=y` → contiene `Read x=y.`; `show demo first --input note=n --input ticket=a.md` (due input dichiarati) → contiene `Read a.md.`. (passa-subito atteso: M24, M25)
- [x] (green after 1) T46 AC-V3-019 · errori d'uso di `--input`: `show demo --input ticket` → exit 2, stdout vuoto, la prima riga di `result.stderr` comincia con `error: ` e il resto (`line[len("error: "):]`) è in F e contiene `'ticket'`; `show demo first --input ghost=1` → exit 2, stdout vuoto, stderr come sopra con `'ghost'`; stesso esito con `--json`. (passa-subito atteso: M52, M53)
- [x] (green after 1) T47 AC-V3-018 · nessun `.lasagna/` risalendo dalla cartella corrente (stessa guardia di `pytest.skip` del test di `validate`): `show demo` e `show demo --json` → exit 2, `".lasagna/"` in `result.stderr`, stdout vuoto. (passa-subito atteso: nessuno; il messaggio è lo stesso di `validate`)
- [x] (green after 1) T48 AC-V3-018 · pipeline illeggibile → exit 1, stdout vuoto (anche con `--json`), stderr contiene una riga che comincia con quella che segue: `pipeline.yaml` di `demo` malformato (`a: 1\nb: [1, 2\nc: 3\n`) → `error V01 .lasagna/pipelines/demo/pipeline.yaml: `; `pipeline.yaml` con una chiave `bogus: 1` in più → `error V01 .lasagna/pipelines/demo/pipeline.yaml bogus: `; `pipeline.yaml` assente → `error V05 .lasagna/pipelines.yaml pipelines[0].path: `; `pipelines.yaml` malformato (`a: [1\n`) → `error V01 .lasagna/pipelines.yaml: `. (passa-subito atteso: M53, M58)
- [x] (green after 1) T49 AC-V3-017 · `ref` che esce dalla cartella → exit 1, stdout vuoto (anche con `--json`), la prima riga di stderr comincia con `error: ` e il resto è in F e contiene il `ref` dopo la sostituzione tra apici singoli. Pipeline S con la risorsa di `first` sostituita da `{"type": "doc", "ref": R}` (stessa lista, un solo elemento): `R = "$pipeline/../../x"` → `'$pipeline/../../x'`; `R = "$pipeline/{{ inputs.ticket }}"` con `--input ticket=../../x` → `'$pipeline/../../x'` (input che scavalca); la stessa pipeline con `--input ticket=assets/ok.md` → exit 0 e stdout contiene `.lasagna/pipelines/demo/assets/ok.md`; `R = "$pipeline/assets/link/s.md"` con `assets/link` collegamento (helper di T37) verso una cartella fuori dalla pipeline → exit 1 con `'$pipeline/assets/link/s.md'`; con `R = "$pipeline/../../x"` e **senza nodo** (`show demo`) → exit 0 (i `ref` si leggono solo nella vista del nodo; V20 è del ticket 06). (passa-subito atteso: M61)
- [x] (green after 1) T50 AC-V3-018, AC-V3-019 · stdout in UTF-8 con un sottoprocesso reale (non `CliRunner`; come T31 del ticket 03): `subprocess.run([sys.executable, "-c", "from lasagna.cli import app; app()", "show", *args], cwd=<progetto in tmp_path>, capture_output=True, env=<os.environ senza PYTHONUTF8 e senza PYTHONIOENCODING>)`, con il progetto S dove `description` del nodo `first` è `"Work ✓ on {{ inputs.ticket }}."` e `description` del pipeline è `"café✓"`; tre casi di `args`: `["demo"]`; `["demo", "first", "--input", "ticket=è.md"]`; `["demo", "first", "--json", "--input", "ticket=è.md"]`. Esito: exit code 0; `proc.stdout.decode("utf-8")` non solleva; nel primo caso contiene `café✓`; nel secondo `Work ✓ on è.md.` e `›`; nel terzo `json.loads(...)["node"]["description"] == "Work ✓ on è.md."`. I fine riga di stdout si normalizzano prima di confrontare (`\r\n` → `\n`: non congelato). (passa-subito atteso: nessuno su Windows, dove senza la forzatura UTF-8 `✓` non si codifica in cp1252; M57)
- [x] (passes immediately, mutation check done in review) T51 AC-V3-015 · (passa-subito atteso: M03) un segnaposto con un nome diverso da `params`/`inputs` ma con la chiave presente (`{{ foo.x }}` con `x` in params e in inputs) resta com'è in `render_text`.
- [x] (passes immediately, mutation check done in review) T52 AC-V3-015 · (passa-subito atteso: M29a) `show --json` di un nodo il cui `id` contiene un segnaposto (`"n-{{ params.area }}"`, se i modelli lo ammettono): l'`id` del nodo resta letterale nella vista JSON del nodo.
- [x] (passes immediately, mutation check done in review) T53 AC-V3-015 · (passa-subito atteso: M29c) `show` (vista testo, senza nodo) con `entry` che contiene un segnaposto: resta letterale.
- [x] (passes immediately, mutation check done in review) T54 AC-V3-015 · (passa-subito atteso: M30f) `show` (vista testo, senza nodo) con un segnaposto nella descrizione di un output: viene sostituito.
- [x] (passes immediately, mutation check done in review) T55 AC-V3-017 · (passa-subito atteso: M36c) `show` di un nodo con `description` che contiene `$pipeline/x`: resta letterale (nessuna risoluzione fuori dai `ref`).
- [x] (passes immediately, mutation check done in review) T56 AC-V3-018 · (passa-subito atteso: M43f, M43h, M43i, M43j) vista testo di un nodo senza step, senza gate, senza archi in uscita e senza nodi successivi: le sezioni Steps, Gate, Outgoing edges e Next nodes mostrano `(none)`.
- [x] (green after 1) T57 AC-V3-017 · (rosso atteso) `show demo first` con la voce del registry `path: "./pipelines/demo"` e, in un secondo caso, `path: "pipelines//demo"` (stessa cartella sul disco) e un `$pipeline/assets/guide.md` nel nodo: exit 0 e `ref` risolto `.lasagna/pipelines/demo/assets/guide.md` (prima della correzione `show` usciva con exit 1 "leaves the pipeline folder").

Mutazioni da provare nel nodo review (ognuna: modifica temporanea del codice di produzione → i test indicati falliscono → si ripristina; evidenza nella riga)
- [x] M01 AC-V3-015 · `render_text` che richiede gli spazi (`{{ params.x }}` sì, `{{params.x}}` no) → T01.
- [x] M02 AC-V3-015 · `render_text` che non accetta spazi (`{{params.x}}` sì, `{{ params.x }}` no) → T01.
- [x] M03 AC-V3-015 · `render_text` che sostituisce un segnaposto generico `{{ nome.chiave }}` (anche `github.event.x`) → T02.
- [x] M04 AC-V3-015 · nome non fornito sostituito con stringa vuota o con `None` → T03, T23.
- [x] M05 AC-V3-015 · `params` e `inputs` incrociati (un nome cercato in entrambe le mappe) → T03.
- [x] M06 AC-V3-015 · sostituzione che si ripete finché il testo non cambia più (o due passaggi) → T04, T24.
- [x] M07 AC-V3-015 · inserimento con `re.sub` a stringa (gli escape `\1`, `\g<0>` si interpretano) → T06.
- [x] M08 AC-V3-015 · sostituzione che si porta via il `$` davanti a `{{` → T05.
- [x] M09 AC-V3-015 · spazi interni `\s*` al posto di `[ \t]*` (a capo ammesso) → T02.
- [x] M10 AC-V3-015 · nome con il punto ammesso (`params.x.y` cercato come chiave `x.y`) o regex senza distinzione di maiuscole (`Params.x`, `INPUTS.y`) (uno alla volta) → T02.
- [x] M11 AC-V3-015 · `find_placeholders` che toglie i doppioni, ordina, scarta gli `inputs` o restituisce solo i nomi (uno alla volta) → T07.
- [x] M12 AC-V3-017 · `resolve_pipeline_ref` senza normalizzazione (concatenazione semplice) → T08.
- [x] M13 AC-V3-017 · rifiuto di ogni `..` anche quando il percorso torna dentro → T08.
- [x] M14 AC-V3-017 · controllo con `startswith(pipeline_dir)` senza il separatore → T10.
- [x] M15 AC-V3-017 · nessun controllo testuale dell'uscita (solo il predicato) → T10, T26.
- [x] M16 AC-V3-017 · prefisso `$pipeline` senza la barra → T09.
- [x] M17 AC-V3-017 · prefisso con `strip()` o senza distinzione di maiuscole → T09.
- [x] M18 AC-V3-017 · `$pipeline/` e `$pipeline/assets/` con la barra finale → T08.
- [x] M19 AC-V3-016 · il default vince sul registry → T11, T40.
- [x] M20 AC-V3-016 · origine decisa confrontando il valore col default → T11.
- [x] M21 AC-V3-016 · un override vuoto `""` ignorato (test di verità) → T12.
- [x] M22 AC-V3-016 · un override non dichiarato compare tra i parametri → T12, T43.
- [x] M23 AC-V3-016 · parametri in ordine alfabetico invece che di dichiarazione → T11, T15.
- [x] M24 AC-V3-019 · `parse_input_args` che divide su ogni `=` → T13, T45.
- [x] M25 AC-V3-019 · il primo valore ripetuto vince → T13, T45.
- [x] M26 AC-V3-019 · `parse_input_args` senza il controllo dei dichiarati → T14, T46.
- [x] M27 AC-V3-019 · `ticket` senza `=` o `=v` accettati → T14.
- [x] M28 AC-V3-019 · valore con `strip()` → T13.
- [x] M29 AC-V3-015 · `show` che sostituisce un campo non di testo (`id`, `name`, `entry`, `from`, `to`, `default`, route `to`, valore di default, valore del registry, tipo di risorsa; uno alla volta) → T21.
- [x] M30 AC-V3-015 · `show` che **non** sostituisce uno dei campi di testo (uno alla volta, per ciascuno dei casi di T20) → T20.
- [x] M31 AC-V3-015 · gli `inputs` sostituiti dentro `run` (gate o route) → T22.
- [x] M32 AC-V3-015 · i `params` non sostituiti dentro `run` → T22, G_E/G_B.
- [x] M33 AC-V3-017 · `$pipeline/` risolto **prima** della sostituzione → T26, T25, T49.
- [x] M34 AC-V3-017 · il predicato `is_contained` mai chiamato → T26, T27.
- [x] M35 AC-V3-017 · il predicato chiamato con il `ref` non risolto, o anche per i `ref` che non sono `$pipeline/` → T27.
- [x] M36 AC-V3-017 · `$pipeline/` risolto anche in `steps`, `run`, `description` o `criteria` → T21.
- [x] M37 AC-V3-017 · nella vista senza nodo si controllano i `ref` di tutti i nodi → T28.
- [x] M38 AC-V3-017 · nella vista di un nodo si controllano i `ref` di tutti i nodi → T28.
- [x] M39 AC-V3-019 · tra gli archi in uscita compaiono anche quelli di altri nodi → T35.
- [x] M40 AC-V3-019 · destinazioni con doppioni, in ordine diverso, o con il nodo inesistente → T35.
- [x] M41 AC-V3-018 · testo senza `strip()` (o JSON con `strip()`) → T33.
- [x] M42 AC-V3-018 · JSON con `ensure_ascii` di default, senza `"\n"` finale, con `indent=None` o con `sort_keys=True` (uno alla volta) → T36, T15.
- [x] M43 AC-V3-018 · un'etichetta o un separatore del testo diverso da quello dei testi di riferimento (`(registry)`/`(default)` scambiati, `Next nodes`, `at:`/`by:`, la `›` del titolo, uno dei `(none)`; uno alla volta) → T16, T17, T18, T30, T34.
- [x] M44 AC-V3-018 · il `when` di un `loop` senza default mostrato vuoto, o `max` omesso → T29.
- [x] M45 AC-V3-018 · l'arco `router` senza `default`, con `to` deduplicati o con le route in ordine diverso → T29.
- [x] M46 AC-V3-018 · `entry` assente che solleva → T31.
- [x] M47 AC-V3-018 · `gate=none` per un nodo con gate (o il tipo sbagliato) → T32, T15.
- [x] M48 AC-V3-017 · `containment_check` che confronta il percorso senza `resolve()` (solo testo) → T38.
- [x] M49 AC-V3-017 · `containment_check` che risolve solo la cartella della pipeline e non il bersaglio → T38.
- [x] M50 AC-V3-017 · confronto per prefisso di stringa invece che per componenti → T39.
- [x] M51 AC-V3-017 · cartella della pipeline non risolta (confronto col percorso non risolto) → T39.
- [x] M52 AC-V3-019 · errore di `--input` con exit 1 invece di 2 → T46.
- [x] M53 AC-V3-019 · un errore stampato su stdout invece che su stderr (`--input`, pipeline illeggibile, `ref` che esce; uno alla volta) → T46, T48, T49.
- [x] M54 AC-V3-018 · `show` che si ferma se un'altra pipeline del registry è illeggibile → T44.
- [x] M55 AC-V3-018 · `show` che rifiuta una pipeline con `enabled: false` → T44.
- [x] M56 AC-V3-018 · `show` che rifiuta una pipeline con errori che non sono V01/V05 (V07, V10) → T44.
- [x] M57 AC-V3-018 · `show` senza la forzatura UTF-8 di stdout → T50 (su Windows).
- [x] M58 AC-V3-018 · `show --json` su errore che stampa comunque un JSON parziale su stdout → T48.
- [x] M59 AC-V3-016 · `show` che ignora i `params` del registry → T40, T43.
- [x] M60 AC-V3-016 · un override non dichiarato del registry che fa fallire `show` → T43.
- [x] M61 AC-V3-017 · `ref` che esce stampato come errore ma con exit 0 → T49.
- [x] M62 AC-V3-019 · la CLI che non passa gli input alla vista → T41, T42.

Check del nodo review
- [x] C01 · `uv run pytest` verde e `uv run ruff check` pulito.
- [x] C02 AC-V3-014 · `sha256` dei due file in `schema/` prima e dopo `uv run python -m lasagna.shell.gen_schema schema` uguale (i modelli non cambiano).
- [x] C03 AC-V3-017 · dalla radice del repo: `uv run lasagna show implementation` e `uv run lasagna show implementation contract --input ticket=docs/tickets/v3.0.0/04-templating-and-show.md` escono 0; ogni percorso che comincia con `.lasagna/pipelines/implementation/` stampato nella vista del nodo esiste (lo stesso per le altre due pipeline, nodo per nodo).
- [x] C04 AC-V3-017 · `uv run pytest -rs tests/shell/test_containment.py tests/e2e/test_show.py` non mostra test saltati su questa macchina (la junction funziona).
- [x] C05 AC-V3-017 · lettura di `containment_check`: se `resolve()` solleva (`OSError`, `RuntimeError` per cicli) restituisce `False` (fallisce chiuso). Non è raggiungibile da un test; è una verifica di lettura.
- [x] C06 · copia pulita dell'albero (file tracciati e nuovi, senza `.venv/`; su questa macchina `UV_LINK_MODE=copy`): `uv sync && uv run pytest && uv run ruff check` escono 0.
- [x] R01 · revisore indipendente con il ruolo `adversarial-reviewer`, senza il ragionamento del coordinatore.

Tracciabilità dei criteri: AC-V3-015 → T01–T07, T20–T24, M01–M11, M29–M32, M36; AC-V3-016 → T11, T12, T15, T24, T40, T43, M19–M23, M59, M60; AC-V3-017 → T08–T10, T25–T28, T37–T39, T49, M12–M18, M33–M38, M48–M51, M61, C03–C05; AC-V3-018 → T15, T16, T29–T33, T36, T40, T42, T44, T47, T48, T50, M41–M47, M54–M58; AC-V3-019 → T13, T14, T17–T19, T23, T34, T35, T41, T42, T45, T46, M24–M28, M39, M40, M52, M53, M62.

## Contract

<!-- Filled in by the implementation pipeline (node contract), from its
contract template. -->

Questo contratto **aggiunge** a quelli dei ticket 01–03, che restano validi (modelli,
`validate_project`, `format_finding`, `Finding`, `load_project`, `ProjectData`).
Nessun punto di quei contratti cambia.

### Seams

- **Core:** `lasagna.core.render` (`render_text`, `find_placeholders`, `resolve_pipeline_ref`,
  `resolve_params`, `parse_input_args`, `ResolvedParam`, `PipelinePathError`, `InputError`) e
  `lasagna.core.view` (`show_text`, `show_json`), con `lasagna.core.models.Pipeline.model_validate`
  per costruire l'oggetto.
- **Shell:** `lasagna.shell.project.containment_check` (T37–T39).
- **CLI:** `CliRunner().invoke(lasagna.cli.app, ["show", ...])`; un sottoprocesso reale
  per la codifica (T50).
- Nessun test va più in basso.

### Signatures

```python
# src/lasagna/core/render.py   (NUOVO, puro: solo stdlib e lasagna.core.models)
@dataclass(frozen=True)
class ResolvedParam:
    value: str
    source: Literal["registry", "default"]

class PipelinePathError(ValueError):
    ref: str            # il `ref` (dopo la sostituzione, prima della risoluzione)
    def __init__(self, ref: str) -> None: ...

class InputError(ValueError): ...      # str(error) è il messaggio, in F

def find_placeholders(text: str) -> list[tuple[str, str]]: ...
    # [(kind, name), ...] con kind "params" o "inputs", nell'ordine di comparsa.
def render_text(text: str, params: Mapping[str, str], inputs: Mapping[str, str]) -> str: ...
def resolve_pipeline_ref(ref: str, pipeline_dir: str) -> str: ...
    # solleva PipelinePathError se il percorso esce da pipeline_dir.
def resolve_params(pipeline: Pipeline, overrides: Mapping[str, str]) -> dict[str, ResolvedParam]: ...
def parse_input_args(args: Sequence[str], declared: Collection[str]) -> dict[str, str]: ...
    # solleva InputError.

# src/lasagna/core/view.py   (NUOVO, puro)
def show_text(pipeline: Pipeline, overrides: Mapping[str, str], inputs: Mapping[str, str],
              pipeline_dir: str, node_id: str | None,
              is_contained: Callable[[str], bool]) -> str: ...
def show_json(pipeline: Pipeline, overrides: Mapping[str, str], inputs: Mapping[str, str],
              pipeline_dir: str, node_id: str | None,
              is_contained: Callable[[str], bool]) -> str: ...
    # Entrambe sollevano PipelinePathError (T26). node_id che non è un nodo: non congelato (ticket 11).

# src/lasagna/shell/project.py   (si aggiunge)
def containment_check(root: Path, pipeline_dir: str) -> Callable[[str], bool]: ...

# src/lasagna/cli.py   (si aggiunge)
def show(pipeline_id: str = typer.Argument(...), node: str | None = typer.Argument(None),
         input_args: list[str] = typer.Option([], "--input"),
         json_output: bool = typer.Option(False, "--json")) -> None: ...
    # il comando è `lasagna show <id> [<node>] [--input k=v ...] [--json]`
```

L'implementer non cambia nomi, parametri né tipi. Le funzioni esistenti restano com'erano.

### Data types

- **Segnaposto (D9).** Un segnaposto è, letteralmente: `{{`, zero o più caratteri spazio
  o tab, `params` oppure `inputs` (minuscoli), un punto, un nome fatto di una o più
  lettere ASCII, cifre, `_` o `-`, zero o più spazi o tab, `}}`. Nient'altro: niente a
  capo dentro, niente altri punti, niente maiuscole in `params`/`inputs`. Si cerca da
  sinistra a destra, senza sovrapposizioni. Ogni altro `{{` resta com'è, compresi
  `{{ foo }}`, `${{ github.x }}`, `{% if %}`. `render_text` sostituisce un segnaposto
  quando il suo nome è una chiave della mappa del suo tipo (`params` o `inputs`),
  **alla lettera** (nessun escape interpretato) e **una volta sola** (il valore inserito
  non si riesamina); altrimenti lo lascia identico. Un `$` davanti a `{{` resta (`$X`).
  `find_placeholders` restituisce `(kind, name)` per ogni segnaposto, nell'ordine di
  comparsa, ripetizioni comprese, senza guardare le mappe.
- **Quali campi si sostituiscono** (`show`): `description` di pipeline, di ogni voce di
  `params`/`inputs`/`outputs`, di nodo e di risorsa; `steps`; `ref` di risorsa;
  `gate.message`, `gate.criteria`, `gate.run`; `when` di `loop` e di route; `run` di route.
  **Mai:** `id`, `name`, `entry`, `started_by`, `type`, `from`, `to`, `default`, `at`, `by`,
  `decided_by`, `access`, `required`, `max_iterations`, i `default` dei parametri, i valori
  del registry, i `type` di risorsa (anche quelli propri). **`run`** (di gate e di route):
  si sostituiscono solo i `params`, mai gli `inputs` (D9, V24: un input non diventa un
  comando).
- **`$pipeline/`.** Si risolve solo in `ref` di risorsa (qualunque `type`), **dopo** la
  sostituzione dei segnaposto, e solo se il `ref` così ottenuto comincia con la stringa
  esatta `$pipeline/` (rispetto alle maiuscole, senza spazi davanti). Il risultato è
  `posixpath.normpath(pipeline_dir + "/" + resto)` (resto = ciò che segue `$pipeline/`),
  quindi senza `.` né `//` né barra finale. Se il risultato non è uguale a `pipeline_dir`
  né comincia con `pipeline_dir + "/"`: `PipelinePathError`. Poi `show` chiama
  `is_contained(risolto)`: se è `False`: `PipelinePathError`. `is_contained` si chiama
  solo per i `ref` `$pipeline/` e solo per il nodo richiesto. Un `ref` che non comincia
  con `$pipeline/` (dopo la sostituzione) resta com'è. Nessun'altra posizione risolve
  `$pipeline/` (T21). `pipeline_dir` è il percorso dalla radice del progetto, con `/`.
  La CLI lo costruisce come `posixpath.normpath(".lasagna/" + path)` con il `path` della voce del registry
  (quindi `./pipelines/demo` e `pipelines//demo` danno `.lasagna/pipelines/demo`; barre finali tolte);
  path con `..` o assoluti: non congelato. (Aggiunto dopo la review R01, riga T57.)
- **Valori usati per la sostituzione in `show`.** La mappa dei `params` è `{k: v.value for k, v in resolve_params(pipeline, overrides).items()}` (solo i parametri **dichiarati** nel pipeline; un nome non dichiarato non si sostituisce mai); la mappa degli `inputs` è `inputs` **così com'è arrivata**, dichiarata o no (la dichiarazione la controlla `parse_input_args`). I `ref` si rendono, si risolvono e si controllano (testo e `is_contained`) **solo** nella vista del nodo richiesto, mai in quella senza nodo. `is_contained` si chiama una sola volta per ogni `ref` `$pipeline/` del nodo, nell'ordine delle risorse, per ogni chiamata di `show_text`/`show_json`.
- **F, formato della frase di correzione** (come nel ticket 03): `<problema>; <correzione>.`, la correzione è l'ultimo segmento dopo l'ultimo `"; "`, comincia con una lettera minuscola, ha almeno due parole e finisce con un punto. Vale per `str(InputError)` e per i messaggi di errore della CLI di `show`.
- **Parametri.** `resolve_params(pipeline, overrides)`: una voce per ogni chiave di
  `pipeline.params`, nell'ordine di dichiarazione; `ResolvedParam(overrides[k], "registry")`
  se `k in overrides` (anche valore vuoto o uguale al default), altrimenti
  `ResolvedParam(default, "default")`. Gli override non dichiarati si ignorano.
- **`parse_input_args(args, declared)`.** Ogni argomento si divide sul **primo** `=`:
  chiave prima, valore dopo (anche vuoto, alla lettera, senza `strip`). Senza `=` o con
  chiave vuota: `InputError`. Chiave non in `declared` (confronto esatto): `InputError`.
  Una chiave ripetuta: l'ultima vince. Il risultato è un `dict` nell'ordine di prima
  comparsa delle chiavi. `str(InputError)` è in F e contiene tra apici singoli
  l'argomento intero (formato sbagliato) o la chiave (non dichiarata).
- **`show` senza nodo** (D: §8.4): vedi Formati. **`show` con nodo:** il nodo, gli archi
  in uscita (quelli con `from` uguale all'id del nodo, in ordine di file) e i nodi di
  destinazione.
- **`containment_check(root, pipeline_dir)`** restituisce una funzione `f(path)` che dà
  `True` se e solo se `(root / path).resolve()` coincide con `(root / pipeline_dir).resolve()`
  o è dentro di esso, confrontando per **componenti** del percorso (non per prefisso di
  stringa). Segue symlink e junction; `path` può non esistere. Se `resolve()` solleva
  `OSError` o `RuntimeError`: `False` (fallisce chiuso).
- **CLI `show`.** Sequenza: radice → (nessun `.lasagna/`: exit 2) → `load_project` → il
  registro non si legge o non passa il modello: exit 1 → la voce con quell'id: **non
  presente nel registry: non congelato (ticket 11, §8.11)** → la pipeline della voce non
  si legge, non passa il modello o il suo file manca: exit 1 → `--input` (`parse_input_args` con `declared` = le chiavi di `inputs` del pipeline; errori: exit 2)
  → vista (nodo inesistente: non congelato, ticket 11) → errore `PipelinePathError`:
  exit 1 → altrimenti exit 0. Una voce con `enabled: false` si mostra come le altre. `show`
  **non** applica le regole di `validate` (V07, V10, ...) e non guarda le altre voci del
  registro: una pipeline altrui illeggibile non lo ferma. Un registro o una pipeline
  «che non passa il modello» è quello con un finding V01 di `validate_project` nel file
  del registro o in quello della pipeline mostrata, oppure con un finding di caricamento
  (`load_project`) nel file del registro o in quello della pipeline mostrata, oppure con
  il file della pipeline assente (V05 sul `path` della voce).
- **Stream.** stdout: **solo** il testo (o il JSON) di `show`, **in UTF-8** qualunque sia
  la codifica della piattaforma (come `validate`: lo garantisce `cli.py` all'inizio del
  comando); mai nulla su stdout in caso di errore. stderr: vuoto in caso di successo; in
  caso di errore le righe descritte in Error types. La codifica di stderr e la conversione
  dei fine riga di stdout non sono congelate.

### Formati

Testo di `show` (markdown). Regole comuni, valide per entrambe le viste:
- l'output è `"\n\n".join(blocchi) + "\n"`; un blocco è le sue righe unite da `"\n"`;
- ogni sezione è un blocco: una riga `## <Titolo>` seguita dalle sue righe, oppure da
  `(none)` se non ne ha;
- ogni testo scritto in una riga (descrizioni, passi, criteri, `run`...) è il valore
  reso; **solo il blocco della descrizione** (del pipeline e del nodo) ha `strip()` ai
  margini; le righe interne restano com'erano;
- «nome o id» = il `name` se c'è, altrimenti l'`id`.

**Senza nodo** (`show <id>`): blocchi in quest'ordine.
1. `# <nome o id del pipeline>`, `id: <id>`, `version: <version>` (solo se c'è), `entry: <entry>` (`entry: (none)` se assente).
2. la `description` resa, con `strip()` (blocco presente solo se c'è).
3. `## Params`: per ogni parametro risolto, in ordine di dichiarazione, `- <nome> = <valore come stringa JSON con ensure_ascii=False> (<registry|default>)` seguito da `: <description resa>` se c'è.
4. `## Inputs`: `- <nome> (required|optional)` seguito da `: <description resa>` se c'è.
5. `## Outputs`: `- <nome>` seguito da `: <description resa>` se c'è.
6. `## Nodes`: `- <id> (<nome o id>) started_by=<agent|human> gate=<human|check|agent|none>`.
7. `## Edges`: `- ` + la forma compatta di ogni arco, in ordine di file.

**Forma compatta di un arco** (testo; i valori sono quelli resi):
- `direct`: `<from> -> <to>`.
- `loop`: `<from> -> <to> [loop when: <when>, max: <max_iterations>]`.
- `router`: `<from> -> <to della route 1>, <to della route 2>, ... [router decided_by: <decided_by>]` e, se c'è `default`, `[router decided_by: <decided_by>, default: <default>]`.

**Con nodo** (`show <id> <node>`): blocchi in quest'ordine.
1. `# <id del pipeline> › <id del nodo> (<nome o id del nodo>)` (il carattere `›` è U+203A) e `started_by: <started_by>`.
2. la `description` del nodo resa, con `strip()`.
3. `## Steps`: `<n>. <passo reso>` con `n` da 1.
4. `## Resources`: `- <type> <ref reso e risolto> (access: <read|write>, <required|optional>)` seguito da `: <description resa>` se c'è.
5. `## Gate`: se il nodo ha un gate, le righe `type: <type>`, `at: <entry|exit>`, `by: <self|subagent>`, poi `message: <...>` se c'è, `run: <...>` se c'è, e se ci sono i criteri la riga `criteria:` seguita da `- <criterio reso>` per ognuno; altrimenti `(none)`.
6. `## Outgoing edges`: `- ` + forma compatta degli archi in uscita.
7. `## Next nodes`: `- <id> (<nome o id>)` per ogni nodo di destinazione che esiste, nell'ordine di prima comparsa negli archi in uscita (le `to` di un `direct` o di un `loop`; per un `router` le `to` delle route in ordine e poi il `default`), senza doppioni; destinazioni inesistenti omesse.

**JSON** (`show_json`): `json.dumps(documento, indent=2, ensure_ascii=False) + "\n"` (senza `sort_keys`; chiavi nell'ordine scritto sotto; tutti i valori resi come sopra, **senza `strip()`**; `null` per ciò che manca).
- Senza nodo: `{"id", "name", "version", "description", "entry", "params", "inputs", "outputs", "nodes", "edges"}`. `params`: oggetto `nome → {"value", "source", "description"}`; `inputs`: `nome → {"required", "description"}`; `outputs`: `nome → {"description"}`; `nodes`: lista di `{"id", "name", "started_by", "gate"}` con `gate` il tipo (`"human"`, `"check"`, `"agent"`) o `null`; `edges`: lista in ordine di file, ogni arco come `model_dump(by_alias=True)` dell'arco reso: `direct` `{"type", "from", "to"}`; `loop` `{"type", "from", "to", "when", "max_iterations"}`; `router` `{"type", "from", "decided_by", "routes": [{"to", "when", "run"}, ...], "default"}`.
- Con nodo: `{"pipeline", "node", "edges", "next"}`. `pipeline`: l'id; `node`: `model_dump(by_alias=True)` del nodo reso (chiavi `id, description, name, started_by, steps, resources, gate`; ogni risorsa `type, ref, access, required, description` con `ref` reso e risolto; il gate `type, at, message, run, criteria, by` oppure `null`); `edges`: gli archi in uscita come sopra; `next`: lista di `{"id", "name"}` come `## Next nodes`.

### Fixture

Registro del progetto S (`.lasagna/pipelines.yaml`):

```yaml
lasagna: "3.0"
pipelines:
  - id: demo
    path: pipelines/demo
    params:
      cmd: "pytest -q"
```

Pipeline S (`.lasagna/pipelines/demo/pipeline.yaml`):

```yaml
lasagna: "3.0"
id: demo
name: "Demo"
version: "1.0.0"
description: "Demo for {{ params.area }}."
params:
  area: { default: "core", description: "Area {{ params.area }}." }
  cmd: { default: "pytest" }
inputs:
  ticket: { description: "Ticket of {{ params.area }}." }
  note: { required: false }
outputs:
  line: { description: "A line." }
entry: first
nodes:
  - id: first
    name: "First"
    description: "Work on {{ inputs.ticket }} in {{ params.area }}."
    started_by: human
    steps:
      - "Read {{inputs.ticket}}."
      - "Keep {{ foo }} and ${{ github.x }}."
    resources:
      - { type: doc, ref: "$pipeline/assets/guide.md", description: "Guide for {{ inputs.ticket }}." }
      - { type: path, ref: "{{ inputs.ticket }}", access: write, required: false }
    gate:
      type: check
      run: "{{ params.cmd }} {{ inputs.ticket }}"
  - id: second
    description: "Second."
    gate: { type: human, message: "OK {{ inputs.ticket }}?" }
edges:
  - { type: direct, from: first, to: second }
  - { type: loop, from: second, to: first, when: "Redo {{ inputs.ticket }}", max_iterations: 2 }
```

Pipeline N (T34, T35; dizionario Python; `show_text(N, {}, {}, PD, "b", ALL)`):

```python
N = {"lasagna": "3.0", "id": "demo", "entry": "a", "nodes": [
      {"id": "a", "description": "A"},
      {"id": "b", "name": "Beta", "description": "B", "steps": ["s1"],
       "gate": {"type": "agent", "at": "entry", "criteria": ["c1", "c2"], "by": "subagent"}},
      {"id": "c", "description": "C"}],
     "edges": [
      {"type": "direct", "from": "a", "to": "b"},
      {"type": "router", "from": "b", "decided_by": "agent",
       "routes": [{"to": "c", "when": "w"}, {"to": "a", "when": "w2"}], "default": "ghost"},
      {"type": "loop", "from": "b", "to": "a", "when": "pass", "max_iterations": 3},
      {"type": "direct", "from": "c", "to": "a"}]}
```

### Output di riferimento

Tutti con `pipeline_dir = ".lasagna/pipelines/demo"`, `overrides = {"cmd": "pytest -q"}` (solo per S).

`G_A` = `show_text(S, OVS, INS, PD, None, ALL)`:

```text
# Demo
id: demo
version: 1.0.0
entry: first

Demo for core.

## Params
- area = "core" (default): Area core.
- cmd = "pytest -q" (registry)

## Inputs
- ticket (required): Ticket of core.
- note (optional)

## Outputs
- line: A line.

## Nodes
- first (First) started_by=human gate=check
- second (second) started_by=agent gate=human

## Edges
- first -> second
- second -> first [loop when: Redo a.md, max: 2]
```

`G_B` = `show_text(S, OVS, INS, PD, "first", ALL)`:

```text
# demo › first (First)
started_by: human

Work on a.md in core.

## Steps
1. Read a.md.
2. Keep {{ foo }} and ${{ github.x }}.

## Resources
- doc .lasagna/pipelines/demo/assets/guide.md (access: read, required): Guide for a.md.
- path a.md (access: write, optional)

## Gate
type: check
at: exit
by: self
run: pytest -q {{ inputs.ticket }}

## Outgoing edges
- first -> second

## Next nodes
- second (second)
```

`G_C` = `show_text(S, OVS, {}, PD, "first", ALL)`:

```text
# demo › first (First)
started_by: human

Work on {{ inputs.ticket }} in core.

## Steps
1. Read {{inputs.ticket}}.
2. Keep {{ foo }} and ${{ github.x }}.

## Resources
- doc .lasagna/pipelines/demo/assets/guide.md (access: read, required): Guide for {{ inputs.ticket }}.
- path {{ inputs.ticket }} (access: write, optional)

## Gate
type: check
at: exit
by: self
run: pytest -q {{ inputs.ticket }}

## Outgoing edges
- first -> second

## Next nodes
- second (second)
```

`G_D` = `show_json(S, OVS, INS, PD, None, ALL)`:

```json
{
  "id": "demo",
  "name": "Demo",
  "version": "1.0.0",
  "description": "Demo for core.",
  "entry": "first",
  "params": {
    "area": {
      "value": "core",
      "source": "default",
      "description": "Area core."
    },
    "cmd": {
      "value": "pytest -q",
      "source": "registry",
      "description": null
    }
  },
  "inputs": {
    "ticket": {
      "required": true,
      "description": "Ticket of core."
    },
    "note": {
      "required": false,
      "description": null
    }
  },
  "outputs": {
    "line": {
      "description": "A line."
    }
  },
  "nodes": [
    {
      "id": "first",
      "name": "First",
      "started_by": "human",
      "gate": "check"
    },
    {
      "id": "second",
      "name": null,
      "started_by": "agent",
      "gate": "human"
    }
  ],
  "edges": [
    {
      "type": "direct",
      "from": "first",
      "to": "second"
    },
    {
      "type": "loop",
      "from": "second",
      "to": "first",
      "when": "Redo a.md",
      "max_iterations": 2
    }
  ]
}
```

`G_E` = `show_json(S, OVS, INS, PD, "first", ALL)`:

```json
{
  "pipeline": "demo",
  "node": {
    "id": "first",
    "description": "Work on a.md in core.",
    "name": "First",
    "started_by": "human",
    "steps": [
      "Read a.md.",
      "Keep {{ foo }} and ${{ github.x }}."
    ],
    "resources": [
      {
        "type": "doc",
        "ref": ".lasagna/pipelines/demo/assets/guide.md",
        "access": "read",
        "required": true,
        "description": "Guide for a.md."
      },
      {
        "type": "path",
        "ref": "a.md",
        "access": "write",
        "required": false,
        "description": null
      }
    ],
    "gate": {
      "type": "check",
      "at": "exit",
      "message": null,
      "run": "pytest -q {{ inputs.ticket }}",
      "criteria": null,
      "by": "self"
    }
  },
  "edges": [
    {
      "type": "direct",
      "from": "first",
      "to": "second"
    }
  ],
  "next": [
    {
      "id": "second",
      "name": null
    }
  ]
}
```

`G_N` = `show_text(N, {}, {}, PD, "b", ALL)`:

```text
# demo › b (Beta)
started_by: agent

B

## Steps
1. s1

## Resources
(none)

## Gate
type: agent
at: entry
by: subagent
criteria:
- c1
- c2

## Outgoing edges
- b -> c, a [router decided_by: agent, default: ghost]
- b -> a [loop when: pass, max: 3]

## Next nodes
- c (c)
- a (a)
```

`G_EMPTY_TEXT` (`Q0` con `nodes = [A]` ed `edges = []`, senza `ov` né `inp`):

```text
# demo
id: demo
entry: a

## Params
(none)

## Inputs
(none)

## Outputs
(none)

## Nodes
- a (a) started_by=agent gate=none

## Edges
(none)
```

`G_EMPTY_JSON` (lo stesso pipeline):

```json
{
  "id": "demo",
  "name": null,
  "version": null,
  "description": null,
  "entry": "a",
  "params": {},
  "inputs": {},
  "outputs": {},
  "nodes": [
    {
      "id": "a",
      "name": null,
      "started_by": "agent",
      "gate": null
    }
  ],
  "edges": []
}
```

(Tutti i testi qui sopra sono prodotti dal prototipo di fattibilità, fuori dal repo; ognuno
termina con un solo `"\n"`.)

### Error types

Stile del progetto: la validazione non solleva; i comandi traducono le eccezioni in exit code.

| Caso | Dove | Esito |
|---|---|---|
| `ref` `$pipeline/` che esce dalla cartella (testo o collegamento) | core: `PipelinePathError(ref)` | CLI: exit 1, stdout vuoto, stderr `error: resource ref '<ref>' ...` con il resto del messaggio in F (T49) |
| `--input` senza `=`, con chiave vuota o non dichiarato | core: `InputError` | CLI: exit 2, stdout vuoto, stderr `error: <str(InputError)>` (T46) |
| nessun `.lasagna/` | CLI | exit 2, stdout vuoto, stderr `error: no .lasagna/ folder found here or in any parent folder` (come `validate`) |
| registro o pipeline illeggibili (YAML, modello, file assente) | CLI | exit 1, stdout vuoto, stderr: una riga `format_finding` per ogni finding che lo causa (T48); altre righe non congelate |
| id non nel registry; nodo inesistente | CLI | **ticket 11 (§8.11): non congelato qui, nessun test** |

### Return shape

- `render_text` → `str`; `find_placeholders` → `list[tuple[str, str]]`; `resolve_pipeline_ref` → `str`;
  `resolve_params` → `dict[str, ResolvedParam]`; `parse_input_args` → `dict[str, str]`;
  `show_text`, `show_json` → `str` con i testi di Formati e Output di riferimento;
  `containment_check(...)` → `Callable[[str], bool]`.
- CLI: per ogni caso, stdout, stderr ed exit code come in Data types › CLI `show` e Error types.

### External dependencies

| Dependency | How the code reaches it | How tests control it |
|---|---|---|
| File system (`.lasagna/` letto; esistenza e collegamenti) | `shell/project.py` (`load_project`, `containment_check`); `core/` mai | `tmp_path` con file scritti dal test |
| Verifica del contenimento da parte di `core/` | parametro `is_contained: Callable[[str], bool]` passato dalla shell | nei test del core una funzione del test (`ALL`, `lambda path: False`, `inside` che registra le chiamate); in `tests/shell/` quella vera |
| Collegamenti a cartelle (symlink / junction) | creati dal test con l'helper di T37 | `os.symlink`, altrimenti `mklink /J` (su questa macchina i symlink non si possono creare: WinError 1314, la junction sì: verificato con il prototipo) |
| Cartella corrente | `Path.cwd()` solo in `cli.py` | `monkeypatch.chdir(tmp_path)` nei test e2e (non in `tests/core/`) |
| Parsing YAML | `ruamel.yaml` solo in `shell/project.py` | file veri in `tmp_path` |
| Modelli | `Pipeline`/`Registry` di `core/models.py` | dizionari o YAML del test |
| stdout, stderr, exit code | typer (`typer.echo`, `typer.Exit`) | `CliRunner`: `result.stdout`, `result.stderr`, `result.exit_code` |
| Codifica di stdout | `sys.stdout` riconfigurato in `cli.py` | T50: sottoprocesso reale, ambiente senza `PYTHONUTF8` e `PYTHONIOENCODING` |
| Serializzazione JSON, espressioni regolari, `posixpath` | stdlib dentro `core/` (puro) | confronto col testo esatto |
| Orologio, rete, variabili d'ambiente, casualità | non usati | — |
| Sorgenti di `core/` (test di purezza) | invariato | vale anche per `core/render.py` e `core/view.py` |

### What is NOT frozen

- Il testo dei messaggi oltre a F e alle sottostringhe nominate (`'<ref>'`, `'<chiave>'`,
  `error: `); le righe di stderr oltre a quelle nominate in T48; i messaggi di `--help`.
- Nomi privati e divisione in funzioni interne; come `view.py` usa `render.py`.
- Id non nel registry e nodo inesistente (ticket 11); `show` su un pipeline con id
  ripetuti (V03, ticket 06).
- Percorso del registro con `..`, assoluto o con barre finali multiple.
- Backslash e lettere di unità nei `ref` (`$pipeline/..\..\x`, `$pipeline/C:/x`): le
  intercetta solo `containment_check` (su Windows) e solo se il file system li risolve
  fuori; non c'è un test.
- La conversione dei fine riga di stdout (CRLF su Windows ammesso); la codifica di stderr.
- Il comportamento di `{{{ params.x }}}` (graffe in più attorno a un segnaposto).
- L'ordine di valutazione tra `--input` malformato e pipeline illeggibile quando
  coincidono.
- Colonna del YAML malformato (§8.11): ticket 11.

## Out of scope

- V17, V20, V24 (errori di validazione sui segnaposto e su `$pipeline/`):
  ticket 06.
- `list` e `graph`: ticket 05.
- Errori "id non presente" / "nodo inesistente" del §8.11: ticket 11.
- L'hardening di `add` (metà di P08): ticket 09.

## Definition of done

- [x] every criterion has the verification the spec asks for: a test that fails on a plausible wrong implementation, a passing check, or a recorded review
- [x] whole suite green
- [x] changelog line under Unreleased
- [x] traceability evidence filled in the tickets index; current file updated

## Log

<!-- One line per session: date | outcome | cycles used per criterion | summary of the [lasagna] lines | notes -->

2026-11-11 | done (pending maintainer approval of the commits) | 57 test rows (T01-T50 planned, T51-T57 added in review): all green after 1 attempt; the contract gate failed once (undefined substitution maps, edge replace-vs-extend, strict models rejecting tuples) and passed on the 2nd; review went back to red once (1 of 2): T51-T56 (mutation gaps, passes-immediately by design) and T57 (red, then green) | contract (fail, pass) -> red/green x50 -> review (62 mutations, 134 runs with variants: 9 survived) -> T51-T56 (all 9 killed) -> R01 (no blocker; registry path `./pipelines/demo` found) -> T57 red/green -> close | Decisions (maintainer, 2026-11-11): `run` substitutes only params, never inputs; substitution happens before `$pipeline/` resolution; `$pipeline/` resolves only in resource `ref`, only in the node view, only for the requested node; a ref that leaves the folder is `PipelinePathError` (exit 1, format F); `$pipeline/../demo/x.md` is allowed; `--input` undeclared, without `=` or with an empty key exits 2, last repeated value wins; `show` works on `enabled: false` pipelines and is not stopped by other unreadable pipelines or by validate rules; spec 14.8 left as is; the CLI builds `pipeline_dir` with `posixpath.normpath` (added after R01). Passes-immediately rows: the declared list (T02-T06, T09, T12, T20-T24, T27, T28, T30-T36, T39, T41, T44, T45) plus T25 (M33), T38 (M48, M49) and T43 (M59, M60), approved one by one by the maintainer, plus T51-T56 approved in review; every one verified by its mutation. Some rows were batched in one subagent call (T05+T06, T18+T19, T22+T23, T31+T32, T33+T34, T35+T36, T38+T39, T43+T44, T45+T46), a deviation from one test at a time. Checks: C01-C06 pass (570 tests before T57, 572 after; ruff clean; clean copy with UV_LINK_MODE=copy; symlinks cannot be created on this machine (WinError 1314), so containment tests use junctions and none is skipped). Not done, left as notes (reviewer R01): a newline in an `--input` value breaks the first-line format of the two error messages; a missing input inside a `$pipeline/` ref with `..` is collapsed by normpath; `show` on an unknown pipeline id or node raises StopIteration (ticket 11); weak assertions in tests/e2e/test_show.py (overview with a leaving ref asserts only the exit code; T44 disabled/rule-violations do not assert empty stderr); `ruff format --check` disagrees with the repo style (left alone).
