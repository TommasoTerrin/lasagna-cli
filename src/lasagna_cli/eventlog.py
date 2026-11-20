"""The run event log: the only code that writes or reads `.lasagna/runs/*.jsonl`."""

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
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


@dataclass(frozen=True)
class LogRead:
    """What `read_log` found: the complete events and any warnings."""

    events: list[dict]
    warnings: list[str]


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


def read_log(path: Path) -> LogRead:
    """Read a run log, checking every line.

    A last line without a trailing newline is an interrupted write: it is
    ignored and reported as a warning. Anything else wrong is corruption.
    """
    pieces = path.read_bytes().split(b"\n")
    partial = pieces.pop()  # b"" when the file ends with a newline
    events: list[dict] = []
    for number, raw in enumerate(pieces, start=1):
        events.append(_check_line(path, number, raw, events))
    warnings = []
    if partial:
        warnings.append(f"{path.as_posix()}: ignored an interrupted last line")
    return LogRead(events, warnings)


def read_events(path: Path) -> list[dict]:
    """The complete events of a log, without the warnings."""
    return read_log(path).events


def _check_line(path: Path, number: int, raw: bytes, previous: list[dict]) -> dict:
    def corrupt(reason: str) -> CorruptLogError:
        return CorruptLogError(path, number, reason)

    if not raw.strip():
        raise corrupt("blank line")
    try:
        event = json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        raise corrupt("invalid UTF-8") from None
    except ValueError:
        raise corrupt("invalid JSON") from None
    errors = schema_errors("run", event)
    if errors:
        field, message = errors[0]
        raise corrupt(f"{field}: {message}" if field else message)
    if event["run"] != path.stem:
        raise corrupt(f"run must be '{path.stem}'")
    expected = len(previous) + 1
    if event["seq"] != expected:
        raise corrupt(f"seq must be {expected}, found {event['seq']}")
    if not previous and event["event"] != "run_started":
        raise corrupt("first event must be run_started")
    return event
