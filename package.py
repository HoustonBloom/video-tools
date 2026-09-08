#!/usr/bin/env python3
"""Package a tool folder into a self-contained copy anyone can drop into
~/.claude/skills/, and refuse to ship one that carries a path off this machine.

    python package.py              # every folder holding a SKILL.md
    python package.py tighten      # named ones only
    python package.py --check      # gate and report, write nothing

For each tool it writes dist/<name>/ and dist/<name>.zip, where <name> comes from
the SKILL.md frontmatter rather than the folder, so `shorts` keeps shipping as
`shorts-director`.

THE GATE. A shipped copy may not contain a path off this machine. The scan runs
over every text file in the staged copy before the zip is written, and a hit
stops that tool with a non-zero exit and no zip. This was a shell one-liner in
README.md that had to be remembered. Now it cannot be skipped.

WHAT IS LEFT OUT. Compiled Python, editor droppings, and anything listed one per
line in a tool's own `.packageignore`. A tool that ships a curated subset says so
there, beside the thing it is excluding, rather than in this file.

Every package gets `check_install.py`, generated here, which reads the packaged
requirements.txt and the binaries named in SKILL.md and reports what is missing.
"""

import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"

# A hit on any of these in a staged text file stops the package.
MACHINE = ("Claude_Projects", "C:/Users", "C:\\Users", "Obsidian_MCP", str(Path.home()))

# _deprecated/ holds superseded versions and never ships.
SKIP_DIRS = {"__pycache__", ".git", ".pytest_cache", "node_modules", ".ipynb_checkpoints", "_deprecated"}
SKIP_SUFFIX = {".pyc", ".pyo", ".swp", ".DS_Store"}
# Every text type is scanned, stylesheets and pages included.
TEXT_SUFFIX = {".py", ".md", ".txt", ".json", ".mjs", ".js", ".yml", ".yaml", ".cfg", ".toml", ".css", ".html", ".vtt", ""}

CHECK_INSTALL = '''#!/usr/bin/env python3
"""Report what this tool needs and does not have. Written by package.py.

    python check_install.py

Exits 1 if anything is missing, so a handoff can gate on it.
"""

import importlib.util
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BINARIES = {binaries}

# A requirement line maps to an import name only sometimes. These are the ones
# where the two differ across this tool set.
IMPORT_NAME = {{
    "opencv-python-headless": "cv2",
    "opencv-python": "cv2",
    "faster-whisper": "faster_whisper",
    "pillow": "PIL",
    "pyyaml": "yaml",
}}


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
'''


def skill_name(folder):
    skill = folder / "SKILL.md"
    if skill.is_file():
        m = re.search(r"^name:\s*(\S+)", skill.read_text(encoding="utf-8", errors="replace"), re.M)
        if m:
            return m.group(1).strip()
    return folder.name


def binaries_in(folder):
    """Binaries this tool needs on PATH: the ones its SKILL.md names, plus the
    runtime its scripts are written in. loudness is one .mjs file and named no
    binary but node, so reading the SKILL.md alone reported it as needing
    nothing."""
    found = set()
    skill = folder / "SKILL.md"
    if skill.is_file():
        text = skill.read_text(encoding="utf-8", errors="replace").lower()
        found |= {b for b in ("ffmpeg", "ffprobe") if b in text}
    suffixes = {p.suffix for p in folder.rglob("*") if p.is_file()}
    if suffixes & {".mjs", ".js"}:
        found.add("node")
    return sorted(found)


def ignore_patterns(folder):
    f = folder / ".packageignore"
    if not f.is_file():
        return []
    return [l.strip() for l in f.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]


def stage(folder, out):
    ignores = ignore_patterns(folder)
    copied = []
    for src in sorted(folder.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(folder)
        if any(p in SKIP_DIRS for p in rel.parts):
            continue
        if src.suffix in SKIP_SUFFIX or src.name == ".packageignore":
            continue
        posix = rel.as_posix()
        if any(posix == pat or posix.startswith(pat.rstrip("/") + "/") for pat in ignores):
            continue
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(posix)
    return copied


def gate(out):
    hits = []
    for p in sorted(out.rglob("*")):
        if not p.is_file() or p.suffix not in TEXT_SUFFIX:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            for needle in MACHINE:
                if needle and needle in line:
                    hits.append((p.relative_to(out).as_posix(), line_no, needle))
    return hits


def package(folder, write):
    """Stage somewhere disposable, gate there, and only then touch dist/.

    Staging directly into dist/ would let a refused package's cleanup remove the
    shipped copy. Nothing under dist/ is removed until a package has passed.
    """
    name = skill_name(folder)
    print(folder.name + " -> dist/" + name)

    tmp = Path(tempfile.mkdtemp(prefix="package-" + name + "-"))
    staged = tmp / name
    staged.mkdir(parents=True)
    try:
        copied = stage(folder, staged)
        (staged / "check_install.py").write_text(
            CHECK_INSTALL.format(binaries=repr(binaries_in(folder))), encoding="utf-8")
        copied.append("check_install.py")

        hits = gate(staged)
        if hits:
            print("  REFUSED. A path off this machine reached the staged copy:")
            for rel, line_no, needle in hits[:10]:
                print("    " + rel + ":" + str(line_no) + "  " + needle)
            print("  dist/" + name + " left as it was.")
            return 1

        if not write:
            print("  gate passed, " + str(len(copied)) + " files. Nothing written (--check).")
            return 0

        out = DIST / name
        if out.exists():
            shutil.rmtree(out)
        shutil.copytree(staged, out)

        zip_path = DIST / (name + ".zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for rel in copied:
                z.write(out / rel, name + "/" + rel)
        print("  gate passed. " + str(len(copied)) + " files, " + name + ".zip "
              + format(zip_path.stat().st_size, ",") + " bytes")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    write = "--check" not in sys.argv[1:]

    if args:
        folders = []
        for a in args:
            p = HERE / a
            if not (p / "SKILL.md").is_file():
                print(a + ": no SKILL.md, so there is nothing to package", file=sys.stderr)
                return 2
            folders.append(p)
    else:
        folders = sorted(p for p in HERE.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())

    if not folders:
        print("No tool folder holds a SKILL.md.", file=sys.stderr)
        return 2

    DIST.mkdir(exist_ok=True)
    bad = 0
    for f in folders:
        bad += package(f, write)
    print()
    verb = "packaged" if write else "would package"
    print(str(len(folders) - bad) + " of " + str(len(folders)) + " " + verb)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
