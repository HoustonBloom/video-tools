"""
Turn a tightening removal list into a plan the renderer reads.

`find_tightening.py` says what to take out. This says what is left, which is what
a renderer needs. The keeps are the complement of the removals across the source
duration, and every boundary is one the removal list already placed inside
measured silence.

    python make_plan.py v3.max.json --out plans/take3-tightened.json
    python make_plan.py v3.max.json --out plans/take3.json --span 84.14 110.81

`--span` restricts the plan to one stretch of the source, so a composed cut and
a whole-take tighten come out of the same command. A span with no removals inside
it yields a single segment, which is the correct answer and not a failure: it
means that stretch needs no cuts.

The plan carries `kind: "tighten"`. `build_short.py` enforces a hook, build and
payoff contract that a tightened whole take cannot satisfy and should not have to:
it is one continuous piece of speech with the air taken out, not an argument
assembled from spans. Renderers should read `kind` before applying that contract.

Nothing is rendered here. This writes JSON.
"""

import argparse
import json
import os


def keeps(removals, start, end, min_seg):
    """The complement of the removals across [start, end]."""
    out, cur = [], start
    for r in sorted(removals, key=lambda x: x["in"]):
        a, b = float(r["in"]), float(r["out"])
        if b <= start or a >= end:
            continue
        a, b = max(a, start), min(b, end)
        if a > cur:
            out.append((cur, a))
        cur = max(cur, b)
    if cur < end:
        out.append((cur, end))
    return [s for s in out if s[1] - s[0] >= min_seg]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("removals", help="JSON written by find_tightening.py --json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--span", nargs=2, type=float, metavar=("IN", "OUT"),
                    help="restrict to this stretch of the source")
    ap.add_argument("--min-seg", type=float, default=0.12,
                    help="drop keeps shorter than this; they are splice artefacts")
    ap.add_argument("--source", help="override the source path recorded in the plan")
    ap.add_argument("--why", default="tightening pass: dead air, pauses, filler")
    a = ap.parse_args()

    d = json.load(open(a.removals, encoding="utf-8"))
    src = a.source or d["source"]
    dur = float(d["duration"])
    start, end = (a.span if a.span else (0.0, dur))
    if not (0 <= start < end <= dur + 0.01):
        raise SystemExit(f"--span must sit inside 0 to {dur:.2f}")

    segs = keeps(d.get("removals", []), start, end, a.min_seg)
    if not segs:
        raise SystemExit("no segments left; the removals cover the whole span")

    kept = sum(b - a_ for a_, b in segs)
    plan = {
        "kind": "tighten",
        "source": src,
        "output": os.path.splitext(a.out)[0] + ".mp4",
        "span": [round(start, 3), round(end, 3)],
        "span_duration": round(end - start, 3),
        "result_duration": round(kept, 3),
        "removed": round((end - start) - kept, 3),
        "splices": max(0, len(segs) - 1),
        "settings": d.get("settings", {}),
        "segments": [{"in": round(s, 3), "out": round(e, 3),
                      "mode": "camera", "why": a.why} for s, e in segs],
    }
    json.dump(plan, open(a.out, "w", encoding="utf-8"), indent=1)

    print(f"{os.path.basename(a.out)}")
    print(f"  source   {os.path.basename(src)}")
    print(f"  span     {start:.2f} to {end:.2f}   {end - start:.2f}s")
    print(f"  result   {kept:.2f}s in {len(segs)} segment(s), "
          f"{plan['removed']:.2f}s removed, {plan['splices']} splice(s)")
    if plan["splices"] == 0:
        print("  no splices: this span plays as recorded")


if __name__ == "__main__":
    main()
