# Contract template

Copy these sections into the ticket's **Contract** section. The contract is
frozen once the gate of the contract node passes: the test-writer and the
implementer both work from it and from nothing else about each other. If it
must change, stop and say why; the human resumes from the contract node.

## Seams

The public boundary the tests live on: the function, command, endpoint or
module entry point. Tests never go lower than this.

## Signatures

```python
def decide_x(order: Order, now: datetime) -> Decision: ...
```

Names, parameters, types, return types. The implementer may not change them
for convenience.

## Data types

Fields and invariants of every type the signatures use that does not exist yet.

## Error types

| Error | Raised / returned when |
|---|---|

State the style: exceptions, result values, error codes — the project's
convention.

## Return shape

What success looks like, precisely enough that two people would write the same
assertion.

## External dependencies

Every source of I/O or non-determinism the code under test needs, and how the
tests control it. One row each: a missing row is two agents inventing two
different answers.

| Dependency | How the code reaches it | How tests control it |
|---|---|---|
| Current time | parameter `now: datetime` | fixed value |
| Storage | `Repo` (Protocol) | in-memory fake |
| Config | settings object | instance built in the test |

Default: a parameter when it is enough; an interface only when the
architecture guide's rule 3 applies; on an existing project, the mechanism the
project already uses.

## What is NOT frozen

Internals the tests must not assert on (helper names, private structure,
log messages, ordering where the spec does not promise one).
