#!/usr/bin/env python3
"""The whole workflow, ending in the HTML page. That page is the objective.

    python run.py --captions CAPTIONS.vtt
    python run.py --captions C.vtt --video IN.mp4 --out-dir run/ --title "..."

Four steps, each writing a file the next one reads, each runnable on its own:

    find_moments.py       captions            -> moments.json
    (the read)            captions, by an AI  -> segments.json     (this script cannot do it)
    pick_turn_stills.py   video + spans       -> turn-stills.json, segment-stills.json
    build_readthrough.mjs moments + segments  -> readthrough.html

THE READ IS A STEP, AND A SCRIPT CANNOT TAKE IT. find_moments.py matches phrases
it was given. A host who says "Today, our guest speaker is [name]" or "this
gentleman over here [name] is going to talk about [product]" in words the list
does not carry produces no boundary, and the page goes out with the guest and
the featured founders missing. So segments.json is written by the AI running
this workflow, reading the whole transcript against the checklist in SKILL.md. When it is missing this script
prints the prompt for that read, builds the page anyway from the mechanical
pass, and the page says at the top that the recording has not been read.

IT FAILS UNLESS THE PAGE EXISTS. A run that writes moments.json and stops has
produced nothing anybody asked for. The last thing this script does is check the
page is on disk and has the parts a page needs, and exit non-zero if it does not.

IT EDITS NOTHING IT CALLS. pick_turn_stills.py hands work to
../../stills/scripts/pick_stills.py by subprocess. The stills tool is not
imported, not patched and not configured from here, so it goes on working
exactly the same when run on its own.
"""

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# The same words the page shows when segments.json is missing. Kept here as
# well so a terminal run with no browser open still hands the reader the step.
READ_PROMPT = ("Read the whole transcript of this recording end to end, then write segments.json "
               "beside it in the readthrough-segments/v1 shape (see video-tools/readthrough/SKILL.md). "
               "For every segment give in, out, who, what, and the lines worth quoting with their times. "
               "Look for, and say when you find none of: the opening and who is introduced; a guest "
               "speaker; each featured founder and their company; a demo (who, in, out); the sponsor; "
               "the round of introductions with every name; questions from the room; the closing. "
               "Names are as heard unless known. Then rebuild: node scripts/build_readthrough.mjs .")


def step(name, cmd):
    print("\n== " + name, flush=True)
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print("FAILED at: " + name, file=sys.stderr)
        sys.exit(r.returncode)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--captions", required=True)
    ap.add_argument("--style-from", default=None,
                    help="no longer used; the page carries its own vendored template")
    ap.add_argument("--video", help="optional. Without it the page has no stills.")
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--out", default="readthrough.html")
    ap.add_argument("--title", default=None, help="what to call the recording on the page")
    ap.add_argument("--every", type=float, default=20.0, help="stills sampling interval")
    a = ap.parse_args()

    out = Path(a.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    captions = Path(a.captions).resolve()

    if not captions.is_file():
        print("No captions at " + str(captions), file=sys.stderr)
        return 1

    step("find moments", [sys.executable, str(HERE / "find_moments.py"), str(captions),
                          "--out", str(out / "moments.json")])

    segments = out / "segments.json"
    if segments.is_file():
        print("\n== the read\n  segments.json is here, written " + str(
            __import__("json").loads(segments.read_text(encoding="utf-8")).get("read", {}).get("on", "(no date)")))
    else:
        print("\n== the read\n  NOT DONE. No segments.json in " + str(out) + ".")
        print("  The page will build from the mechanical pass and say so at the top.")
        print("  To read the recording, paste this to your AI in that folder:\n")
        print("  " + READ_PROMPT + "\n")

    if a.video:
        step("pick stills", [sys.executable, str(HERE / "pick_turn_stills.py"),
                             "--video", str(Path(a.video).resolve()),
                             "--speakers", str(out / "moments.json"),
                             "--out", str(out / "turn-stills")])
        if segments.is_file():
            step("pick segment stills", [sys.executable, str(HERE / "pick_turn_stills.py"),
                                         "--video", str(Path(a.video).resolve()),
                                         "--speakers", str(segments),
                                         "--out", str(out / "segment-stills"),
                                         "--every", "10", "--head", "20"])
    else:
        print("\n== stills\n  skipped, no --video. The page will have no pictures.")

    step("build page", ["node", str(HERE / "build_readthrough.mjs"), str(out), "--out", a.out]
         + (["--title", a.title] if a.title else []))

    # The objective check. Everything above writes JSON; only this is the thing.
    page = out / a.out
    if not page.is_file():
        print("\nNo page at " + str(page) + ". The workflow has not finished.", file=sys.stderr)
        return 1
    html = page.read_text(encoding="utf-8", errors="replace")
    missing = [what for what, probe in [
        ("a title", "<title>"),
        ("stat cards", 'class="stats"'),
        ("the filters", 'class="filters"'),
        ("the timeline", 'class="tl-track"'),
        ("at least one ranked card", 'class="lens'),
    ] if probe not in html]
    if missing or len(html) < 4000:
        print("\nThe page at " + str(page) + " is not a finished page.", file=sys.stderr)
        for m in missing:
            print("  missing " + m, file=sys.stderr)
        if len(html) < 4000:
            print("  only %d bytes" % len(html), file=sys.stderr)
        return 1

    print("\n== done")
    print("  " + str(page) + "  " + format(page.stat().st_size, ",") + " bytes")
    print("  open it by double-clicking. It needs no server.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
