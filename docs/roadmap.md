# lasagna v3 — piano operativo e roadmap delle versioni

> Stato: **bozza da approvare** (2026-11-05).
> Decisioni: Tommaso Terrin. Redazione: sessione Claude Code.
> Documento compagno: [`specs/v3.0.0.md`](specs/v3.0.0.md), la specifica completa della 3.0.0.

## 0. Come usare questo documento

Questo documento descrive **il prodotto finale** e il percorso per arrivarci,
diviso in versioni. Per ogni versione trovi:

- **obiettivo** e **perché ora**;
- **funzionalità**, complete ma non ancora al livello di dettaglio di una spec;
- **milestone interne**, in ordine;
- **fuori scope**;
- **criterio di successo**;
- **criticità e punti aperti**;
- un **prompt** autosufficiente. È l'input `goal` da dare alla pipeline
  `project-manager` quando quella versione parte (§1.4). Il prompt viene
  "grigliato", diventa una spec e la spec viene affettata in ticket.

Solo la 3.0.0 ha già una spec completa ([`specs/v3.0.0.md`](specs/v3.0.0.md)), scritta a
mano perché la pipeline che dovrebbe produrla non esiste ancora (§1.4).

---

## 1. Visione

### 1.1 Cos'è lasagna v3

**Un protocollo per descrivere processi di lavoro, che qualsiasi coding agent
può leggere ed eseguire, più una CLI che lo gestisce.**

- **Il protocollo** è la grammatica: lo schema YAML di registry e pipeline, più
  `rules.md`, che spiega la semantica a un agente che non conosce lasagna.
- **Le pipeline** sono i contenuti: processi riutilizzabili, versionati,
  componibili, parametrizzabili. Sono lo "stampino".
- **La CLI** è l'attrezzatura: crea, valida, mostra, disegna, copia e
  verifica le pipeline. Non esegue l'agente.
- **Gli adapter** (dalla 3.1) traducono concetti del protocollo in meccanismi
  di uno strumento specifico (hook di Claude Code, cartelle di opencode…),
  senza che il protocollo dipenda da nessuno strumento.

L'esecutore è sempre il coding agent (o l'umano). Una fase può delegare a un
subagent o a un agente esterno. Lasagna dà struttura; le garanzie (sandbox,
CI, hook) sono una scelta di chi lo adotta.

### 1.2 Posizionamento

| | OpenSpec / Spec Kit | lasagna v2 | lasagna v3 |
|---|---|---|---|
| Cosa sono | Un processo fisso | Un processo fisso, rigoroso, per Claude Code | Il formato in cui si scrivono i processi |
| Artefatto centrale | La spec | Spec + contratto + stato di fase | La pipeline (il processo) |
| Integrazione con l'agente | Comandi e template specifici per strumento, da mantenere | Plugin Claude Code (skill, hook, agenti) | Nessuna: file + `rules.md`; adapter opzionali |
| Garanzie | Obbedienza dell'agente | Hook deterministici | Convenzione, più gate `check` deterministici; hook tramite adapter |

Il vantaggio di lasagna v3 **non è l'affidabilità**: anche lei, senza adapter,
conta sull'obbedienza dell'agente. È **portabilità, componibilità e
standardizzazione del processo**. Rispetto a una skill in markdown: una pipeline
è componibile pezzo per pezzo, validabile, disegnabile, confrontabile con un
diff. Una skill è un blocco di testo generico e meno ordinato.

### 1.3 Principi di progetto

1. **Less is more.** Ogni campo dello schema deve servire a una delle pipeline
   reali che lasagna distribuisce. Se nessuna lo usa, non entra.
2. **Il protocollo funziona senza CLI e senza adapter.** La CLI rende comodo,
   l'adapter rende vincolante. Nessuno dei due è obbligatorio.
3. **Lo stato vive negli artefatti, non nel protocollo** (fino alla 3.2): le
   pipeline tengono traccia di dove sono con i loro file (`current`, ticket,
   changelog), che l'agente legge.
4. **Grammatica stabile, contenuti liberi.** Il nucleo di `rules.md` cambia solo
   con la versione del protocollo. L'estensione avviene con tipi di risorsa
   dichiarati nel registry e con `rules.local.md`.
5. **Functional core, imperative shell** anche per la CLI (eredità della v2):
   logica pura testata senza mock, I/O ai bordi.

### 1.4 Lasagna costruisce lasagna (dogfooding)

