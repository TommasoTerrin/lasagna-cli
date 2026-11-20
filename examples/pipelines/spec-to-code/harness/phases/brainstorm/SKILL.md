---
name: brainstorm
description: Brainstorm phase of the spec-to-code Lasagna pipeline. Turns an idea into an approved spec with a verifiable checklist, through a conversation with the user.
---

# Brainstorm

You are in an interactive session with the user. Your job is to turn their
idea into a spec that another agent, with no access to this conversation, can
implement item by item.

## How to run the conversation

1. Ask what they want to build. Ask one question at a time, and prefer
   questions with concrete options.
2. Clarify goal, users, scope, what is out of scope, constraints (language,
   libraries, platform) and how each requirement will be verified.
3. When the picture is clear, propose a short kebab-case folder name under
   `specs/` (for example `specs/todo-app`) and show the full spec in chat.
4. Iterate until the user explicitly approves it.

## What to write once approved

1. Write `<folder>/spec.md` with these sections: Goal, Scope, Out of scope,
   Constraints, Requirements, Checklist.
2. The Checklist has one line per verifiable item, in implementation order,
   each starting with `- [ ]`. Each item must be small, concrete and checkable
   (a file exists, a command succeeds, a behaviour is observable). The
   Checklist is the only place where `- [ ]` may appear.
3. Write the folder as a line `spec-dir=<folder>` in the file named by the
   `LASAGNA_OUTPUT` environment variable, for example:
   `echo "spec-dir=specs/todo-app" >> "$LASAGNA_OUTPUT"`.
4. Tell the user to close the session. Lasagna will then wait for them to
   start the implementation phase.

Do not write any code in this phase.
