"""Scripted fake agent for tests; it never calls Claude or the network.

It reads a JSON list of actions from the file named by FAKE_AGENT_SCRIPT and
runs them in order, in the current directory (the worktree):

- {"write": "path", "text": "..."}   write a file (parents created)
- {"append": "path", "text": "..."}  append to a file
- {"output": "name", "value": "v"}   append name=value to $LASAGNA_OUTPUT
- {"decision": "v"}                  append decision=v to $LASAGNA_OUTPUT
- {"next": "phase"}                  append next=phase to $LASAGNA_OUTPUT
- {"sleep": 1.5}                     sleep
- {"exit": 3}                        exit with that code at once
- {"log": "path"}                    append a JSON line with every LASAGNA_*
                                     variable and argv to a file
- {"probe": "path"}                  append a JSON line saying whether the file
                                     named by the whole prompt exists, and its size
- {"prompt_file": "text"}            append text to the file named by the whole
                                     prompt (an agent using ${{ lasagna.output }})

With no script the agent only exits 0.
"""

import json
import os
import sys
import time
from pathlib import Path


def append(path: str, line: str) -> None:
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(line)


def main() -> int:
    script = os.environ.get("FAKE_AGENT_SCRIPT")
    actions = json.loads(Path(script).read_text(encoding="utf-8")) if script else []
    for action in actions:
        if "write" in action:
            target = Path(action["write"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(action.get("text", ""), encoding="utf-8", newline="\n")
        elif "append" in action:
            target = Path(action["append"])
            target.parent.mkdir(parents=True, exist_ok=True)
            append(str(target), action.get("text", ""))
        elif "output" in action:
            append(
                os.environ["LASAGNA_OUTPUT"], f"{action['output']}={action['value']}\n"
            )
        elif "decision" in action:
            append(os.environ["LASAGNA_OUTPUT"], f"decision={action['decision']}\n")
        elif "next" in action:
            append(os.environ["LASAGNA_OUTPUT"], f"next={action['next']}\n")
        elif "sleep" in action:
            time.sleep(float(action["sleep"]))
        elif "log" in action:
            variables = {
                k: v for k, v in os.environ.items() if k.startswith("LASAGNA_")
            }
            append(
                action["log"],
                json.dumps({"env": variables, "argv": sys.argv[1:]}) + "\n",
            )
        elif "probe" in action:
            target = Path(os.environ["LASAGNA_PARAM_PROMPT"])
            size = target.stat().st_size if target.is_file() else None
            append(action["probe"], json.dumps({"size": size}) + "\n")
        elif "prompt_file" in action:
            append(os.environ["LASAGNA_PARAM_PROMPT"], action["prompt_file"])
        elif "exit" in action:
            return int(action["exit"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
