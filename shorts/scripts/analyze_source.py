"""
Locate what matters in a locked-off frame, so a 9:16 crop can be aimed at it.

Two things are measured, both from the same signal:

  mode    Is this stretch a slide composite or a camera shot? Decided by the
          purple lower-third bar, which is present in slide mode and absent
          in camera mode.

  regions Where is the moving content? On a locked-off camera the background
          does not move, so accumulated frame difference marks the subjects.
          In slide mode the slide is static and the camera inset is the only
          thing moving, so the same measurement finds the inset rectangle.

No face model is used. OpenCV 5.0 ships no cascades and no ONNX weights, and
fetching them needs a network this workspace does not use. Motion is a better
locator for this footage regardless: it finds a person turned away from camera,
which a frontal face detector does not.

Usage:
    python analyze_source.py VIDEO [--start S] [--end S] [--json OUT]
"""

import argparse
import json
import sys

import cv2
import numpy as np

# Proportion of frame height treated as the lower-third band.
BAR_BAND = 0.93
# Sampling resolution for the motion map. Full res buys nothing here and costs time.
WORK_W = 480
# Frames sampled per second of source.
SAMPLE_FPS = 2.0
# A column counts as subject when its motion energy clears this fraction of the peak.
COLUMN_FLOOR = 0.28


