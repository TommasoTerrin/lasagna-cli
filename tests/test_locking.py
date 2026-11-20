import subprocess
import sys
import time
from pathlib import Path

import pytest

from lasagna_cli.locking import FileLock, LockBusyError

HOLDER = Path(__file__).parent / "helpers" / "hold_lock.py"


def test_second_lock_on_same_path_is_busy(tmp_path):
    first = FileLock(tmp_path / "a.lock")
    second = FileLock(tmp_path / "a.lock")
    first.acquire()
    try:
        with pytest.raises(LockBusyError):
            second.acquire()
        assert first.held and not second.held
    finally:
        first.release()


def test_release_allows_reacquire(tmp_path):
    lock = FileLock(tmp_path / "a.lock")
    lock.acquire()
    lock.release()
    assert not lock.held
    other = FileLock(tmp_path / "a.lock")
    other.acquire()
    other.release()


def test_release_when_not_held_is_a_noop(tmp_path):
    FileLock(tmp_path / "a.lock").release()


def test_context_manager_releases_on_exception(tmp_path):
    path = tmp_path / "a.lock"
    with pytest.raises(RuntimeError):
        with FileLock(path) as lock:
            assert lock.held
            raise RuntimeError("boom")
    assert FileLock.is_free(path)


def test_different_paths_do_not_conflict(tmp_path):
    with FileLock(tmp_path / "a.lock"), FileLock(tmp_path / "b.lock"):
        pass


def test_acquire_creates_missing_folders(tmp_path):
    path = tmp_path / "runs" / "x.lock"
    with FileLock(path):
        assert path.is_file()


def test_is_free_reflects_state(tmp_path):
    path = tmp_path / "a.lock"
    assert FileLock.is_free(path)
    with FileLock(path):
        assert not FileLock.is_free(path)
    assert FileLock.is_free(path)


def test_is_free_on_missing_folder_creates_nothing(tmp_path):
    path = tmp_path / "nope" / "a.lock"
    assert FileLock.is_free(path)
    assert not path.parent.exists()


def test_lock_dies_with_process(tmp_path):
    path = tmp_path / "held.lock"
    proc = subprocess.Popen(
        [sys.executable, str(HOLDER), str(path)],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert proc.stdout.readline().strip() == "ready"
        assert not FileLock.is_free(path)
        proc.kill()
        proc.wait()
        deadline = time.monotonic() + 5
        while not FileLock.is_free(path) and time.monotonic() < deadline:
            time.sleep(0.05)
        assert FileLock.is_free(path)
    finally:
        proc.kill()
        proc.wait()
        proc.stdout.close()
