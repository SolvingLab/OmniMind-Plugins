"""Protocol check for the NetSuite connect adapter. Not a live ERP session."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "tests" / "check_protocol.mjs"


def main() -> int:
    node = shutil.which("node")
    if not node:
        print("node is required to run the NetSuite protocol check", file=sys.stderr)
        return 1
    completed = subprocess.run([node, str(CHECK)], check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
