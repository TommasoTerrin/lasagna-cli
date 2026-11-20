---
name: quick-fix
description: Quick-fix phase of the bug-fix Lasagna pipeline. Applies a minimal fix based on the bug report.
---

# Quick fix

Read the report named in the prompt and apply the smallest possible fix. The
phase is repeated until `npm test` passes: if `LASAGNA_ITERATION` is greater
than 1, run the tests first and start from the failures.
