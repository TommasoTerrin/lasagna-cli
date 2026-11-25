"""Stub program for tests: records its argv and OPENCODE_CONFIG_CONTENT."""

import json
import os
import sys

with open(os.environ["RECORD_FILE"], "a", encoding="utf-8") as handle:
    line = {"argv": sys.argv[1:], "config": os.environ.get("OPENCODE_CONFIG_CONTENT")}
    handle.write(json.dumps(line) + "\n")
