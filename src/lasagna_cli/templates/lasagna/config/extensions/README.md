# Extensions (not active in the MVP)

An extension is a new type that inherits from a primitive (`human`, `machine`,
`agent`, `pipeline`, `phase`) or from another extension. It gives objects
features the base protocol lacks, without touching the primitives. As in
object-oriented programming, an extension can add fields or redefine an
existing one; redefinitions are at the author's risk, and `lasagna validate`
will warn when a redefined field is no longer compatible with the parent's.

## Planned shape

Each extension is a folder in `config/extensions/`:

```
config/extensions/
└── tech-lead/
    ├── extension.yaml
    └── README.md
```

```yaml
# extension.yaml
name: tech-lead
extends: human                 # a primitive or another extension
description: A human with roles, assignable to phases by role.
schema:                        # added or redefined fields, as JSON Schema
  properties:
    roles:
      type: array
      items: { type: string }
  required: [roles]
```

An instance uses it by declaring the type:

```yaml
# actors/marco.yaml
type: tech-lead
name: marco
roles: [backend, review]
```

## Planned rules

Single inheritance. Merging with the parent type follows fixed rules:
`properties` are merged, `required` lists are joined, a redefined field
replaces the parent's. For the engine an instance keeps its root primitive: a
`tech-lead` runs as a `human`. New fields only have an effect if something
reads them, for example a hook or a plugin: how an extension can define
behaviour, not just structure, is the first question to settle when extensions
enter the protocol.

## Technical note

In the MVP the primitive schemas are closed (`additionalProperties: false`) to
catch typos. To compose them with `allOf` they will have to be opened, and the
closing will move to the validator, which will apply
`unevaluatedProperties: false` to the final type of each object.

## Planned examples

Humans with roles, assignments and tenants. Machines with execution
constraints (hosts, addresses, workers). Agents with a standard definition of
skill and MCP injection. Pipelines with priorities and active triggers
(schedules, events). Phases with deterministic hooks or extra completion
criteria (`done_when`).
