#!/usr/bin/env python3
"""Report what this tool needs and does not have. Written by package.py.

    python check_install.py

Exits 1 if anything is missing, so a handoff can gate on it.
"""

import importlib.util
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BINARIES = ['ffmpeg', 'node']

# A requirement line maps to an import name only sometimes. These are the ones
# where the two differ across this tool set.
IMPORT_NAME = {
    "opencv-python-headless": "cv2",
    "opencv-python": "cv2",
    "faster-whisper": "faster_whisper",
    "pillow": "PIL",
    "pyyaml": "yaml",
}


def wanted():
    req = HERE / "requirements.txt"
    if not req.is_file():
        return []
    out = []
    for line in req.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        name = line.split("==")[0].split(">=")[0].split("<")[0].strip()
        if name:
            out.append(name)
    return out


def main():
    missing = []
    for b in BINARIES:
        ok = shutil.which(b) is not None
        print(("  ok    " if ok else "  MISS  ") + b + "  (on PATH)")
        if not ok:
            missing.append(b)
    for pkg in wanted():
        mod = IMPORT_NAME.get(pkg.lower(), pkg.replace("-", "_"))
        ok = importlib.util.find_spec(mod) is not None
        print(("  ok    " if ok else "  MISS  ") + pkg + "  (import " + mod + ")")
        if not ok:
            missing.append(pkg)
    if not BINARIES and not wanted():
        print("  nothing declared")
    print()
    if missing:
        print("missing: " + ", ".join(missing))
        return 1
    print("everything this tool needs is present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
