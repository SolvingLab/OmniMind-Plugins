"""Run the user-installed himalaya executable. The program is not bundled.

Arguments are passed only to a native executable. On Windows a .bat or .cmd
path is refused, because Windows may run those through cmd even when Python
shell is false. Missing configuration exits before any process starts.
"""

from __future__ import annotations

import os
import subprocess
import sys


def rejected_wrapper(path: str) -> bool:
    lower = path.lower()
    if lower.endswith((".bat", ".cmd")):
        return True
    return os.name == "nt" and not lower.endswith(".exe")


def main() -> int:
    binary = os.environ.get("HIMALAYA_BIN", "").strip()
    if not binary or not os.path.isfile(binary):
        print(
            "setup_required: HIMALAYA_BIN must be the user-installed himalaya file. No default.",
            file=sys.stderr,
        )
        return 2
    if rejected_wrapper(binary):
        print(
            "setup_required: HIMALAYA_BIN must be a native executable. "
            "On Windows that is a .exe. Batch wrappers are not dispatched.",
            file=sys.stderr,
        )
        return 2
    if len(sys.argv) < 2:
        print(
            "setup_required: pass himalaya arguments. This launcher does not connect an account or send mail.",
            file=sys.stderr,
        )
        return 2
    try:
        completed = subprocess.run([binary, *sys.argv[1:]], check=False, shell=False)
    except OSError as exc:
        print(f"setup_required: failed to start himalaya: {exc}", file=sys.stderr)
        return 2
    if completed.returncode is None:
        print("setup_required: himalaya did not report an exit status.", file=sys.stderr)
        return 2
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
