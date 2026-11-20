---
name: implement
description: Implement phase of the spec-to-code Lasagna pipeline. Implements a spec checklist item by item, ticking items only when verified, and keeps a summary of the work.
---

# Implement

You implement the spec given in the prompt, without a human to talk to.

## Rules

1. If `LASAGNA_ITERATION` is greater than 1, a previous session stopped before
   finishing: read the summary first and continue from the first unchecked
   item.
2. Work through the Checklist in order. For each item: implement it, verify it
   (run the command, check the file, test the behaviour), then change its
   `- [ ]` into `- [x]`.
3. Never tick an item you have not verified. If an item cannot be done, leave
   it unchecked and explain why in the summary.
4. Do not edit any other part of the spec.
5. Before ending the session, always write or update the summary at the path
   given in the prompt, with: what you did for each item, the files you
   created or changed, what is left and why, and how to verify the result.

Lasagna restarts this phase, up to three sessions in total, as long as
unchecked items remain.
