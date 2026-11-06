# v<version> — specification

> Status: **draft** | approved (YYYY-MM-DD, by whom)
> Decisions: <who decides>. Written by: <who wrote it>.

<!-- A spec is self-sufficient: a session starting from nothing must be able to
build the version from this file plus the repository. Keep every section; write
"none" rather than deleting one. -->

## 1. Context

Where the product stands today and why this version exists. Links to the
artifacts that matter (architecture file, previous spec, issues).

## 2. Goals and non-goals

### Goals
1. <outcome, verifiable>

### Non-goals
- <what this version deliberately does not do, and where it goes instead>

## 3. Decisions

Closed during grilling. To change one, stop and discuss it: never work around
it silently.

### D1 — <title>
- **What**:
- **Why**:
- **Rejected**: <alternative and why not>

## 4. Behaviour

Use cases, commands or flows, in the form that fits the product. For each: who
starts it, the main flow, the alternative flows, what must NOT change when it
fails.

## 5. Acceptance criteria

Every criterion is verifiable, and belongs to exactly one ticket after
slicing. The Verification column says how: `test` (an automated test),
`check` (a command that must pass, e.g. CI or a build) or `review` (a human or
adversarial review).

| ID | Criterion | Verification |
|---|---|---|
| AC-001 | <Given … When … Then …, or a precise statement> | test |

## 6. Error cases

| Error | When | What the user sees | What must not change |
|---|---|---|---|

## 7. External dependencies

Everything outside the code (network, storage, clock, randomness, third-party
services) and how it is reached.

## 8. Rollback

Only if the version is deployed: how to go back, and what data survives.

## 9. Open points

Questions not yet decided, each with who decides and before which ticket.
