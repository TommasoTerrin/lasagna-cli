"""Fake long-running program: optionally record its pid, then sleep."""

import os
import sys
import time
from pathlib import Path

if len(sys.argv) > 1:
    Path(sys.argv[1]).write_text(str(os.getpid()), encoding="utf-8")
time.sleep(600)
