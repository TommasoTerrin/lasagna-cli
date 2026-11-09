# v3.0.0 — tickets

Spec: `docs/specs/v3.0.0.md`. One ticket at a time, one session per ticket, with
the implementation pipeline.

Status: **approved (2026-11-06)**

The status line above is the approval of this plan. Slicing writes it as
`draft`; dispatch sets it to `approved` once the human has approved the plan.
The state of each ticket lives only in its own `status` field.

## Tickets

| # | Ticket | Depends on |
|---|---|---|
| 01 | [Tracer bullet: script `lasagna`, `--version`, `validate` minimo](01-tracer-bullet.md) (tracer bullet) | — |
| 02 | [Modello completo, chiavi `x-*`, JSON Schema](02-full-model-and-schema.md) | 01 |
| 03 | [Regole del grafo (V07, V10, V12), `--json` e formato dei messaggi](03-graph-rules-and-messages.md) | 02 |
| 04 | [Templating, `$pipeline/` e `lasagna show`](04-templating-and-show.md) | 02 |
| 05 | [`lasagna list` e `lasagna graph`](05-list-and-graph.md) | 02 |
| 06 | [Regole di validazione restanti, avvisi e `--strict`](06-remaining-validation-rules.md) | 03, 04 |
| 07 | [`lasagna check`](07-check.md) | 04 |
| 08 | [`lasagna doctor`](08-doctor.md) | 07 |
| 09 | [`lasagna add`](09-add.md) | 05, 06 |
| 10 | [`lasagna init`, `AGENTS.md`/`CLAUDE.md`, `rules.md` definitivo](10-init-and-rules.md) | 09 |
| 11 | [Contratto della CLI su tutti i comandi](11-cli-contract.md) | 08, 10 |
| 12 | [Pipeline incluse definitive](12-builtin-pipelines.md) | 06 |
| 13 | [README e pacchetto pubblicabile](13-readme-and-package.md) | 10, 12 |

## Execution order

1. 01 — la via più sottile da capo a fondo: script, `--version`, `validate`
   con tre regole e purezza di `core/` dal primo modulo (la CI è della 3.0.1).
2. 02 — il modello completo: senza, nessun altro comando legge pipeline vere,
   e il `.lasagna/` di questo repo non si può auto-validare.
3. 03 — regole del grafo e formato dei messaggi, che tutte le regole
   successive riusano.
4. 04 — templating e `show`: la vista per agenti; `core/render.py` serve a
   06 e 07.
5. 05 — `list` e `graph`; `shell/builtin.py` serve a 09.
6. 06 — chiude la validazione (matrice di AC-V3-007): serve ad `add` e alle
   pipeline incluse.
7. 07 — `check`.
8. 08 — `doctor` (con path con spazi anche per `check`).
9. 09 — `add`.
10. 10 — `init` (riusa `add` per `--with`) e `rules.md` definitivo.
11. 11 — contratto della CLI: arriva quando tutti i comandi esistono.
12. 12 — pipeline incluse definitive.
13. 13 — README e pacchetto.

Senza dipendenze tra loro: 03, 04 e 05 (dopo 02); 07 rispetto a 05 e 06;
12 rispetto a 07–11. L'ordine sopra è quello consigliato.

## Traceability

Every acceptance criterion of the spec appears exactly once. Verification is
taken from the spec (`test`, `check` or `review`). Evidence is filled in when
the ticket closes: the test names, the command run, or the review note.

I criteri ritirati AC-V3-004, AC-V3-012, AC-V3-031, AC-V3-032 e AC-V3-033 (spec §13) non
hanno ticket.

| AC | Ticket | Verification | Evidence |
|---|---|---|---|
| AC-V3-001 | 01 | check | |
| AC-V3-002 | 01 | test | |
| AC-V3-003 | 01 | test | |
| AC-V3-005 | 02 | test | |
| AC-V3-006 | 02 | test | |
| AC-V3-007 | 06 | test | |
| AC-V3-008 | 06 | test | |
| AC-V3-009 | 03 | test | |
| AC-V3-010 | 03 | test | |
| AC-V3-011 | 03 | test | |
| AC-V3-013 | 03 | test | |
| AC-V3-014 | 02 | test | |
| AC-V3-015 | 04 | test | |
| AC-V3-016 | 04 | test | |
| AC-V3-017 | 04 | test | |
| AC-V3-018 | 04 | test | |
| AC-V3-019 | 04 | test | |
| AC-V3-020 | 05 | test | |
| AC-V3-021 | 05 | test | |
| AC-V3-022 | 01 | test | |
| AC-V3-023 | 07 | test | |
| AC-V3-024 | 10 | test | |
| AC-V3-025 | 08 | test | |
| AC-V3-026 | 08 | test | |
| AC-V3-027 | 08 | test | |
| AC-V3-028 | 09 | test | |
| AC-V3-029 | 09 | test | |
| AC-V3-030 | 09 | test | |
| AC-V3-034 | 10 | test | |
| AC-V3-035 | 10 | test | |
| AC-V3-036 | 10 | test | |
| AC-V3-037 | 10 | test | |
| AC-V3-038 | 11 | test | |
| AC-V3-039 | 12 | check | |
| AC-V3-040 | 12 | test | |
| AC-V3-041 | 12 | test | |
| AC-V3-042 | 13 | review | |
| AC-V3-043 | 13 | check | |
| AC-V3-044 | 11 | test | |
| AC-V3-045 | 03 | test | |
| AC-V3-046 | 11 | test | |
| AC-V3-047 | 09 | test | |
| AC-V3-048 | 10 | test | |
| AC-V3-049 | 06 | test | |

## Cross-cutting conventions

- Design, layout e comandi: [`docs/architecture.md`](../../architecture.md).
  `core/` puro (AC-V3-022 vale per ogni modulo nuovo), shell sottile, `cli.py`
  solo parsing.
- Ogni test porta il criterio in un commento accanto: `# AC-V3-NNN`.
- Codice, docstring e messaggi della CLI in inglese; i documenti in `docs/`
  in italiano (AGENTS.md, regola 5).
- Messaggi d'errore: inglese, su stderr, con la correzione suggerita; exit 0
  ok, 1 contenuto, 2 uso (spec §8). La tabella §8.11 completa è del ticket 11.
- Nessuna rete nei test; i test devono poter girare su Windows e Linux (la CI che lo verifica è della 3.0.1). Path con
  `pathlib`, `/` nei file YAML.
- D11: i ticket modificano solo `src/lasagna/builtin/` e
  `src/lasagna/protocol/rules.md`, mai `.lasagna/` (salvo hotfix di processo
  approvato, AGENTS.md regola 2).
- I punti aperti del §14 (e le proposte P08, P18, P19 della revisione M0) si
  chiedono al maintainer prima del ticket che li tocca: ogni ticket lo dice
  nel suo Context.
- `depends_on` usa numeri di ticket a due cifre tra virgolette (`["01"]`).
- Commit e push solo con l'approvazione del maintainer; Conventional Commits.
