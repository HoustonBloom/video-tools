"""
Check a rendered cut against its plan, and against the ways a render lies.

    python verify_cut.py PLAN.json
    python verify_cut.py --file cut.mp4 --expect 34.76

Every check here exists because something passed without it.

**Audio duration against video duration** is the important one. A cut shipped
with 1.5 seconds of audio under 18.5 seconds of picture, and it passed every
check that ran, because those checks asked whether an audio stream existed and
what its loudness was. Both questions have answers on a truncated stream. The
cause was a double trim, `atrim` in the filter chain and `-ss` on the output,
each taking the keyframe lead off the front.

**Loudness measured on the output**, never the value the renderer intended.
Two separate bugs shipped where the tool printed the target it asked for rather
than the number it got: once when single pass loudnorm did not converge across
short segments, once when the true peak ceiling capped the gain and loudnorm
reported success anyway.

Exit code is 1 if anything fails, so this can gate a hand-off.
"""

import argparse
import json
import os
import re
import subprocess
import sys

TARGET_I = -14.0
TOL_I = 0.4          # LUFS
TOL_DUR = 0.15       # seconds
TOL_AV = 0.30        # seconds between audio and video length
TP_CEILING = -1.0    # dBTP, above this a lossy re-encode will clip


def probe(path, stream, fields):
    """Key=value, because ffprobe returns fields in its own order, not yours."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", stream,
         "-show_entries", "stream=" + ",".join(fields),
         "-of", "default=noprint_wrappers=1", path],
        capture_output=True, text=True).stdout
    d = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def loudness(path):
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path,
         "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    i = re.findall(r"I:\s*(-?\d+\.?\d*)\s*LUFS", out)
    p = re.findall(r"Peak:\s*(-?\d+\.?\d*)\s*dBFS", out)
    return (float(i[-1]) if i else None), (float(p[-1]) if p else None)


def check_one(path, expect):
    rows, ok = [], True

    def add(name, passed, detail):
        nonlocal ok
        rows.append((passed, name, detail))
        if not passed:
            ok = False

    if not os.path.exists(path):
        return False, [(False, "file exists", path)]

    v = probe(path, "v:0", ["width", "height", "duration", "avg_frame_rate"])
    a = probe(path, "a:0", ["codec_name", "duration", "channels", "sample_rate"])

    add("video stream", bool(v.get("width")), v.get("width", "none"))
    add("audio stream", bool(a.get("codec_name")), a.get("codec_name", "NONE"))
    if not v.get("width") or not a.get("codec_name"):
        return ok, rows

    # A stream can lack its own duration tag; fall back to the container.
    def dur_of(d):
        if d.get("duration") not in (None, "N/A"):
            return float(d["duration"])
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                              "format=duration", "-of",
                              "default=noprint_wrappers=1:nokey=1", path],
                             capture_output=True, text=True).stdout.strip()
        return float(out) if out else 0.0

    vdur, adur = dur_of(v), dur_of(a)
    add("canvas", True, f"{v['width']}x{v['height']} @ {v.get('avg_frame_rate','?')}")
    add("audio length matches video", abs(adur - vdur) <= TOL_AV,
        f"video {vdur:.2f}s, audio {adur:.2f}s, difference {abs(adur - vdur):.2f}s")

    if expect is not None:
        add("duration matches plan", abs(vdur - expect) <= TOL_DUR,
            f"{vdur:.2f}s against {expect:.2f}s planned")

    i, peak = loudness(path)
    add("loudness", i is not None and abs(i - TARGET_I) <= TOL_I,
        f"{i} LUFS against {TARGET_I}")
    if peak is not None:
        add("peak headroom", peak <= TP_CEILING, f"{peak} dBFS")
    return ok, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan", nargs="?")
    ap.add_argument("--file")
    ap.add_argument("--expect", type=float)
    a = ap.parse_args()

    jobs = []
    if a.file:
        jobs.append((a.file, a.expect))
    elif a.plan:
        plan = json.load(open(a.plan, encoding="utf-8"))
        expect = sum(float(s["out"]) - float(s["in"]) for s in plan["segments"])
        stem, ext = os.path.splitext(plan["output"])
        targets = plan.get("targets", [{"name": ""}])
        for t in targets:
            n = t.get("name") or ""
            jobs.append((f"{stem}_{n}{ext}" if n else plan["output"], expect))
    else:
        sys.exit("give a plan, or --file with --expect")

    failed = 0
    for path, expect in jobs:
        ok, rows = check_one(path, expect)
        print(f"\n{os.path.basename(path)}")
        for passed, name, detail in rows:
            print(f"  {'pass' if passed else 'FAIL'}  {name:28} {detail}")
        if not ok:
            failed += 1
    print(f"\n{len(jobs) - failed} of {len(jobs)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
