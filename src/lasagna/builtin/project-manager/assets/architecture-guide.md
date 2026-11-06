# Architecture guide: functional core, imperative shell

Reference for the grilling question on the separation level, and for anyone
writing the project's architecture file. The project's own conventions always
win over this guide.

## The principle

- **Core**: functions (or plain classes) that receive data and return data,
  applying the business rules. No I/O, no clock, no randomness, no environment
  variables.
- **Shell**: endpoints, CLI, jobs, database/file/network access. It gathers the
  data, calls the core, applies what the core decided. Thin, with few `if`s and
  no business rule.

Expected effect: the core is tested by passing values, **without mocks**; fakes
are needed only where there is an abstraction (rule 3); end-to-end tests are
few and check the wiring.

## Five rules

1. **Logic lives in "poor" modules**: the standard library plus a few
   foundational libraries declared in the architecture file (e.g. pydantic).
   A guideline, not a mechanical check.
2. **I/O stays at the edges.** Logic receives values: `now` is a parameter,
   configuration is an object.
3. **An abstraction (Protocol / interface) only when it pays**: the technology
   may really change, or the test must replace something slow or
   non-deterministic, or two implementations already exist. Otherwise pass a
   value or a function.
4. **Vendor types do not enter the logic**: HTTP errors, ORM models, SDK
   objects are translated at the edge. This is what makes migrations local.
5. **Organise by feature, not by technical layer** (`billing/`, `auth/` rather
   than `domain/`, `adapters/`). File names say the behaviour
   (`decide_registration`), not the role (`service`). In a small project
   `logic.py` + `app.py` is enough.

## Separation levels (decided in grilling)

| Level | When | Shape |
|---|---|---|
| **minimal** | little business logic, scripts, simple CRUD | one pure logic module plus the edges |
| **modular** (recommended default) | non-trivial logic, some external dependencies | modules per feature, pure core per module, interfaces only on external dependencies that deserve one |
| **full hexagonal** | complex domain, several real adapters for the same port, strong consistency constraints | explicit ports and adapters, aggregates |

Present the question with a recommendation and its reason; record the answer
in the architecture file.

## When an abstraction is not needed

- current time → a `now` parameter;
- a single operation → a callable;
- configuration → a settings object;
- **most often**: move the I/O to the shell. Instead of
  `cancel(store, order_id)` write `cancel(order, now) -> Order` (pure); the
  shell does get → cancel → save. No dependency, no fake.

## Existing projects

- First **detect** the conventions (where the logic lives, error style,
  dependency injection, test style, folder layout) and write them in the
  architecture file, confirmed by the human.
- New code follows those conventions even where they differ from the rules
  above.
- Improvements (including "apply FCIS to this module") are written as
  proposals with reason and estimated cost, never applied without discussion.
- Severe spaghetti code that blocks the work: ask the human, with options.

Sources: Gary Bernhardt, *Boundaries* (2012); Kenneth Lange, *The Functional
Core, Imperative Shell Pattern*.
