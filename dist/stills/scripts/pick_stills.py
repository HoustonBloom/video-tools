#!/usr/bin/env python
"""
Choose WHEN. Give it any video, get back a shortlist of frames worth looking at.

Nothing here knows about a programme, an episode or a person. It samples the
video, measures each sample, keeps the ones that measure well, spaces them out,
and re-extracts those at full resolution from the source.

What gets measured, per sampled frame:

  sharpness    variance of the Laplacian on the greyscale frame. Blur and motion
               smear both drive this down. The main signal.
  motion       mean absolute difference against the previous sample. A settled
               moment beats one caught mid-gesture.
  subject_frac fraction of pixels inside a broad skin-tone range in YCrCb. A
               model-free stand-in for "a person takes up a useful amount of
               this frame". It cannot tell a face from a forearm, and it
               over-includes wood and warm walls. It is a floor, not a ranking.
  contrast     standard deviation of luma. Cuts to black and dissolves read low.
  exposure     mean luma, plus the fraction of pixels clipped at either end.

**This shortlists. It does not judge.** Nothing here sees a blink, a half-formed
word, or a back of a head. The output is a pile to look through. Look at every
frame before any of it goes out: on the first real run, 22 of 180 shortlisted
frames were rejected by eye and not one of them by a measurement.

No face detection, for the reason in `requirements.txt`: OpenCV 5.0 dropped
CascadeClassifier and ships no cascade files. So face size and eyes-open are
not measured and are not claimed.

Usage:
    python pick_stills.py --video IN.mp4 --out DIR --label "Name" --count 20
    python pick_stills.py --video IN.mp4 --out DIR --label "Slot" --from 238 --to 1102
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

# Anything longer than this is sampled by seeking rather than decoding through.
SEEK_OVER_S = 300
# Analysis frames are measured at this width. Full res buys nothing and costs time.
WORK_W = 640
# Below this the frame is a dissolve, a cut to black or a flat card.
FLAT_CONTRAST = 25


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error",
         "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate,codec_name,bit_rate",
         "-show_entries", "format=duration,size",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    s, f = d["streams"][0], d["format"]
    num, den = (s.get("r_frame_rate") or "0/1").split("/")
    return {
        "width": int(s["width"]),
        "height": int(s["height"]),
        "codec": s.get("codec_name"),
        "fps": round(float(num) / float(den), 3) if float(den) else None,
        "duration_s": round(float(f["duration"]), 3),
        # the video stream, not the container, so sources compare like with like
        "video_bitrate_bps": int(s["bit_rate"]) if s.get("bit_rate") else None,
        "size_bytes": int(f["size"]),
    }


def sample_decode(path, every, workdir):
    """One analysis frame every `every` seconds, decoding straight through.

    Right for short clips. On a feature-length master it decodes every frame to
    throw nearly all of them away, so sample_seek is used there instead.
    """
    pat = str(Path(workdir) / "s_%06d.jpg")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path),
         "-vf", "fps=1/%s,scale=%d:-2" % (every, WORK_W), "-q:v", "3", pat],
        check=True)
    frames = sorted(Path(workdir).glob("s_*.jpg"))
    # fps=1/every emits one frame per bucket; the midpoint is the safe seek target
    return [(round((i + 0.5) * every, 3), p) for i, p in enumerate(frames)]


def sample_seek(path, every, workdir, start, end):
    """Same shape, one input seek per sample instead of a full decode.

    Measured on a 15.5 GB, 1:37:22 master: about 0.4 s per sample, and flat with
    depth into the file, because an input seek lands on a keyframe rather than
    reading forward to it. That is what makes a feature-length source workable.
    """
    times, t = [], float(start)
    while t < end:
        times.append(round(t, 3))
        t += every
    got = []
    for i, tt in enumerate(times):
        dest = Path(workdir) / ("s_%06d.jpg" % i)
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % tt, "-i", str(path),
             "-frames:v", "1", "-vf", "scale=%d:-2" % WORK_W, "-q:v", "3", str(dest)],
            capture_output=True)
        if r.returncode == 0 and dest.exists() and dest.stat().st_size:
            got.append((tt, dest))
    return got


def subject_fraction(bgr):
    """Fraction of pixels inside a broad skin-tone range in YCrCb.

    Broad on purpose: it has to hold across every skin tone in a room, so it
    over-includes wood, warm walls and some clothing. Use it as a floor for "is
    anybody in this shot", never as a ranking and never as a face.
    """
    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    mask = cv2.inRange(ycrcb, np.array([40, 133, 77], np.uint8),
                       np.array([255, 180, 130], np.uint8))
    return float(mask.mean() / 255.0)


def measure(jpg, prev_small):
    img = cv2.imread(str(jpg))
    if img is None:
        return None, prev_small
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (160, 90))

    motion = None
    if prev_small is not None:
        motion = float(np.abs(small.astype(np.int16) - prev_small.astype(np.int16)).mean())

    return {
        "sharpness": round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 2),
        "motion": round(motion, 3) if motion is not None else None,
        "subject_frac": round(subject_fraction(img), 4),
        "contrast": round(float(gray.std()), 2),
        "luma_mean": round(float(gray.mean()), 2),
        "clipped_frac": round(float(((gray < 4) | (gray > 251)).mean()), 4),
        "_thumb": small,
    }, small


def looks_like_a_graphic(m, sharp_ref, motion_ref):
    """A slide, screen share or title card rather than a picture of a room.

    A general test, deliberately not the one in `shorts/scripts/analyze_source.py`.
    That one keys on a purple lower-third bar, which is one programme's branding
    and would be wrong here.

    This keys on the two things true of any inserted graphic: rendered text and
    flat fills are far crisper than a camera image of a room, and the frame does
    not change between samples. Measured on one 1:37:22 episode: inserted slides
    scored 670 to 1070 on sharpness where camera frames scored 65 to 290, so the
    gap is wide, and this errs toward keeping.

    A heuristic, not a detector. The eye pass still has to happen.
    """
    if m["motion"] is None or not sharp_ref or not motion_ref:
        return False
    return m["sharpness"] > sharp_ref * 2.2 and m["motion"] < motion_ref * 0.5


def score(m, sharp_ref, motion_ref, subject_ref):
    s = 0.0
    if sharp_ref:
        s += 2.5 * min(m["sharpness"] / sharp_ref, 2.0)
    if subject_ref:
        s += 1.0 * min(m["subject_frac"] / subject_ref, 1.6)
    if m["motion"] is not None and motion_ref:
        # settled beats mid-gesture, but a frozen frame earns no bonus either
        s += 0.8 * max(0.0, 1.0 - m["motion"] / (motion_ref * 2.0))
    if m["contrast"] < FLAT_CONTRAST:
        s -= 1.5
    if m["clipped_frac"] > 0.06:
        s -= 1.0
    if not 45 <= m["luma_mean"] <= 205:
        s -= 0.8
    return round(s, 3)


def timecode(t):
    """Minutes and seconds, dash separated, because a colon cannot go in a
    filename on Windows. `build_sheet.py` renders it back with a colon."""
    return "%02d-%06.3f" % (int(t // 60), t % 60)


def main():
    ap = argparse.ArgumentParser(description="Choose frames worth looking at.")
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", required=True, help="basename for the stills")
    ap.add_argument("--count", type=int, default=20)
    ap.add_argument("--every", type=float, default=3.0,
                    help="analysis sampling interval, seconds")
    ap.add_argument("--min-gap", type=float, default=25.0,
                    help="minimum seconds between two picks, so the set is not "
                         "six copies of one moment")
    ap.add_argument("--min-subject-frac", type=float, default=0.02)
    ap.add_argument("--from", dest="t_from", type=float, default=None,
                    help="only consider this span, seconds into the source")
    ap.add_argument("--to", dest="t_to", type=float, default=None)
    ap.add_argument("--keep-graphics", action="store_true",
                    help="keep inserted slides and screen shares, which are "
                         "dropped by default")
    ap.add_argument("--sample-mode", choices=["auto", "seek", "decode"], default="auto",
                    help="auto seeks on anything over five minutes")
    args = ap.parse_args()

    # resolved, so a manifest read from any working directory still
    # finds the video it came from
    src = Path(args.video).resolve()
    info = probe(src)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    lo = args.t_from if args.t_from is not None else 0.0
    hi = args.t_to if args.t_to is not None else info["duration_s"]

    mode = args.sample_mode
    if mode == "auto":
        mode = "seek" if info["duration_s"] > SEEK_OVER_S else "decode"

    work = tempfile.mkdtemp(prefix="pick_stills_")
    try:
        cands = (sample_seek(src, args.every, work, lo, hi) if mode == "seek"
                 else sample_decode(src, args.every, work))

        rows, prev = [], None
        for t, p in cands:
            m, prev = measure(p, prev)
            if m is None or not (lo <= t <= hi):
                continue
            m["t"] = t
            rows.append(m)

        if not rows:
            sys.exit("no analysable frames in %s" % src.name)

        sharp_ref = float(np.median([r["sharpness"] for r in rows])) or 1.0
        mv = [r["motion"] for r in rows if r["motion"] is not None]
        motion_ref = float(np.median(mv)) if mv else 0.0

        graphics = [r for r in rows if looks_like_a_graphic(r, sharp_ref, motion_ref)]
        pool = rows if args.keep_graphics else [r for r in rows if r not in graphics]

        over_floor = [r for r in pool if r["subject_frac"] >= args.min_subject_frac]
        if len(over_floor) >= args.count:
            pool = over_floor
        if not pool:
            sys.exit("every frame was filtered out of %s" % src.name)

        sharp_ref = float(np.median([r["sharpness"] for r in pool])) or 1.0
        subject_ref = float(np.median([r["subject_frac"] for r in pool])) or 1.0
        for r in pool:
            r["score"] = score(r, sharp_ref, motion_ref, subject_ref)

        # drop the softest third outright, then rank, then space the picks out
        floor = float(np.percentile([r["sharpness"] for r in pool], 35))
        ranked = sorted([r for r in pool if r["sharpness"] >= floor],
                        key=lambda r: -r["score"]) or sorted(pool, key=lambda r: -r["score"])

        picks = []
        for r in ranked:
            if len(picks) >= args.count:
                break
            if any(abs(r["t"] - q["t"]) < args.min_gap for q in picks):
                continue
            if any(np.abs(r["_thumb"].astype(np.int16)
                          - q["_thumb"].astype(np.int16)).mean() < 3.0 for q in picks):
                continue                       # near enough to one already taken
            picks.append(r)
        picks.sort(key=lambda r: r["t"])

        manifest = []
        for i, r in enumerate(picks, 1):
            name = "%s - %02d.jpg" % (args.label, i)
            dest = out / name
            subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % r["t"],
                 "-i", str(src), "-frames:v", "1", "-q:v", "2", str(dest)],
                check=True)
            full = cv2.imread(str(dest))
            fullsharp = None
            if full is not None:
                fullsharp = round(float(cv2.Laplacian(
                    cv2.cvtColor(full, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()), 2)
            manifest.append({
                "file": name,
                "source": src.name,
                "source_path": str(src),
                "source_video_bitrate_bps": info["video_bitrate_bps"],
                "at_seconds": r["t"],
                "at_timecode": timecode(r["t"]),
                "width": info["width"],
                "height": info["height"],
                "bytes": dest.stat().st_size,
                "sharpness_fullres": fullsharp,
                "sharpness_sample": r["sharpness"],
                "subject_frac": r["subject_frac"],
                "contrast": r["contrast"],
                "motion": r["motion"],
                "score": r["score"],
            })

        (out / ("%s.stills.json" % args.label)).write_text(
            json.dumps({
                "tool": "video-tools/stills/scripts/pick_stills.py",
                "source": dict(info, path=str(src)),
                "span_considered_s": [round(lo, 3), round(hi, 3)],
                "sampled_every_s": args.every,
                "sample_mode": mode,
                "frames_analysed": len(rows),
                "graphics_dropped": 0 if args.keep_graphics else len(graphics),
                # Where the graphics were, in source seconds, whether or not
                # they were kept. A count says a stretch had 23 graphic frames
                # in 333; it cannot say they were one 48 second screen share
                # at 26:51. A reader that wants the run needs the times.
                "graphics_at_s": [round(r["t"], 3) for r in graphics],
                # And every sampled frame's numbers, one row each, so a reader
                # can ask a question this script did not. The first one asked
                # was "where is the live demo": its frames are crisp and move,
                # so the graphics test keeps them as camera, and nobody is in
                # them, which subject_frac says and the graphics test does not.
                "subject_floor": args.min_subject_frac,
                "samples_fields": ["t", "sharpness", "motion", "subject_frac"],
                "samples": [[round(r["t"], 3), r["sharpness"], r["motion"], r["subject_frac"]] for r in rows],
                "shortlisted": len(manifest),
                "not_measured": "No face detection. OpenCV 5 dropped CascadeClassifier "
                                "and no face model is on this machine, so face size, "
                                "who is in shot and whether the eyes are open are not "
                                "measured. Look at every frame before it goes out.",
                "picks": manifest,
            }, indent=2), encoding="utf-8")
        print("  %s: %d stills from %d analysed frames%s"
              % (args.label, len(manifest), len(rows),
                 "" if args.keep_graphics else ", %d graphics dropped" % len(graphics)))
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
