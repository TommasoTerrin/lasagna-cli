"""Hold a FileLock until the process is killed (used by lock tests)."""

import sys
import time
from pathlib import Path

from lasagna_cli.locking import FileLock

lock = FileLock(Path(sys.argv[1]))
lock.acquire()
print("ready", flush=True)
time.sleep(600)
