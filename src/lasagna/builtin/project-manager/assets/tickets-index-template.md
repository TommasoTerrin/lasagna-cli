# v<version> — tickets

Spec: `<path of the spec>`. One ticket at a time, one session per ticket, with
the implementation pipeline.

Status: **draft** | approved (YYYY-MM-DD)

The status line above is the approval of this plan. Slicing writes it as
`draft`; dispatch sets it to `approved` once the human has approved the plan.
The state of each ticket lives only in its own `status` field.

## Tickets

| # | Ticket | Depends on |
|---|---|---|
| 01 | [<title>](01-<slug>.md) (tracer bullet) | — |

## Execution order

1. 01 — <why first: thinnest end-to-end path>

Tickets with no dependency between them may run in any order; say which.

## Traceability

Every acceptance criterion of the spec appears exactly once. Verification is
taken from the spec (`test`, `check` or `review`). Evidence is filled in when
the ticket closes: the test names, the command run, or the review note.

| AC | Ticket | Verification | Evidence |
|---|---|---|---|
| AC-001 | 01 | test | |

## Cross-cutting conventions

Rules every ticket of this version follows (error style, naming, language of
docstrings, no network in tests…). Link the architecture file rather than
repeating it.
