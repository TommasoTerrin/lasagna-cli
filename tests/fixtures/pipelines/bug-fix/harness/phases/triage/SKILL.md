---
name: triage
description: Triage phase of the bug-fix Lasagna pipeline. Analyses an issue with the user and writes a bug report with the proposed fix.
---

# Triage

You are in an interactive session with the user. Read the issue named in the
prompt, ask questions until cause and fix are clear, then write the report at
the given path: description, steps to reproduce, likely cause, proposed fix,
files involved. Finally write the severity as a line `severity=low|medium|high`
in the file named by `LASAGNA_OUTPUT`.
