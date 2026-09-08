"""
Render a composition to one or more delivery targets.

`build_short.py` crops a 9:16 window out of a wide source, which is right for
16:9 talk footage and wrong for a 3:4 phone source: there is no spare width to
throw away, and the crop takes 270px off a frame the speaker already fills. See
`../../DELIVERY-TARGETS.md` for the measurement.

    python build_padded.py PLAN.json --proof 0 --at 2.0 --out proof.png
    python build_padded.py PLAN.json
    python build_padded.py PLAN.json --target feed

Plan format:

    {
      "kind": "composition",
      "fps": 30,
      "output": ".../cut.mp4",         # stem; each target appends its name
      "targets": [
        {"name": "reels",  "canvas": [1080, 1920], "fit": "pad",  "fill": "blur"},
        {"name": "feed",   "canvas": [1080, 1350], "fit": "pad",  "fill": "blur"},
        {"name": "square", "canvas": [1080, 1080], "fit": "crop", "anchor": "top"}
      ],
      "segments": [
        {"source": "...", "in": 84.14, "out": 110.81,
         "beat": "hook", "why": "..."}
      ]
    }

With no `targets` it renders one 1080x1920 padded file, which is what the first
version did.

**Beats are enforced**, the same contract `build_short.py` applies: one hook, a
payoff last, at most two builds. A segment that cannot be named as a beat is a
segment nobody chose. The first version of this renderer did not check, which
meant the pipeline's own discipline stopped at the tool boundary.

Two things `delivery.md` paid for, both honoured:

- **Fast-seek with a keyframe lead, then trim precisely.**
- **Concatenate through MPEG-TS.** The concat demuxer produced 193 consecutive
  non-monotonic DTS frames where re-encoded pieces met stream-copied ones.

Nothing is posted. This writes files.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

LEAD = 8.0            # keyframe lead before a cut point, seconds

# The source recordings sit 10 to 11 dB under target, not the 20 dB the
# original chain was built for, so the compressor is gentler here.
#
# **Loudness is corrected on the finished file, not per segment.** Single pass
# loudnorm on a short segment does not converge, and it fails silently: a four
# segment cut came out at -20.9 LUFS against a -14 target with 4.5 dB of unused
# headroom and LRA crushed to 1.4, while a one segment cut from the same source
# landed at -14.1. Measure the concatenation, then apply the measurement.
AUDIO_CHAIN = ("highpass=f=75,"
               "acompressor=threshold=-20dB:ratio=2:attack=20:release=250")

TARGET_I, TARGET_TP, TARGET_LRA = -14.0, -1.5, 11.0

DEFAULT_TARGETS = [{"name": "", "canvas": [1080, 1920], "fit": "pad", "fill": "blur"}]

BEATS = ("hook", "build", "payoff", "landing")


def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"ffmpeg failed\n{' '.join(args[:12])}...\n{p.stderr[-1500:]}")
    return p


def measure_i(path):
    """Integrated loudness of a file, in LUFS, off ebur128."""
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128",
         "-f", "null", "-"], capture_output=True, text=True).stderr
    hits = re.findall(r"I:\s*(-?\d+\.?\d*)\s*LUFS", out)
    if not hits:
        sys.exit(f"could not measure loudness of {path}")
    return float(hits[-1])


def normalise(raw, out, tolerance=0.3, max_passes=4):
    """Bring `raw` to TARGET_I, and verify it got there.

    **loudnorm is not used, because it fails silently on this material.** These
    takes have a high crest factor: a quiet speaker with loud transients. To
    reach -14 LUFS the gain needed is over 13 dB, which pushes true peak past
    the -1.5 dBTP ceiling, so loudnorm caps the gain and still reports success.
    One cut came out at -18.7 LUFS with the tool printing that it had corrected
    to -14.0. Dynamic mode (`linear=false`) fails the same way for the same
    reason.

    Gain plus a true-peak limiter reaches the target, and the limiter costs
    around 0.8 dB per pass, so the result is measured and the gain corrected
    until it lands. Every pass renders from `raw`, never from the previous
    output, so there is one generation of audio encoding regardless.
    """
    limit = 10 ** (TARGET_TP / 20.0)          # -1.5 dBTP as linear amplitude
    measured = measure_i(raw)
    gain = TARGET_I - measured
    for p in range(1, max_passes + 1):
        run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-c:v", "copy",
             "-af", f"volume={gain:.2f}dB,alimiter=limit={limit:.4f}:level=false",
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
             "-movflags", "+faststart", out])
        got = measure_i(out)
        if abs(got - TARGET_I) <= tolerance:
            return measured, got, p
        gain += TARGET_I - got
    return measured, got, max_passes

def check_beats(segs):
    """One hook, a payoff last, at most two builds. Same contract as build_short."""
    problems = []
    for i, s in enumerate(segs):
        b = s.get("beat")
        if b is None:
            problems.append(f"segment {i} has no beat. One of {', '.join(BEATS)}.")
        elif b not in BEATS:
            problems.append(f"segment {i} beat {b!r} is not one of {', '.join(BEATS)}.")
    if problems:
        return problems
    # A beat can be several spliced pieces once the tightening pass has run
    # inside it, so consecutive segments carrying the same beat are one beat.
    kinds = []
    for s in segs:
        if not kinds or kinds[-1] != s["beat"]:
            kinds.append(s["beat"])
    if kinds.count("hook") != 1:
        problems.append(f"{kinds.count('hook')} hook segments. A cut has exactly one.")
    spoken = [k for k in kinds if k != "landing"]
    if spoken and spoken[-1] != "payoff":
        problems.append(f"the last spoken beat is {spoken[-1]!r}, not the payoff.")
    if kinds.count("payoff") == 0:
        problems.append("no payoff. A cut that does not land has not made a point.")
    if kinds.count("build") > 2:
        problems.append(f"{kinds.count('build')} build segments. More than two is "
                        "usually padding: name what each one adds or cut it.")
    return problems


def video_chain(t, fps):
    """Source at its own aspect on the target canvas."""
    cw, ch = t["canvas"]
    fit = t.get("fit", "pad")
    if fit == "crop":
        # Anchor matters: the speaker's head touches the top of these frames, so
        # a centred square crop takes the top of her head off.
        anchor = t.get("anchor", "center")
        y = {"top": "0", "bottom": "(ih-oh)", "center": "(ih-oh)/2"}[anchor]
        return (f"[0:v]fps={fps},scale={cw}:-2,crop={cw}:{ch}:0:{y},setsar=1[v]")
    fill = t.get("fill", "blur")
    if fill == "blur":
        return (
            f"[0:v]fps={fps},split=2[bg][fg];"
            f"[bg]scale={cw}:{ch}:force_original_aspect_ratio=increase,"
            f"crop={cw}:{ch},gblur=sigma=40[bgb];"
            f"[fg]scale={cw}:{ch}:force_original_aspect_ratio=decrease[fgs];"
            f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2,setsar=1[v]"
        )
    return (
        f"[0:v]fps={fps},scale={cw}:{ch}:force_original_aspect_ratio=decrease,"
        f"pad={cw}:{ch}:(ow-iw)/2:(oh-ih)/2:color={fill},setsar=1[v]"
    )


def segment_args(seg, t, fps, out, with_audio=True):
    a, b = float(seg["in"]), float(seg["out"])
    dur = b - a
    ss = max(0.0, a - LEAD)
    trim = a - ss
    args = ["ffmpeg", "-v", "error", "-y", "-ss", f"{ss:.3f}", "-i", seg["source"],
            "-filter_complex", video_chain(t, fps), "-map", "[v]"]
    if with_audio:
        # No atrim here. The output -ss/-t below trims every stream together.
        # Doing both truncated the audio by the keyframe lead on every segment:
        # atrim cut to [trim, trim+dur], then -ss trim took another `trim`
        # seconds off the front. An 18.5s cut shipped with 1.5s of audio and
        # every check passed, because they tested that an audio stream existed
        # rather than how long it was.
        args += ["-map", "0:a:0", "-af", AUDIO_CHAIN,
                 "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
    else:
        args += ["-an"]
    args += ["-ss", f"{trim:.3f}", "-t", f"{dur:.3f}",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-pix_fmt", "yuv420p", "-r", str(fps), out]
    return args


def render_target(segs, t, fps, out):
    tmp = tempfile.mkdtemp(prefix="padded_")
    try:
        ts = []
        for i, seg in enumerate(segs):
            mp4 = os.path.join(tmp, f"s{i:02d}.mp4")
            run(segment_args(seg, t, fps, mp4))
            p = os.path.join(tmp, f"s{i:02d}.ts")
            run(["ffmpeg", "-v", "error", "-y", "-i", mp4,
                 "-c", "copy", "-bsf:v", "h264_mp4toannexb", "-f", "mpegts", p])
            ts.append(p)
        raw = os.path.join(tmp, "joined.mp4")
        run(["ffmpeg", "-v", "error", "-y", "-i", "concat:" + "|".join(ts),
             "-c", "copy", "-bsf:a", "aac_adtstoasc", raw])

        before, after, passes = normalise(raw, out)
        return before, after, passes
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--target", help="render only the target with this name")
    ap.add_argument("--proof", type=int, help="render one still from this segment")
    ap.add_argument("--at", type=float, default=1.0)
    ap.add_argument("--out", help="where the proof still goes")
    a = ap.parse_args()

    plan = json.load(open(a.plan, encoding="utf-8"))
    fps = int(plan.get("fps", 30))
    segs = plan["segments"]
    targets = plan.get("targets", DEFAULT_TARGETS)
    if a.target:
        targets = [t for t in targets if t.get("name") == a.target]
        if not targets:
            sys.exit(f"no target named {a.target!r} in the plan")

    for i, s in enumerate(segs):
        if not os.path.exists(s["source"]):
            sys.exit(f"segment {i}: source not found, {s['source']}")
        if float(s["out"]) <= float(s["in"]):
            sys.exit(f"segment {i}: out is not after in")

    problems = check_beats(segs)
    if problems:
        print("This plan does not describe a cut:")
        for p in problems:
            print(f"  {p}")
        print("Fix the plan, or go back to the proposal sheet. Do not pad to a length.")
        sys.exit(1)

    if a.proof is not None:
        seg = segs[a.proof]
        at = float(seg["in"]) + a.at
        out = a.out or "proof.png"
        ss = max(0.0, at - LEAD)
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{ss:.3f}", "-i", seg["source"],
             "-ss", f"{at - ss:.3f}", "-filter_complex", video_chain(targets[0], fps),
             "-map", "[v]", "-frames:v", "1", "-update", "1", "-f", "image2", out])
        print(f"proof from segment {a.proof} at +{a.at:.2f}s, "
              f"target {targets[0].get('name') or 'default'} -> {out}")
        return

    stem, ext = os.path.splitext(plan["output"])
    total = sum(float(s["out"]) - float(s["in"]) for s in segs)
    print(f"  {len(segs)} segment(s), {total:.2f}s, beats "
          f"{' '.join(s['beat'] for s in segs)}")
    for t in targets:
        name = t.get("name") or ""
        out = f"{stem}_{name}{ext}" if name else plan["output"]
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        before, after, passes = render_target(segs, t, fps, out)
        cw, ch = t["canvas"]
        flag = "" if abs(after - TARGET_I) <= 0.3 else "   <-- MISSED TARGET"
        print(f"  {name or 'default':8} {cw}x{ch} {t.get('fit','pad'):5} "
              f"-> {os.path.basename(out)}  {before:.1f} to {after:.1f} LUFS "
              f"in {passes} pass(es){flag}")


if __name__ == "__main__":
    main()
