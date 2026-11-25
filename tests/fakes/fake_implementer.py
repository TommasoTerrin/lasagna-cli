"""Fake implement agent for the spec-to-code example; never calls a real agent.

With `one` it ticks the first unchecked item of `$LASAGNA_INPUT_SPEC_DIR/spec.md`;
with `none` it ticks nothing. Either way it rewrites the summary, as the skill
of the phase asks before every session ends.
"""

import os
import sys
from pathlib import Path


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "one"
    folder = Path(os.environ["LASAGNA_INPUT_SPEC_DIR"])
    spec = folder / "spec.md"
    text = spec.read_text(encoding="utf-8")
    if mode == "one":
        text = text.replace("- [ ]", "- [x]", 1)
        spec.write_text(text, encoding="utf-8", newline="\n")
    left = text.count("- [ ]")
    summary = f"Session {os.environ['LASAGNA_ITERATION']}: {left} items left.\n"
    (folder / "summary.md").write_text(summary, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
