#!/usr/bin/env python
"""
Choose WHERE. Reframe chosen stills to a feed shape, one crop per subject.

Takes the `.stills.json` that `pick_stills.py` wrote and cuts each full frame to
an aspect. On a locked-off camera the people are the only things that move, so
the subjects are found by accumulating frame difference across the span.

**Subject location is not written here.** It is `shorts/scripts/analyze_source.py`,
which already does it, was measured when it was built, and is used by the Shorts
system. This imports `motion_map` and `column_regions` from it rather than
keeping a second copy that can drift. The one thing not imported is
`classify_mode`, which keys on a purple lower-third bar belonging to one
programme.

## The reason this returns bands rather than a point

An earlier version took the single hottest column and cropped around it. On a
six-person couch it picked whoever fidgeted most across the span, which was not
the person speaking, and would have produced a folder named for one founder
holding ten pictures of somebody else.

`column_regions` returns every band that clears the floor, so a two-shot yields
two crops and a couch yields as many as it has movers. Nothing is named. A crop
is `a`, `b`, `c` left to right, and which one holds who is for a person to see.

Height is never scaled up, and by default never cropped either: losing headroom
looks worse than losing width. `--height-frac` trades height for a tighter frame
where a shot has dead space above the heads, and the manifest records what it
cost.

Usage:
    python crop_stills.py --manifest DIR/Name.stills.json --out CROPDIR
    python crop_stills.py --manifest DIR/Name.stills.json --out CROPDIR \
        --aspect 9:16 --height-frac 0.85
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shorts" / "scripts"))
from analyze_source import motion_map, column_regions  # noqa: E402

# Frames pulled across the span to build the motion map.
SPAN_SAMPLES = 16
WORK_W = 640


def span_frames(video, lo, hi, n=SPAN_SAMPLES):
    """n frames spread across [lo, hi], by seeking, so a long master stays cheap."""
    step = (hi - lo) / max(n - 1, 1) if hi > lo else 0
    frames = []
    with tempfile.TemporaryDirectory(prefix="crop_stills_") as tmp:
        for i in range(n):
            t = lo + i * step
            p = Path(tmp) / ("f_%02d.jpg" % i)
            r = subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % t, "-i", str(video),
                 "-frames:v", "1", "-vf", "scale=%d:-2" % WORK_W, "-q:v", "3", str(p)],
                capture_output=True)
            if r.returncode == 0 and p.exists() and p.stat().st_size:
                img = cv2.imread(str(p))
                if img is not None:
                    frames.append(img)
    return frames


def subjects(video, lo, hi, W, H):
    """Bands of moving content across the span, left to right. May be empty.

    Each band carries an energy-weighted centroid rather than its midpoint. A
    person gesturing throws a band wider than their body on the side the arm
    goes, and the midpoint of that band sits off them: measured on a two-shot,
    the midpoint put the speaker hard against the frame edge with a lamp filling
    the middle. The centroid follows the mass of the movement, which is the body.
    """
    frames = span_frames(video, lo, hi)
    if len(frames) < 2:
        return [], "too few frames could be read to measure movement"
    fh, fw = frames[0].shape[:2]
    acc, scale = motion_map(frames, fw, fh)
    regions = column_regions(acc, scale)
    if not regions:
        return [], "no band of movement cleared the floor"

    # column_regions returns coordinates in the space of the frames it was handed,
    # so rescale from analysis width to the real frame width.
    up = W / float(fw)
    prof = acc.mean(axis=0)

    # Vertical too. On a locked-off wide the people sit in a band across the
    # middle, so a crop centred on frame height gives away the top to empty wall
    # and the bottom to a coffee table. The rows that move are the rows worth
    # keeping.
    rows = acc.mean(axis=1)
    rows = rows - rows.min()
    y_frac = (float((np.arange(len(rows)) * rows).sum() / rows.sum())
              / len(rows)) if rows.sum() > 0 else 0.5

    for r in regions:
        # band edges back into acc's own column space to weight them
        a = max(0, int(round(r["x0"] * scale)))
        b = min(len(prof), max(a + 1, int(round(r["x1"] * scale))))
        w = prof[a:b]
        if w.sum() > 0:
            centroid = a + float((np.arange(len(w)) * w).sum() / w.sum())
        else:
            centroid = (a + b) / 2.0
        r["centre_x"] = int(round(centroid / scale * up))
        r["x0"] = int(round(r["x0"] * up))
        r["x1"] = int(round(r["x1"] * up))
        r["centre_y_frac"] = y_frac
    return regions, "movement accumulated across the span"


def main():
    ap = argparse.ArgumentParser(description="Reframe stills to a feed shape.")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--src-dir", default=None,
                    help="where the full frames are, if not beside the manifest")
    ap.add_argument("--out", required=True)
    ap.add_argument("--aspect", default="4:5")
    ap.add_argument("--height-frac", type=float, default=1.0,
                    help="fraction of frame height to keep. Below 1 frames tighter "
                         "and costs resolution, which the manifest records.")
    ap.add_argument("--max-crops", type=int, default=3,
                    help="most crops per frame, taking the strongest bands first")
    ap.add_argument("--max-overlap", type=float, default=0.45,
                    help="two crops overlapping more than this fraction of their "
                         "width are the same picture, so the weaker one is dropped")
    ap.add_argument("--centre-only", action="store_true",
                    help="skip subject location and cut one centred crop")
    args = ap.parse_args()

    man = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    src_dir = Path(args.src_dir) if args.src_dir else Path(args.manifest).parent
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    video = Path(man["source"]["path"])
    aw, ah = (int(x) for x in args.aspect.split(":"))
    W, H = man["source"]["width"], man["source"]["height"]

    regions, how = [], "frame centre, by request"
    if not args.centre_only:
        lo, hi = man.get("span_considered_s", [None, None])
        if lo is None:
            ts = [p["at_seconds"] for p in man["picks"]]
            lo, hi = min(ts), max(ts)
        if not video.exists():
            regions, how = [], "frame centre, the source video is not at the path the manifest records"
        else:
            regions, how = subjects(video, lo, hi, W, H)

    ch = max(1, int(round(H * min(max(args.height_frac, 0.1), 1.0))))
    cw = int(round(ch * aw / ah))
    if cw >= W and ch >= H:
        sys.exit("a %s crop of %dx%d is not smaller than the frame; nothing to do"
                 % (args.aspect, W, H))
    cw = min(cw, W)

    # Bands are segmented on the motion profile, which splits one person in two
    # as readily as it separates two people. What matters is whether the crops
    # they produce are different pictures, so suppress on the windows instead.
    # Measured before this went in: a couch gave three bands whose crops
    # overlapped 83 percent, and a two-shot gave three overlapping 54 percent.
    kept = []
    for r in sorted(regions, key=lambda r: -r["energy"]):
        x0 = max(0, min(W - cw, r["centre_x"] - cw // 2))
        if any(max(0, min(x0 + cw, k[0] + cw) - max(x0, k[0])) / float(cw) > args.max_overlap
               for k in kept):
            continue
        kept.append((x0, r))
        if len(kept) >= args.max_crops:
            break
    kept.sort(key=lambda k: k[0])
    regions = [dict(r, _x0=x0) for x0, r in kept]

    rows = []
    for pick in man["picks"]:
        img = cv2.imread(str(src_dir / pick["file"]))
        if img is None:
            continue
        yf = regions[0]["centre_y_frac"] if regions else 0.5
        y0 = max(0, min(H - ch, int(round(yf * H)) - ch // 2))

        if regions:
            boxes = [(chr(ord("a") + i) if len(regions) > 1 else "",
                      r["_x0"], r["energy"]) for i, r in enumerate(regions)]
        else:
            boxes = [("", max(0, W // 2 - cw // 2), None)]

        for tag, x0, energy in boxes:
            suffix = (" %s" % tag) if tag else ""
            name = "%s%s (%d-%d).jpg" % (Path(pick["file"]).stem, suffix, aw, ah)
            cv2.imwrite(str(out / name), img[y0:y0 + ch, x0:x0 + cw],
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
            rows.append({
                "file": name,
                "from_full_frame": pick["file"],
                "source": pick["source"],
                "at_timecode": pick["at_timecode"],
                "crop_px": [cw, ch],
                "crop_origin_xy": [x0, y0],
                "subject": tag or None,
                "centred_on": how,
                "motion_energy": energy,
                "upscaled": False,
            })

    stem = Path(args.manifest).stem.replace(".stills", "")
    (out / (stem + ".crops.json")).write_text(
        json.dumps({
            "tool": "video-tools/stills/scripts/crop_stills.py",
            "aspect": args.aspect,
            "source": man["source"]["path"],
            "height_frac": args.height_frac,
            "never_upscaled": True,
            "subjects_found": len(regions),
            "subject_location": how,
            "subjects_are_not_named": "A crop is a, b, c left to right. Which one "
                                      "holds who is for a person to see. Nothing "
                                      "here identifies anybody.",
            "crops": rows,
        }, indent=2), encoding="utf-8")
    print("  %s: %d crops from %d frames, %d subject%s found"
          % (out.name, len(rows), len(man["picks"]), len(regions),
             "" if len(regions) == 1 else "s"))


if __name__ == "__main__":
    main()
