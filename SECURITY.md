# Security policy

lasagna is pre-alpha: version 3.0.0 is being built, and no release has been
published yet. Only the latest commit of `main` is supported.

## What to report

lasagna runs and installs things on your behalf, so the interesting problems
are the ones that make it run or copy something you did not expect:

- a pipeline that executes a command you did not review (the `run` of a `check`
  gate or route is executed by the CLI with the system shell);
- a way for a pipeline, ticket, issue or tool output to make an agent ignore
  `rules.md` or the human (prompt injection);
- path traversal, symlink or file-overwrite problems in `lasagna init` and
  `lasagna add`;
- secrets leaking into the registry, the generated files or the CLI output.

A pipeline is instructions for your agent and, through `check` gates, commands
for your shell. Treat a pipeline from a third party like code: read it before
you enable it (`lasagna add` from a local folder adds it disabled for this
reason).

## How to report

Please do **not** open a public issue. Use GitHub's private vulnerability
reporting: open the repository's **Security** tab and choose **Report a
vulnerability**.

Include what you did, what you expected and what happened, and the files
involved. You will get an answer as soon as the maintainer can, usually within
a week. Fixes land on `main` first and are mentioned in the changelog once
released.
