"""
Render a vertical Short from a plan, or render one proof frame from it.

The plan is a JSON file. It is the thing a human approves, and it is the only
place framing decisions live, so a Short can always be rebuilt from it.

    {
      "source": "...E1_Edited.mp4",
      "output": "...short.mp4",
      "profile": {                       # composite geometry, per source
        "inset": [0, 447, 432, 690],     # x0 y0 x1 y1 of the camera inset
        "slide": [444, 0, 1920, 1004],   # x0 y0 x1 y1 of the slide panel
        "bg":    "0x000000"              # canvas colour
      },
      "segments": [
        {"in": 1337.29, "out": 1342.53, "mode": "camera", "crop_x": 1306},
        {"in": 1420.00, "out": 1432.00, "mode": "slide",  "layout": "stacked"}
      ],
      "captions": "burned.ass"           # optional
    }

Modes and layouts, and why each exists, are in ../references/framing.md.

Usage:
    python build_short.py PLAN.json
    python build_short.py PLAN.json --proof 0 --at 2.0 --out frame.png
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

W, H = 1080, 1920          # Shorts canvas
FPS = 30

# Audio targets. Same chain the LinkedIn and YouTube cuts were measured against,
# and where YouTube normalises to.
AUDIO_CHAIN = ("highpass=f=75,afftdn=nr=6:nf=-45:tn=1,"
               "acompressor=threshold=-24dB:ratio=2.5:attack=20:release=250,"
               "loudnorm=I=-14:TP=-1.5:LRA=11")

# The Shorts player puts title, channel and description over the bottom of the
# frame and the action rail up the right side. Nothing that has to be read goes
# below SAFE_BOTTOM. Panels are centred in the band above it, so the layout
# adapts to whatever the source geometry turns out to be instead of assuming it.
SAFE_TOP = 120
SAFE_BOTTOM = 1660
PANEL_GAP = 44


def stack_positions(*panel_heights):
    """Top y for each panel, centred as a group inside the safe band."""
    total = sum(panel_heights) + PANEL_GAP * (len(panel_heights) - 1)
    y = SAFE_TOP + max(0, ((SAFE_BOTTOM - SAFE_TOP) - total) // 2)
    out = []
    for h in panel_heights:
        out.append(int(y))
        y += h + PANEL_GAP
    return out



BEATS = ("hook", "build", "payoff", "landing")


def check_beats(segs):
    """
    Every segment has to say which beat it is, and the beats have to make a
    Short: one hook, at least one payoff, and the payoff last.

    This exists because of a specific failure. A build was approved with three
    beats, then rendered with four: an extra "build" segment added purely to
    reach a length band. It ran 0:10 to 0:16 and it was exactly where the
    viewer said she stopped watching. Padding to hit a number is the failure
    mode this refuses.

    A segment that cannot be named as a beat is a segment nobody chose.
    """
    problems = []
    for i, s in enumerate(segs):
        b = s.get("beat")
        if not b:
            problems.append(f"segment {i} has no beat. One of {', '.join(BEATS)}.")
        elif b not in BEATS:
            problems.append(f"segment {i} beat {b!r} is not one of {', '.join(BEATS)}.")
    if problems:
        return problems

    kinds = [s["beat"] for s in segs]
    if kinds.count("hook") != 1:
        problems.append(f"a Short needs exactly one hook, found {kinds.count('hook')}.")
    if "payoff" not in kinds:
        problems.append("no payoff. A Short that does not land has not made a point.")
    elif kinds[0] != "hook":
        problems.append("the first segment is not the hook.")
    else:
        last_real = [k for k in kinds if k != "landing"][-1]
        if last_real != "payoff":
            problems.append(f"the last spoken beat is {last_real!r}, not the payoff. "
                            "The point goes at the end.")
    if kinds.count("build") > 2:
        problems.append(f"{kinds.count('build')} build segments. More than two is usually "
                        "padding: name what each one adds or cut it.")
    return problems


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"ffmpeg failed:\n{' '.join(cmd)}\n\n{p.stderr[-3000:]}")
    return p


def even(n):
    """H.264 needs even dimensions."""
    return int(n) - (int(n) % 2)


def camera_chain(crop_x, src_h=1080):
    """
    Crop a 9:16 window of full frame height and scale it to the canvas.

    Full height is always kept. Losing headroom reads as a mistake; losing
    width at the sides of a locked-off room shot does not.
    """
    cw = even(src_h * 9 / 16)
    return (f"crop={cw}:{src_h}:{int(crop_x)}:0,"
            f"scale={W}:{H}:flags=lanczos,setsar=1")


def slide_chain(profile, layout, trim=""):
    """
    Slide mode never gets a centre crop: it would cut the slide in half and
    drop the camera inset entirely.

    stacked  slide on top, camera inset scaled up underneath
    solo     slide on top, empty lower panel for captions, no camera

    The canvas is made with pad rather than a colour source. A colour source
    runs forever and has to be bounded by hand, and getting that wrong is how
    the first build produced a segment with no camera in it at all.
    """
    bg = profile.get("bg", "0x000000")
    sx0, sy0, sx1, sy1 = profile["slide"]
    sw, sh = even(sx1 - sx0), even(sy1 - sy0)
    slide_h = even(W * sh / sw)
    slide = (f"crop={sw}:{sh}:{sx0}:{sy0},scale={W}:{slide_h}:flags=lanczos")

    if layout != "stacked":
        (sy,) = stack_positions(slide_h)
        return (f"[0:v]{trim}{slide},"
                f"pad={W}:{H}:0:{sy}:color={bg},setsar=1[v]")

    ix0, iy0, ix1, iy1 = profile["inset"]
    iw, ih = even(ix1 - ix0), even(iy1 - iy0)
    cam_h = even(W * ih / iw)
    sy, cy = stack_positions(slide_h, cam_h)
    return (
        # One input pad cannot feed two filters. Split it.
        f"[0:v]{trim}split=2[s0][s1];"
        f"[s0]{slide},pad={W}:{H}:0:{sy}:color={bg},setsar=1[base];"
        f"[s1]crop={iw}:{ih}:{ix0}:{iy0},scale={W}:{cam_h}:flags=lanczos,setsar=1[cam];"
        f"[base][cam]overlay=0:{cy}[v]"
    )


def segment_args(src, seg, profile, extra_out, with_audio=True):
    """ffmpeg args for one segment, cut and reframed."""
    dur = float(seg["out"]) - float(seg["in"])
    lead = 8.0  # keyframe lead, so fast seek lands before the cut
    ss = max(0.0, float(seg["in"]) - lead)
    trim = float(seg["in"]) - ss

    base = ["ffmpeg", "-v", "error", "-y", "-ss", f"{ss:.3f}", "-i", src]

    if seg["mode"] == "camera":
        vf = f"trim=start={trim:.3f}:duration={dur:.3f},setpts=PTS-STARTPTS,"
        vf += camera_chain(seg.get("crop_x", 0))
        args = base + ["-filter_complex", f"[0:v]{vf}[v]", "-map", "[v]"]
    else:
        tr = f"trim=start={trim:.3f}:duration={dur:.3f},setpts=PTS-STARTPTS,"
        chain = slide_chain(profile, seg.get("layout", "stacked"), trim=tr)
        args = base + ["-filter_complex", chain, "-map", "[v]"]

    if with_audio:
        args += ["-af", f"atrim=start={trim:.3f}:duration={dur:.3f},asetpts=PTS-STARTPTS",
                 "-map", "0:a?"]
    else:
        args += ["-an"]
    return args + extra_out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--proof", type=int, default=None,
                    help="render one still from this segment index instead of the film")
    ap.add_argument("--at", type=float, default=1.0, help="seconds into the segment")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    with open(a.plan, encoding="utf-8") as f:
        plan = json.load(f)
    src, profile = plan["source"], plan["profile"]
    segs = plan["segments"]

    problems = check_beats(segs)
    if problems:
        print("This plan does not describe a Short:")
        for x in problems:
            print(f"  {x}")
        print("")
        print("Fix the plan, or go back to the proposal sheet. Do not pad to a length.")
        sys.exit(1)

    if a.proof is not None:
        seg = dict(segs[a.proof])
        seg["in"] = float(seg["in"]) + a.at
        seg["out"] = seg["in"] + 0.2
        out = a.out or f"proof_{a.proof}.png"
        run(segment_args(src, seg, profile, ["-frames:v", "1", out], with_audio=False))
        print(out)
        return

    tmp = tempfile.mkdtemp(prefix="short_")
    try:
        # Matroska intermediates, so audio can stay PCM through the join.
        # MPEG-TS cannot carry PCM and drops it silently, which is how the
        # first build produced a finished file with no audio stream at all.
        parts = []
        for i, seg in enumerate(segs):
            p = os.path.join(tmp, f"seg{i:03d}.mkv")
            run(segment_args(src, seg, profile,
                             ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
                              "-pix_fmt", "yuv420p", "-r", str(FPS),
                              "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", p]))
            parts.append(p)
            print(f"  segment {i} {seg['mode']:6s} {float(seg['out'])-float(seg['in']):5.2f}s")

        # Every segment is re-encoded here with identical parameters, so the
        # concat demuxer is safe. Remux through MPEG-TS instead when joining
        # stream-copied pieces to re-encoded ones: that mix produced 193
        # non-monotonic DTS frames on the YouTube feature cut.
        listing = os.path.join(tmp, "list.txt")
        with open(listing, "w", encoding="utf-8") as f:
            for p in parts:
                f.write(f"file '{p.replace(chr(92), '/')}'\n")
        joined = os.path.join(tmp, "joined.mkv")
        run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
             "-i", listing, "-c", "copy", joined])

        vf = []
        if plan.get("captions"):
            style = plan.get("caption_style", "")
            vf = ["-vf", f"ass={plan['captions']}" if plan["captions"].endswith(".ass")
                  else f"subtitles={plan['captions']}{style}"]
        # A landing. Most spans do not end on enough silence to stop the clip
        # reading as cut off: the gap after the last word is often a third of a
        # second, and the next sentence starts right after it. Holding the last
        # frame with silent audio manufactures the air the cut does not have.
        hold = float(plan.get("tail_hold", 0) or 0)
        if hold > 0:
            vf = vf or ["-vf", "null"]
            vf[1] = f"{vf[1]},tpad=stop_mode=clone:stop_duration={hold:.2f}"
            tail_a = f",apad=pad_dur={hold:.2f}"
        else:
            tail_a = ""

        # Two pass loudnorm. Single pass missed the target by 1.1 dB once a
        # third short segment changed the mix, because the filter is guessing
        # at the whole-file loudness from a running estimate.
        chain = AUDIO_CHAIN
        m = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostats", "-i", joined,
             "-af", AUDIO_CHAIN + ":print_format=json", "-f", "null", "-"],
            capture_output=True, text=True)
        j = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", m.stderr, re.S)
        if j:
            d = json.loads(j.group(0))
            chain = AUDIO_CHAIN + (
                f":measured_I={d['input_i']}:measured_TP={d['input_tp']}"
                f":measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}"
                f":offset={d['target_offset']}:linear=true")

        run(["ffmpeg", "-v", "error", "-y", "-i", joined] + vf +
            (["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]
             if vf else ["-c:v", "copy"]) +
            ["-af", chain + tail_a, "-c:a", "aac", "-b:a", "192k", plan["output"]])
        print(plan["output"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