Criterio di successo della 3.0.0: **la CLI viene sviluppata seguendo le due
pipeline che distribuisce**, `project-manager` e `implementation`. Questo
ribalta la decisione D14 della v2 ("niente lasagna su lasagna"), che valeva per
un plugin fatto di markdown. La v3 è un'applicazione vera, e il protocollo è
progettato per funzionare anche senza la sua CLI. Quindi il bootstrap è
possibile:

1. **M0 (a mano):** si scrivono `rules.md` e le due pipeline in `.lasagna/` di
   questo repo. Nessuna CLI esiste ancora: l'agente legge lo YAML direttamente.
   Questa è già la prima prova che il protocollo funziona.
2. La spec della 3.0.0 è stata scritta a mano (questo lavoro). Entra nella
   pipeline `project-manager` come spec già approvata e la pipeline parte dal
   nodo `slicing`.
3. Ogni ticket della 3.0.0 si esegue con `implementation`, una sessione per
   ticket.
4. Appena esiste `lasagna validate`, la CLI valida le pipeline con cui viene
   costruita.

Criterio secondario (3.0.x): **Fidelitree v0.4.0** con le stesse pipeline,
cambiando solo i parametri nel registry, senza modificare i file delle pipeline.

---

## 2. Mappa delle versioni

| Versione | Tema | Dipende da |
|---|---|---|
| **3.0.0** | Protocollo 3.0, CLI di base, pipeline incluse, dogfooding | — |
| **3.0.1** | CI su GitHub e protezione di `main` (rinviate dalla 3.0.0) | 3.0.0 funzionante |
| **3.1.0** | Adapter (Claude Code per primo) e suite di conformità | 3.0 |
| **3.2.0** | Stato, resume e cicli `foreach` | 3.0 |
| **3.3.0** | Trigger e automazione (routine sulle issue GitHub) | 3.1, 3.2 |
| **3.4.0** | Distribuzione: indice della community, lockfile, aggiornamenti | 3.0 |
| **4.0.0** | Team e governance: permessi, approvazioni reali, telemetria, valutazione | 3.2, 3.3 |

3.1, 3.2 e 3.4 sono indipendenti tra loro e possono anche cambiare ordine.
L'ordine proposto segue il valore per l'utente attuale (un solo sviluppatore,
su Claude Code).

---

## 3. Versione 3.0.0 — MVP

**Obiettivo:** il protocollo esiste, si può scrivere una pipeline, validarla,
vederla, disegnarla, copiarla tra progetti, e un agente qualunque la segue
leggendo `rules.md`.

**Spec completa:** [`specs/v3.0.0.md`](specs/v3.0.0.md). Qui c'è solo il riassunto.

**Funzionalità:**
- Protocollo 3.0: schema del registry (`pipelines.yaml`) e delle pipeline
  (nodi, archi `direct`/`loop`/`router`, gate `human`/`check`/`agent`, risorse
  tipizzate e aperte, parametri, input/output); `rules.md` del nucleo;
  `rules.local.md` per le estensioni. Dopo la revisione del 2026-11-05 lo
  schema è più snello: niente sottopipeline (3.2), `schedule`/`event`/`trigger`
  (3.3), `classifier`, `blocking`, `expect`, `resource_types`, `group`, tipo
  `agent` (rientrano solo con un consumatore reale).
- CLI Python: `init`, `validate`, `list`, `show`, `graph`, `check`, `doctor`,
  `add` (da `builtin:` o da una cartella locale).
- Libreria globale, `save`, `add library:` e `add git+`: rinviati alla 3.4.
- Pipeline incluse: `project-manager`, `implementation`, `quick-fix`.
- Aggancio agli agenti tramite blocco in `AGENTS.md` (e `@AGENTS.md` in
  `CLAUDE.md`).

