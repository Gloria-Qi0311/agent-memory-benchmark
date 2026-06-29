"""Per-task experiment runners.

Each task has its own runner function (write → read → judge per case)
because the schemas, probe shapes, and metrics differ. Shared helpers
live here; task-specific functions are added as tasks are built.

v0 fusion + rewrite runners were removed when v1 superseded those tasks.
T4 (split intake) and later v1 tasks add their runners here.
"""
import json
import sys
import traceback
from pathlib import Path


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)
