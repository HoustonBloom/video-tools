#!/usr/bin/env python3
"""Check a change to the moment patterns in seconds, on both formats.

    python run_tests.py            # check
    python run_tests.py --accept   # rewrite expected.json from what runs now

WHY THIS EXISTS. Checking a change to a regex meant re-processing a 2h56m video
and a 1h12m one, twenty minutes of stills included, and overwriting the outputs
of both. That is the wrong instrument for a one-line change, and it means the
person who changes a pattern finds out what they broke long after they have
moved on.

THE FIXTURES ARE REAL. Each one is a verbatim slice of a recording, not written
by hand, so a pattern that passes here is a pattern that works on the tape. Two
formats are covered on purpose: a lineup where a host calls people up by name,
and a conversation where nobody is announced.

WHAT IT DOES NOT COVER. The stills step and the page build. This checks what the
reading pass finds, which is where the patterns live and where the regressions
have been.
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
EXPECTED = HERE / "expected.json"
FIND = HERE.parent / "scripts" / "find_moments.py"


def run_one(vtt, tmp):
    out = tmp / (vtt.stem + ".json")
    r = subprocess.run([sys.executable, str(FIND), str(vtt), "--out", str(out)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None, (r.stderr or r.stdout).strip()[:400]
    d = json.loads(out.read_text(encoding="utf-8"))
    return {
        "counts": d["counts"],
        "stretches": len(d["stretches"]),
        "names": sorted(m["name_read"] for m in d["moments"] if m["name_read"]),
        "matched": [m["kind"] + ": " + m["matched"] for m in d["moments"]],
    }, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--accept", action="store_true",
                    help="rewrite expected.json. Read the diff before you do.")
    a = ap.parse_args()

    fixtures = sorted(FIXTURES.glob("*.vtt"))
    if not fixtures:
        print("No fixtures in " + str(FIXTURES), file=sys.stderr)
        return 2

    expected = json.loads(EXPECTED.read_text(encoding="utf-8")) if EXPECTED.is_file() else {}
    got, failed = {}, 0

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for f in fixtures:
            result, err = run_one(f, tmp)
            if err:
                print("CRASH  " + f.name)
                print("       " + err)
                failed += 1
                continue
            got[f.name] = result
            want = expected.get(f.name)
            if want is None:
                print("NEW    " + f.name + "  (no expectation recorded)")
                failed += 1
                continue
            diffs = [k for k in ("counts", "stretches", "names", "matched") if want.get(k) != result[k]]
            if diffs:
                failed += 1
                print("FAIL   " + f.name)
                for k in diffs:
                    print("       " + k)
                    print("         want " + json.dumps(want.get(k), ensure_ascii=False))
                    print("         got  " + json.dumps(result[k], ensure_ascii=False))
            else:
                print("ok     %-26s %d stretches, %d moments" %
                      (f.name, result["stretches"], len(result["matched"])))

    if a.accept:
        EXPECTED.write_text(json.dumps(got, indent=1, ensure_ascii=False), encoding="utf-8")
        print("\nwrote " + str(EXPECTED))
        return 0

    print()
    if failed:
        print("%d of %d fixtures differ. Either the change is wrong, or the "
              "expectation is out of date and --accept records the new one."
              % (failed, len(fixtures)))
        return 1
    print("%d fixtures, all matching." % len(fixtures))
    return 0


if __name__ == "__main__":
    sys.exit(main())
