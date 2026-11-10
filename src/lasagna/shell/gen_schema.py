"""Write the registry and pipeline JSON Schema files to a directory."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from lasagna.core.schema import render_schema


def write_schema(out_dir: Path) -> None:
    for kind in ("registry", "pipeline"):
        (Path(out_dir) / f"{kind}.schema.json").write_bytes(
            render_schema(kind).encode("utf-8")
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: python -m lasagna.shell.gen_schema OUT_DIR", file=sys.stderr)
        return 2
    write_schema(Path(args[0]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