**Milestone:** vedi [`specs/v3.0.0.md` §12](specs/v3.0.0.md#12-milestone-indicative-per-lo-slicing)
(M0 bootstrap a mano → M1 tracer bullet → M2
validazione completa → M3 lettura per agenti → M4 check e doctor → M5
`add` → M6 init e aggancio → M7 pipeline definitive e pacchetto).

**Fuori scope:** adapter, stato/resume, sottopipeline, trigger, libreria
globale, indice remoto, RBAC, telemetria.

**Criterio di successo:** §1.4.

### 3.1 Versione 3.0.1 — CI e protezione di `main`

Rinviata dalla 3.0.0 (decisione del maintainer, 2026-11-06): finché la 3.0.0
non è funzionante la usa solo lui in locale, e `ruff` + `pytest` si lanciano con
`uv run`. Si fa quando esiste una 3.0.0 funzionante.

- `.github/workflows/ci.yml`: `ruff check` + `pytest` su Python 3.11 e 3.15, su
  Ubuntu e Windows (era AC-V3-004, verifica `check`: l'evidenza è un run su
  GitHub, che richiede un push approvato).
- Protezione di `main` con i job del workflow come check obbligatori (azione
  del maintainer su GitHub).
- Rimettere in `docs/release-checklist.md` la riga "CI verde su Ubuntu e
  Windows, Python 3.11 e 3.15".
- Se i test sono stati scritti solo su Windows, il primo run su Ubuntu e su 3.15
  può far emergere differenze (path, fine riga): previsto tempo per correggerle.

---

## 4. Versione 3.1.0 — Adapter e conformità

**Obiettivo:** rendere *vincolanti*, su uno strumento specifico, le parti del
protocollo che in 3.0 sono convenzione. Misurare quanto bene un agente segue il
protocollo.

**Perché ora:** la 3.0 perde una cosa che la v2 aveva: l'isolamento
test-writer / implementer imposto dagli hook. Senza adapter è solo
un'istruzione. Il primo adapter recupera quella garanzia.

**Funzionalità:**
- **Interfaccia adapter:** un adapter è un pacchetto Python registrato come
  entry point (`lasagna.adapters`) con nome, versione, versioni di protocollo
  supportate. Riceve il registry risolto e produce file per lo strumento.
- **`lasagna adapt <tool> [--dry-run]`:** genera, rigenera o rimuove i file
  dello strumento. Ogni file generato porta un'intestazione "generated by
  lasagna adapt" e l'hash della sorgente. Rigenerare non tocca file senza
  quell'intestazione. `--dry-run` mostra il diff.
- **Campi di estensione:** gli adapter leggono solo chiavi `x-<tool>` nei nodi,
  nelle risorse e nei gate (già permesse dallo schema 3.0) e le convenzioni
  del nucleo.
- **Adapter `claude-code` (incluso):**
  - gate `check` → hook `Stop`/`SubagentStop` che esegue `lasagna check` e
    blocca se il gate è bloccante e fallisce;
  - risorse `subagent` con `ref` a un file `$pipeline/assets/*.md` → file in
    `.claude/agents/`;
  - risorse `skill` → link o copia in `.claude/skills/` se la skill è un asset
    della pipeline;
  - risorse con `access` → regole `PreToolUse` per i path dichiarati, con la
    stessa euristica su Bash della v2 (ostacolo, non muro);
  - isolamento test-writer / implementer della pipeline `implementation`
    tramite `x-claude-code: { isolation: ... }`, che reintroduce
    `block-test-edits`, `block-test-reads` e `block-code-reads` della v2.
- **Adapter `opencode` (incluso o della community, da decidere):** risoluzione
  delle skill in `.opencode/skills`, subagent nel suo formato.
- **`lasagna doctor --adapter <tool>`:** verifica anche skill, subagent e MCP nel
  formato dello strumento.
- **Suite di conformità del protocollo:** pipeline d'esempio più scenari con
  esito atteso ("dato questo stato dei file, il prossimo nodo è X"; "il gate
  fallisce → l'agente si ferma"). Si esegue con `claude plugin eval` per Claude
  Code e con script equivalenti per altri agenti. Il risultato è "l'agente X
  parla lasagna al N%". Riprende la suite di eval della v2.

**Milestone:** M1 interfaccia adapter + `adapt` con dry-run → M2 adapter
claude-code (gate e subagent) → M3 isolamento sui path → M4 suite di
conformità e primo report su Claude Code → M5 secondo adapter.

**Fuori scope:** adapter per agenti fatti in casa (basta il protocollo);
sandbox a livello di sistema operativo.

**Criterio di successo:** su questo repo, con l'adapter claude-code attivo, un
implementer che prova a leggere un test viene bloccato; un gate `check` che
fallisce impedisce di chiudere la sessione; la suite di conformità gira su
almeno due agenti.

**Criticità e punti aperti:**
- Un adapter della community che scrive hook equivale a eseguire codice
  altrui: serve la stessa politica di fiducia di `lasagna add` (§7.3).
- I file generati possono divergere se l'utente li modifica a mano: l'hash
  nell'intestazione rileva la modifica, `adapt` si rifiuta di sovrascrivere
  senza `--force`.
- Gli hook di Claude Code cambiano tra versioni: l'adapter dichiara la
  versione minima supportata.

**Prompt:**

```text
Versione 3.1.0 di lasagna: adapter e conformità.

Contesto: lasagna 3.0 è un protocollo (registry + pipeline YAML + rules.md) e
una CLI Python (init, validate, list, show, graph, check, doctor, add).
L'agente esegue le pipeline leggendo rules.md; resources, access e gate
non-check sono convenzioni. Lo schema permette chiavi x-<tool> ovunque.

Obiettivo: rendere vincolanti, su strumenti specifici, le parti che oggi sono
convenzione, senza che il protocollo dipenda da nessuno strumento. Una
pipeline deve continuare a funzionare senza adapter.

Funzionalità richieste:
1. Interfaccia adapter come entry point Python "lasagna.adapters": nome,
   versione, versioni di protocollo supportate, funzione pura
   plan(registry_risolto) -> lista di file da scrivere/rimuovere, più la shell
   che li applica.
2. Comando "lasagna adapt <tool> [--dry-run] [--remove] [--force]": file
   generati con intestazione e hash della sorgente; nessuna sovrascrittura di
   file modificati a mano senza --force; dry-run mostra il diff.
3. Adapter claude-code incluso: gate check -> hook Stop/SubagentStop che
   chiamano "lasagna check"; risorse subagent con asset -> .claude/agents/;
   skill come asset -> .claude/skills/; access sui path -> PreToolUse; isolamento
   test-writer/implementer della pipeline implementation (blocco di scrittura e
   lettura dei test per l'implementer, di lettura del codice per il
   test-writer), riprendendo comportamento e limiti dichiarati degli hook v2
   (docs/reference/lasagna-v2-spec.md §6.1).
4. Un secondo adapter (opencode) per dimostrare che l'interfaccia regge.
5. "lasagna doctor --adapter <tool>" che verifica skill/subagent/MCP nel
   formato dello strumento.
6. Suite di conformità del protocollo: scenari con esito atteso sul percorso
   nel grafo, sui gate e sui blocchi; eseguibile su Claude Code con
   "claude plugin eval" e su almeno un altro agente; report percentuale per
   agente.

Vincoli: FCIS come nella 3.0; nessuna modifica incompatibile al protocollo 3.0
(solo chiavi x-*); test senza rete; Windows, macOS, Linux.

Criterio di successo: su lasagna-cli con l'adapter claude-code, l'implementer
non può leggere i test, un gate check bloccante che fallisce impedisce la
chiusura, la suite di conformità gira su due agenti.

Da decidere nel grilling: opencode incluso o della community; politica di
fiducia per adapter di terzi; versione minima di Claude Code.
```

---

## 5. Versione 3.2.0 — Stato, resume e `foreach`

**Obiettivo:** portare nel protocollo, in modo opzionale, il "dove sono" che in
3.0 vive negli artefatti delle pipeline. Permettere cicli su liste (per ogni
ticket, per ogni criterio).

**Perché ora:** in 3.0 i contatori dei loop vivono nel contesto dell'agente e il
ciclo sui ticket è manuale (il `project-manager` dice qual è il prossimo, l'umano
apre la sessione). Funziona, ma non sopravvive a crash e non si automatizza.

**Funzionalità:**
- **`.lasagna/state.json`** (opzionale, attivato con `state: true` nel
  registry; nome già riservato in 3.0): run attive con id, pipeline, nodo
  corrente, input risolti, contatori di iterazione per arco, storia degli esiti
  dei gate, timestamp. Più run possono esistere insieme (una per ticket).
- **Comandi:**
  - `lasagna start <pipeline> --input k=v` restituisce un `run_id`;
  - `lasagna at <run>` mostra il nodo corrente, già renderizzato;
  - `lasagna done <run> [--outcome pass|fail]` registra l'esito, valuta gli
    archi e sposta il cursore;
  - `lasagna status`;
  - `lasagna resume <run>`;
  - `lasagna abort <run>`.

  Sono comandi pensati per l'agente: output breve, `--json`.
- **Checkpoint git opzionali:** `checkpoint: commit | stash | none` per
  pipeline. A ogni nodo chiuso, commit leggero (o ref) per poter tornare
  indietro. `lasagna rewind <run> <node>`.
- **Sottopipeline come scatola nera** (rinviate dalla 3.0, P11a): un nodo
  richiama un'altra pipeline registrata con `pipeline` e `with`; il chiamante
  vede solo `inputs`, `outputs` e l'esito (`completed` → `pass`, `blocked` →
  `fail`). Con `foreach` è il primo consumatore reale: da risolvere il caso del
  nodo `human` d'ingresso dentro una sottopipeline, e l'uso di `steps` con
  `pipeline` nello stesso nodo.
- **Nodo `foreach`:** `foreach: { items: <espressione su un input o su un file
  indice>, pipeline: <id>, order: declared | dependencies, session: same | new }`.
  Con `session: new` lasagna non lancia sessioni (non sa farlo in modo
  portabile): registra le run figlie e le dichiara pronte. Le avvia l'agente,
  l'umano o un adapter.
- **Aggiornamento delle pipeline incluse:** `project-manager` usa `foreach` sui
  ticket in ordine di dipendenza; `implementation` usa i contatori persistenti.
  Le versioni 3.0 delle pipeline restano valide.

**Milestone:** M1 formato `state.json` e comandi start/at/done → M2
resume/abort/status → M3 checkpoint git → M4 `foreach` → M5 pipeline incluse
aggiornate.

**Fuori scope:** esecuzione parallela reale dei rami (resta all'agente o
all'adapter); stato condiviso tra macchine (4.0).

**Criterio di successo:** una run di `implementation` interrotta a metà
riprende da `lasagna resume` in una nuova sessione con i contatori intatti;
`project-manager` elenca le run figlie dei ticket in ordine di dipendenza.

**Criticità e punti aperti:**
- `state.json` va in git o no? Proposta: no (locale), con `lasagna status
  --export` per il passaggio di consegne. Da decidere.
- Due sessioni che scrivono `state.json` insieme: serve un lock su file.
- Il rewind con git rischia di perdere lavoro non committato dell'utente:
  sempre con conferma e mai su file fuori dalla pipeline.

**Prompt:**

```text
Versione 3.2.0 di lasagna: stato opzionale, resume e foreach.

Contesto: in lasagna 3.0 il protocollo è senza stato. Le pipeline tengono
traccia di dove sono tramite i propri artefatti (current, ticket, changelog);
i contatori dei loop vivono nel contesto dell'agente; il ciclo sui ticket del
project-manager è manuale. Il nome .lasagna/state.json è riservato.

Obiettivo: stato opzionale nel protocollo, attivato dal registry, che permetta
resume dopo crash o in una nuova sessione, contatori persistenti e cicli su
liste, senza rendere obbligatorio nulla per chi non lo attiva.

Funzionalità richieste:
1. Formato state.json con più run attive: run_id, pipeline, versione, nodo
   corrente, input risolti, contatori per arco, storia degli esiti dei gate,
   timestamp. Lock su file per scritture concorrenti.
2. Comandi per agenti (output breve, --json): start, at, done (--outcome),
   status, resume, abort. La logica di avanzamento è una funzione pura
   (stato, pipeline, esito) -> nuovo stato, testata senza mock.
3. Checkpoint git opzionali per pipeline (commit | stash | none) e
   "lasagna rewind <run> <node>" con conferma obbligatoria.
4. Nodo foreach con items, pipeline, order (declared | dependencies), session
   (same | new). Con session: new lasagna registra le run figlie e le
   dichiara pronte; non avvia sessioni.
5. Nuove versioni minori delle pipeline incluse (project-manager con foreach
   sui ticket, implementation con contatori persistenti), mantenendo valide
   le versioni 3.0.

Vincoli: compatibilità totale con le pipeline 3.0; nessuno stato senza
"state: true"; FCIS; test senza rete; Windows, macOS, Linux.

Criterio di successo: una run di implementation interrotta riprende in una
nuova sessione con i contatori intatti; il project-manager mostra le run dei
ticket in ordine di dipendenza.

Da decidere nel grilling: state.json in git o locale; formato delle
espressioni di foreach.items; politica del rewind.
```

---

## 6. Versione 3.3.0 — Trigger e automazione

**Obiettivo:** introdurre `started_by: schedule` e `started_by: event` (con il
campo `trigger`, tolti dalla 3.0 perché solo descrittivi, P11b) e dare loro un
significato operativo. Prima pipeline autonoma: **issue GitHub → bugfix**.

**Funzionalità:**
- **`lasagna trigger <pipeline> --event <name> --payload <file>`:** il punto di
  ingresso unico per sistemi esterni. Valida che il nodo iniziale accetti quel
  `started_by`, crea la run (3.2) con il payload come input e stampa il prompt
  iniziale da dare all'agente in modalità headless.
- **Ricette di integrazione** (documentazione più template, non servizi):
  - GitHub Actions su `issues.labeled`;
  - cron di sistema;
  - routine di Claude Code;
  - `codex exec` e altri agenti headless.

  Lasagna non diventa un daemon.
- **Pipeline inclusa `issue-autofix`:** legge le issue con un'etichetta, fa
  triage (riproducibile? piccola? sicura?), le caratterizza con un test rosso
  (eredità del bugfix della v2), corregge, apre una PR. Il gate umano sulla PR
  è sempre presente. Merge automatico solo con un parametro esplicito e solo
  per classi di modifica dichiarate.
- **Modalità headless di `rules.md`:** sezione su come comportarsi quando nessun
  umano risponde. I gate `human` diventano "apri una richiesta e fermati"
  (commento sulla issue o PR in bozza), mai "procedi".

**Milestone:** M1 `trigger` + headless in `rules.md` → M2 ricetta GitHub
Actions → M3 `issue-autofix` → M4 prova su Fidelitree con issue reali.

**Fuori scope:** un server di webhook gestito da lasagna; permessi su chi può
attivare cosa (4.0).

**Criterio di successo:** su Fidelitree, una issue etichettata produce senza
intervento una PR con test rosso→verde, e si ferma al gate umano.

**Criticità e punti aperti:**
- Costi e sicurezza di agenti autonomi su CI: serve un budget (token, tempo,
  numero di issue per run) dichiarato nella pipeline.
- Prompt injection dal testo delle issue: `rules.md` headless deve trattare il
  payload come dati, mai come istruzioni.

**Prompt:**

```text
Versione 3.3.0 di lasagna: trigger e automazione.

Contesto: lasagna 3.2 ha stato e run (start/at/done/resume). started_by
vale solo agent o human: schedule ed event (con il campo trigger) vanno
introdotti nello schema in questa versione.

Obiettivo: permettere a sistemi esterni (GitHub Actions, cron, routine di
agenti) di avviare pipeline in modalità headless, senza che lasagna diventi un
servizio. Prima pipeline autonoma: issue GitHub -> bugfix -> PR.

Funzionalità richieste:
1. "lasagna trigger <pipeline> --event <name> --payload <file>": verifica che
   il nodo iniziale accetti quel trigger, crea la run, stampa il prompt
   iniziale per un agente headless.
2. Sezione headless del nucleo di rules.md: nessun gate human viene superato
   in automatico; in headless diventa "apri una richiesta (commento o PR in
   bozza) e fermati"; il payload è dato, mai istruzione.
3. Ricette documentate con template: GitHub Actions (issues.labeled),
   cron, routine di Claude Code, codex exec.
4. Pipeline inclusa issue-autofix: selezione delle issue per etichetta,
   triage (riproducibile, piccola, sicura), caratterizzazione con test
   rosso, fix, PR. Gate umano sempre presente; auto-merge solo con parametro
   esplicito e classi di modifica dichiarate. Budget dichiarato (issue per run,
   tempo, costo).
5. Prova su Fidelitree.

Vincoli: nessun daemon; nessun segreto nei file di pipeline; FCIS; test senza
rete (payload di esempio salvati).

Criterio di successo: su Fidelitree una issue etichettata produce una PR con
test rosso->verde e si ferma al gate umano.

Da decidere nel grilling: dove vive il budget; come la pipeline comunica il
blocco quando nessuno risponde; quali classi di modifica possono avere
auto-merge.
```

---

## 7. Versione 3.4.0 — Distribuzione e community

**Obiettivo:** trovare, installare, aggiornare e fidarsi di pipeline (e adapter)
scritte da altri.

**Funzionalità:**
- **Libreria globale e sorgenti remote** (rinviate dalla 3.0, P12):
  `~/.lasagna/library/<id>/<version>/` (override `LASAGNA_HOME`), `lasagna
  save`, `add library:<id>[@version]` e `add git+<url>[@ref][#subdir]`. Con
  l'hardening individuato dalla revisione del 2026-11-05 (P08, da approvare): niente
  symlink né file non regolari nella sorgente, `#subdir` dentro il clone, `git
  clone --depth 1 --no-recurse-submodules --`, URL e ref che non iniziano con
  `-`, `$pipeline/` che non esce dalla cartella della pipeline.
- **Indice delle pipeline:** un repo Git pubblico con un file indice (id,
  descrizione, sorgente, versioni, hash). Nessun server: l'indice è un file.
  `lasagna search <testo>`, `lasagna info <id>`.
- **Lockfile `.lasagna/pipelines.lock`:** per ogni pipeline copiata, sorgente,
  ref risolto (commit), hash del contenuto. `validate` segnala modifiche
  locali rispetto al lock.
- **`lasagna diff <id>` e `lasagna update <id>`:** confronto con la sorgente,
  aggiornamento con merge a tre vie (originale al lock, versione locale, nuova
  versione). Se ci sono conflitti, scrive i marcatori e si ferma.
- **Fiducia (§7.3):** prima di installare da una sorgente non fidata, `add`
  elenca tutto ciò che è eseguibile (comandi dei gate `check`, risorse `cli`,
  adapter) e chiede conferma (`--yes` per i non interattivi). Elenco di
  sorgenti fidate nella configurazione globale.
- **Composizione tra pacchetti:** una pipeline può dichiarare `requires:`
  (altre pipeline con intervallo di versione), che `add` risolve.

**Milestone:** M1 lockfile → M2 diff/update → M3 indice e search → M4 fiducia →
M5 requires.

**Fuori scope:** firma crittografica dei pacchetti (valutare dopo); registry
con account.

**Criterio di successo:** una pipeline pubblicata da un repo terzo si cerca, si
installa, si modifica in locale e si aggiorna senza perdere le modifiche locali.

**Criticità e punti aperti:**
- Supply chain: un gate `check` remoto è codice remoto. La conferma esplicita è
  il minimo; la firma è il passo successivo.
- Il merge a tre vie su YAML è delicato: va fatto sul testo, preservando i
  commenti.

**Prompt:**

```text
Versione 3.4.0 di lasagna: distribuzione e community.

Contesto: in lasagna 3.0 le pipeline si copiano da builtin o da cartelle locali
(lasagna add); non esistono libreria globale, save né add da git. La
provenienza (source, ref) è registrata nel registry ma non c'è lockfile né
aggiornamento.

Obiettivo: trovare, installare, aggiornare e fidarsi di pipeline di terzi,
senza un server.

Funzionalità richieste:
1. Lockfile .lasagna/pipelines.lock con sorgente, commit risolto, hash del
   contenuto; validate segnala derive locali.
2. "lasagna diff <id>" e "lasagna update <id>" con merge a tre vie testuale
   che preserva i commenti; conflitti come marcatori, poi stop.
3. Indice come file in un repo git pubblico; "lasagna search", "lasagna info".
4. Politica di fiducia: add da sorgente non fidata elenca comandi eseguibili
   (gate check, risorse cli, adapter) e chiede conferma; --yes per uso non
   interattivo; sorgenti fidate nella configurazione globale.
5. requires: tra pipeline con intervalli di versione, risolti da add.

Vincoli: compatibilità con registry 3.0; nessun server; test senza rete (repo
git locali di prova); FCIS.

Criterio di successo: una pipeline di un repo terzo si cerca, si installa, si
modifica in locale e si aggiorna senza perdere le modifiche.

Da decidere nel grilling: formato dell'indice; firma sì/no; dove vive la
configurazione globale delle sorgenti fidate.
```

---

## 8. Versione 4.0.0 — Team e governance

**Obiettivo:** lasagna per team: chi può avviare cosa, approvazioni reali,
osservabilità, valutazione della qualità dei processi.

**Perché 4.0 e non 3.x:** introduce un'identità e, per farla valere davvero, un
componente lato server o CI. È un cambio di natura del prodotto.

**Funzionalità:**
- **Permessi** (`permissions` per pipeline, gruppo e nodo):
  - `allowed_roles`;
  - `allowed_triggers`.

  L'identità viene da git (autore), dal CI (attore del workflow) o
  dall'adapter. Il documento lo dichiara esplicitamente: **in locale i permessi
  sono una convenzione**; diventano vincolanti in CI o con l'adapter.
- **Gate legati alle approvazioni reali:** `gate: { type: human, approval:
  pr_review | codeowners | label }`. In CI il gate passa solo se la PR ha
  l'approvazione richiesta.
- **Namespace e gruppi:** `namespace` del progetto, gruppi di pipeline con
  permessi ereditati (l'idea originale del registry).
- **Telemetria:** emissione di span OpenTelemetry per run, nodo e gate
  (richiede lo stato 3.2), con attributi standard (pipeline, versione, nodo,
  esito, durata, iterazioni). Esportazione su file o OTLP.
- **Valutazione:** giudizio LLM-as-judge per nodo (gate `agent` con rubrica
  versionata), confronto di versioni di pipeline sulla stessa suite di
  scenari, report di cicli, blocchi e tempi per nodo.
- **Dashboard:** report HTML statico generato da `lasagna report`, da stato e
  telemetria.

**Milestone:** M1 schema dei permessi + verifica in CI → M2 gate su
approvazioni PR → M3 telemetria → M4 valutazione e report.

**Criterio di successo:** in un repo con due persone, una pipeline con
`allowed_roles: [tech_lead]` non supera il gate in CI se approva un
`developer`; gli span di una run compaiono in un collector OTLP.

**Criticità e punti aperti:**
- Senza un componente lato CI o server, i permessi restano teatro: va scritto
  in modo onesto.
- Da dove vengono i ruoli (file nel repo, CODEOWNERS, IdP)? Decisione grande.
- Privacy della telemetria: mai contenuti di prompt o codice negli span per
  default.

**Prompt:**

```text
Versione 4.0.0 di lasagna: team e governance.

Contesto: lasagna 3.x è un protocollo di processo con CLI, adapter, stato
opzionale, trigger headless e distribuzione con lockfile. È pensato per un
singolo sviluppatore; non ha identità né permessi.

Obiettivo: renderlo utilizzabile da team con permessi, approvazioni reali,
osservabilità e valutazione, dichiarando in modo onesto cosa è vincolante
(CI/adapter) e cosa resta convenzione (locale).

Funzionalità richieste:
1. permissions (allowed_roles, allowed_triggers) a livello di gruppo,
   pipeline e nodo, con ereditarietà; namespace di progetto e gruppi nel
   registry.
2. Sorgenti di identità: autore git, attore CI, adapter; ruoli da un file del
   repo e/o da CODEOWNERS.
3. Gate human con approval: pr_review | codeowners | label, verificati in CI
   da "lasagna check".
4. Span OpenTelemetry per run, nodo e gate (file o OTLP), senza contenuti
   sensibili per default.
5. Valutazione: gate agent con rubrica versionata, confronto tra versioni di
   pipeline su una suite di scenari, report di cicli, blocchi e durate.
6. "lasagna report": dashboard HTML statica da stato e telemetria.

Vincoli: le pipeline 3.x senza permissions restano valide; FCIS; test senza
rete.

Criterio di successo: in un repo con due persone, un gate che richiede
tech_lead non passa in CI con l'approvazione di un developer; gli span di una
run compaiono in un collector OTLP.

Da decidere nel grilling: modello dei ruoli e sorgente di verità; cosa
rendere vincolante in locale; formato delle rubriche.
```

---

## 9. Criticità trasversali e proposte

Punti che non appartengono a una sola versione, o che vanno decisi presto.

1. **Regressione rispetto alla v2 sull'isolamento.** Nella 3.0
   test-writer e implementer sono isolati solo per istruzione, mentre la v2 lo
   imponeva con gli hook. È accettato per l'MVP (dogfooding su Claude Code, un
   solo sviluppatore attento), ma è il primo motivo della 3.1.
2. **Nome del pacchetto su PyPI.** `lasagna` è occupato da `lasagna-ai`, un
   framework per agenti AI. Pacchetto `lasagna-cli`, comando `lasagna`:
   `lasagna-cli` risulta libero (verificato il 2026-11-05). Si pubblica
   `3.0.0a1` appena `validate` funziona. Il nome di import `lasagna` può
   collidere con `lasagna-ai`: decisione aperta (spec §14.1).
3. **Nomi delle pipeline.** Proposti `project-manager` e `implementation`,
   senza il suffisso `-pipeline`: sono già dentro `pipelines/` e nel registry,
   e il suffisso allunga ogni comando (`lasagna show project-manager-pipeline`).
   Si cambia con una riga se preferisci il suffisso.
4. **Lingua.** I documenti di progetto (`docs/`) sono in italiano. Prodotto,
   `rules.md`, pipeline incluse, messaggi della CLI e README sono in
   inglese, come nella v2. `README.it.md` è la traduzione.
5. **Gate `agent` autoreferenziale.** Un agente che giudica il proprio lavoro è
   debole. `rules.md` raccomanda un subagent o una sessione separata quando il
   gate conta. Nella 4.0 arrivano le rubriche versionate.
6. **Condizioni in linguaggio naturale.** Non sono deterministiche, ed è
   accettato: chi vuole determinismo usa `when: pass/fail` dopo un gate
   `check`. Nessun linguaggio di espressioni prima della 3.2 (`foreach`).
7. **Templating minimo.** Si sostituiscono solo `{{ params.x }}` e
   `{{ inputs.x }}`; tutto il resto resta com'è, così il testo con
   Jinja o GitHub Actions (che usano `{{`) non si rompe.
8. **Pipeline come processo e come prodotto.** In questo repo le pipeline
   incluse sono codice sorgente (`src/lasagna/builtin/`) e insieme il processo
   con cui si lavora (`.lasagna/pipelines/`). Regola: il processo usa una
   copia congelata a inizio versione e il prodotto si modifica nei sorgenti;
   la copia si riallinea solo alla chiusura della versione (dettagli in
   `specs/v3.0.0.md` D11).
9. **Destino della v2 (deciso).** La v3 vive nel repository nuovo
   `lasagna-cli`. Il plugin v2 resta in `lasagna-code`, intatto e deprecato:
   nessun lavoro nuovo (spec D13). Da fare a mano: avviso di deprecazione nel
   README di `lasagna-code` e, quando la 3.0.0 esce, il link al nuovo
   repository.
