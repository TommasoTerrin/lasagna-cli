---
name: green
description: Green phase of the tdd Lasagna pipeline. Changes the code until the red test and all other tests pass.
---

# Green

Change production code until the test named in the prompt passes, without
breaking other tests and without changing the test. The phase is repeated
until `npm test` passes: if `LASAGNA_ITERATION` is greater than 1, run the
tests first and start from the failures.
