"""Fake process tree: start a sleeper child (pid in argv[1]), then stay alive."""

import subprocess
import sys
import time
from pathlib import Path

sleeper = Path(__file__).with_name("sleeper.py")
subprocess.Popen([sys.executable, str(sleeper), sys.argv[1]])
time.sleep(600)
