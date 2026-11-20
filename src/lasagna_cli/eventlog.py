"""The run event log: the only code that writes or reads `.lasagna/runs/*.jsonl`."""

import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from lasagna_cli.locking import FileLock
from lasagna_cli.schemas import schema_errors


class CorruptLogError(Exception):
    """A log line that cannot be trusted, with its file and line number."""

    def __init__(self, path: Path, line: int, reason: str) -> None:
        self.path = path
        self.line = line
        self.reason = reason
        super().__init__(f"{path.as_posix()}:{line}: {reason}")


class InvalidEventError(ValueError):
    """An event that does not match the `run` schema; nothing was written."""


def utc_now() -> datetime:
    return datetime.now(UTC)


class EventWriter:
    """Appends validated events to one run log while the caller holds its lock.

    A last line without a trailing newline is an interrupted write: it is cut
    off when the writer opens the file, and a message goes to `warnings`.
    """

    def __init__(
        self,
        path: Path,
        run_id: str,
        lock: FileLock,
        *,
        now: Callable[[], datetime] = utc_now,
    ) -> None:
        if not lock.held:
            raise RuntimeError("run lock not held")
        self.path = path
        self.run_id = run_id
        self.warnings: list[str] = []
        self._now = now
        self._seq = self._recover()

    def _recover(self) -> int:
        if not self.path.exists():
            return 0
        data = self.path.read_bytes()
        if data and not data.endswith(b"\n"):
            keep = data.rfind(b"\n") + 1
            with self.path.open("r+b") as handle:
                handle.truncate(keep)
                handle.flush()
                os.fsync(handle.fileno())
            self.warnings.append(
                f"{self.path.as_posix()}: discarded {len(data) - keep} bytes "
                "of an interrupted write"
            )
            data = data[:keep]
        if not data:
            return 0
        count = data.count(b"\n")
        try:
            last = json.loads(data.splitlines()[-1].decode("utf-8"))
            return int(last["seq"])
        except (ValueError, KeyError, TypeError):
            raise CorruptLogError(self.path, count, "invalid last line") from None

    def append(self, event: str, **fields: object) -> dict:
        """Validate and append one event; returns it as written."""
        entry = {
            "v": 1,
            "seq": self._seq + 1,
            "ts": self._now().astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "run": self.run_id,
            "event": event,
            **fields,
        }
        errors = schema_errors("run", entry)
        if errors:
            detail = "; ".join(f"{field or '<event>'}: {msg}" for field, msg in errors)
            raise InvalidEventError(detail)
        line = (json.dumps(entry, ensure_ascii=False) + "\n").encode("utf-8")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        self._seq += 1
        return entry