def probe(video):
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        sys.exit(f"cannot open {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    return cap, fps, n, w, h


def sample_frames(cap, fps, start, end, limit=400):
    """Return frames sampled evenly across [start, end], at SAMPLE_FPS."""
    step = max(1, int(round(fps / SAMPLE_FPS)))
    first = int(start * fps)
    last = int(end * fps)
    idxs = list(range(first, last, step))
    if len(idxs) > limit:  # long spans get thinned, not truncated
        idxs = [idxs[round(i * (len(idxs) - 1) / (limit - 1))] for i in range(limit)]
    out = []
    for i in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, frame = cap.read()
        if ok:
            out.append(frame)
    return out


def bar_signature(frames, h):
    """Mean BGR of the lower-third band, and how much it moves over time."""
    band = [f[int(h * BAR_BAND):, :, :] for f in frames]
    per_frame = np.stack([b.reshape(-1, 3).mean(axis=0) for b in band])
    mean = per_frame.mean(axis=0)
    # A graphic overlay is identical frame to frame. A room with people in it
    # is not. Spatial flatness is the wrong test here, because the bar carries
    # white text and text is not flat.
    drift = float(np.mean(per_frame.std(axis=0)))
    return mean, drift


def classify_mode(frames, h):
    """
    Slide mode carries a purple lower-third graphic. Camera mode carries a room.

    Two tests, both required: the band reads purple (blue and red both above
    green), and the band is static over time. A purple cushion on the couch
    fails the second test as soon as anyone moves in front of it.
    """
    mean, drift = bar_signature(frames, h)
    b, g, r = float(mean[0]), float(mean[1]), float(mean[2])
    purple = (b - g > 18) and (r - g > 5) and b > 55
    static = drift < 3.0
    return ("slide" if (purple and static) else "camera",
            {"band_bgr": [round(b, 1), round(g, 1), round(r, 1)],
             "band_drift": round(drift, 2),
             "purple": bool(purple), "static": bool(static)})


def derive_slide_rect(regions, w, h, pad=12):
    """
    The slide panel, derived rather than detected.

    Detecting it directly does not work on this composite. The decorative
    border around the slide is static and full of line art, so every test
    tried (edge density, saturation, non-backdrop masking) returns a box
    spanning the full frame width. Measured on arcs B, D and E1: all three
    returned x0=0, which is the border, not the slide.

    What is reliable is the inset, because it is the only moving thing in
    slide mode. So the slide panel is taken as everything to the right of the
    inset and above the lower-third bar. That errs outward, including some
    decorative margin, which is the safe direction: it never crops slide
    content. Tighten it per source in the composite profile after looking at
    the proof frame.
    """
    if not regions:
        return {"x0": 0, "x1": w, "y0": 0, "y1": int(h * BAR_BAND)}
    inset_right = max(r["x1"] for r in regions)
    return {"x0": min(w - 16, inset_right + pad), "x1": w,
            "y0": 0, "y1": int(h * BAR_BAND)}


def motion_map(frames, w, h):
    """Accumulated absolute difference between consecutive sampled frames."""
    scale = WORK_W / w
    small = [cv2.cvtColor(cv2.resize(f, (WORK_W, int(h * scale))), cv2.COLOR_BGR2GRAY)
             for f in frames]
    acc = np.zeros_like(small[0], dtype=np.float32)
    for a, b in zip(small, small[1:]):
        acc += cv2.absdiff(a, b).astype(np.float32)
    acc = cv2.GaussianBlur(acc, (0, 0), 6)
    if acc.max() > 0:
        acc /= acc.max()
    return acc, scale


def column_regions(acc, scale, min_frac=0.05):
    """
    Collapse the motion map to a column profile and return the bands that
    clear the floor. Each band is one subject on a locked-off camera.
    """
    prof = acc.mean(axis=0)
    prof = prof / prof.max() if prof.max() > 0 else prof
    hot = prof >= COLUMN_FLOOR
    bands, run = [], None
    for x, on in enumerate(hot):
        if on and run is None:
            run = x
        elif not on and run is not None:
            bands.append((run, x))
            run = None
    if run is not None:
        bands.append((run, len(hot)))
    min_w = max(4, int(len(hot) * min_frac))
    bands = [b for b in bands if b[1] - b[0] >= min_w]

    out = []
    for x0, x1 in bands:
        col = acc[:, x0:x1]
        rows = col.mean(axis=1)
        rows = rows / rows.max() if rows.max() > 0 else rows
        ys = np.where(rows >= COLUMN_FLOOR)[0]
        y0, y1 = (int(ys[0]), int(ys[-1])) if len(ys) else (0, acc.shape[0])
        out.append({
            "x0": int(x0 / scale), "x1": int(x1 / scale),
            "y0": int(y0 / scale), "y1": int(y1 / scale),
            "energy": round(float(col.mean()), 4),
        })
    out.sort(key=lambda r: r["x0"])
    return out


def crop_9x16(region, w, h):
    """
    A 9:16 window of full frame height, centred on the region but kept inside
    the frame. Height is never cropped: losing headroom looks worse than
    losing width.
    """
    cw = int(round(h * 9 / 16))
    cx = (region["x0"] + region["x1"]) // 2
    x = max(0, min(w - cw, cx - cw // 2))
    return {"x": x, "y": 0, "w": cw, "h": h, "center_x": cx}


def scan(video, start, end, window):
    """
    Walk the file and report where the composition changes.

    This is the map you frame from: every run of one mode is a stretch that can
    share a framing decision, and every boundary is a place framing has to
    change. Cheaper than it looks, because classifying a window needs only a
    handful of frames from it.
    """
    cap, fps, n, w, h = probe(video)
    dur = end if end is not None else (n / fps if fps else 0.0)
    marks = []
    t = start
    while t < dur:
        t1 = min(t + window, dur)
        step = max(1, int(round(fps / 2)))
        idxs = range(int(t * fps), int(t1 * fps), step)
        frames = []
        for i in list(idxs)[:8]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ok, f = cap.read()
            if ok:
                frames.append(f)
        if len(frames) >= 2:
            marks.append((t, t1, classify_mode(frames, h)[0]))
        t = t1
    cap.release()

    runs = []
    for t0, t1, m in marks:
        if runs and runs[-1]["mode"] == m:
            runs[-1]["out"] = t1
        else:
            runs.append({"in": t0, "out": t1, "mode": m})
    for r in runs:
        r["length"] = round(r["out"] - r["in"], 2)
    return runs


def fmt(t):
    return f"{int(t) // 60}:{t % 60:05.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--scan", action="store_true",
                    help="map where the composition changes across the span")
    ap.add_argument("--window", type=float, default=5.0,
                    help="scan resolution in seconds")
    a = ap.parse_args()

    if a.scan:
        runs = scan(a.video, a.start, a.end, a.window)
        text = json.dumps(runs, indent=2)
        if a.json:
            with open(a.json, "w", encoding="utf-8") as f:
                f.write(text)
        print(f"{len(runs)} runs, resolution {a.window}s\n")
        for r in runs:
            print(f"  {fmt(r['in']):>9s} to {fmt(r['out']):>9s}  "
                  f"{r['mode']:6s} {r['length']:7.2f}s")
        return

    cap, fps, n, w, h = probe(a.video)
    dur = n / fps if fps else 0.0
    end = a.end if a.end is not None else dur
    frames = sample_frames(cap, fps, a.start, end)
    cap.release()
    if len(frames) < 3:
        sys.exit("not enough frames sampled")

    mode, evidence = classify_mode(frames, h)
    acc, scale = motion_map(frames, w, h)
    regions = column_regions(acc, scale)

    slide_rect = derive_slide_rect(regions, w, h) if mode == "slide" else None

    result = {
        "video": a.video,
        "duration": round(dur, 2),
        "span": [a.start, round(end, 2)],
        "size": [w, h],
        "fps": round(fps, 3),
        "frames_sampled": len(frames),
        "mode": mode,
        "mode_evidence": evidence,
        "regions": regions,
        "slide_rect": slide_rect,
        "crops": [crop_9x16(r, w, h) for r in regions],
    }
    text = json.dumps(result, indent=2)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            f.write(text)
    print(text)


if __name__ == "__main__":
    main()
