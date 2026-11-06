---
status: todo            # todo | in_progress | done | blocked
depends_on: []          # ticket numbers
criteria: [AC-001]      # from the spec
---

# NN — <title>

The `status` above is the only record of this ticket's state: the tickets index
and the current file never copy it.

## Goal

One or two sentences: what is true when this ticket is done.

## Context

What the implementer of this ticket needs to know and would not find in the
contract: why this slice, which spec sections, constraints. Link, do not copy.

## Changes

What changes, as a list. Include work no test can drive (deleting files,
configuration, documentation): it is done explicitly, never hidden.

## Files involved

Expected files to create or modify. An estimate, not a constraint, but the
files named here (and in Changes) are the ones the agent may write beyond the
folders its nodes declare.

## Tests to pass

<!-- Filled in by the implementation pipeline (node contract) as a checklist:
one line per planned verification, in order. The green node checks off a test
with `[x] (green after N)`; the review node checks off checks and reviews. -->
- [ ] AC-001 → `test_<behaviour>`
- [ ] AC-002 → check: `<command>`
- [ ] AC-003 → review: <what is reviewed>

## Contract

<!-- Filled in by the implementation pipeline (node contract), from its
contract template. -->

## Out of scope

What this ticket deliberately leaves to others (name the ticket if known).

## Definition of done

- [ ] every criterion has the verification the spec asks for: a test that fails on a plausible wrong implementation, a passing check, or a recorded review
- [ ] whole suite green
- [ ] changelog line under Unreleased
- [ ] traceability evidence filled in the tickets index; current file updated

## Log

<!-- One line per session: date | outcome | cycles used per criterion | summary of the [lasagna] lines | notes -->
