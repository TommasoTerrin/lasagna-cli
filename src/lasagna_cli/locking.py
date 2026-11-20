"""Operating-system file locks, released by the system when the process dies."""

import os
import sys
from pathlib import Path
from types import TracebackType

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


class LockBusyError(Exception):
    """Raised when another holder already has the lock."""


class FileLock:
    """Exclusive, non-blocking lock on a file (one byte at offset 0).

    The file is created on `acquire` and never deleted.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._fd: int | None = None

    @property
    def held(self) -> bool:
        return self._fd is not None

    def acquire(self) -> None:
        """Take the lock or raise `LockBusyError`."""
        if self._fd is not None:
            raise RuntimeError("lock already held by this object")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT)
        try:
            _lock(fd)
        except OSError:
            os.close(fd)
            raise LockBusyError(f"lock is held elsewhere: {self.path}") from None
        self._fd = fd

    def release(self) -> None:
        """Release the lock; a no-op when it is not held."""
        if self._fd is None:
            return
        fd, self._fd = self._fd, None
        try:
            _unlock(fd)
        finally:
            os.close(fd)

    @staticmethod
    def is_free(path: Path) -> bool:
        """True if nobody holds the lock. Never creates the file."""
        if not path.exists():
            return True
        probe = FileLock(path)
        try:
            probe.acquire()
        except LockBusyError:
            return False
        probe.release()
        return True

    def __enter__(self) -> "FileLock":
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()


if sys.platform == "win32":

    def _lock(fd: int) -> None:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)

    def _unlock(fd: int) -> None:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)

else:

    def _lock(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)
