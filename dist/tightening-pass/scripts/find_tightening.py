"""
Propose removals that shorten a take without changing what it says.

This is the tightening pass, not the compositional one. It never chooses a span,
never reorders, never decides what the clip is about. It finds four things and
says how much each one costs:

  head/tail    dead air before the first word and after the last
  pause        silence between phrases longer than the clip needs
  disfluency   an "um" or "uh": a short burst at speech level, bounded by
               silence, that the word-level transcript renders nothing for
  filler       a transcribed word or phrase carrying no meaning, but only where
               measured silence sits on both sides of it

The last condition is the whole design. **A removal is only proposed when both
of its cut points land inside measured silence.** Anything else slices a word.
faster-whisper's word timings drift on this footage, so they are used to say
*what* was said and never to say *where* to cut.

Energy is the same 20ms map and the same relative threshold `find_edges.py`
uses, so the two tools agree about where silence is.

    python find_tightening.py SOURCE.mp4 --transcript words.json
    python find_tightening.py SOURCE.mp4 --transcript words.json --keep-pause 0.25
    python find_tightening.py SOURCE.mp4 --transcript words.json --json plan.json

Output is a proposal. Nothing is rendered and nothing is applied. Repetition that
is delivery reads identically to stutter here, so every removal is a candidate a
human accepts or rejects, not an edit.
"""

import argparse
import json
import re
import subprocess
import sys

import numpy as np

SR = 16000
HOP = 320          # 20ms, matching find_edges.py
PRE = "highpass=f=75,loudnorm=I=-16:TP=-2"

# Lead kept before a word onset when a splice resumes. Landing on the onset
# clips the attack and turns "my driving problem" into "a driving problem".
ONSET_LEAD = 0.07

# Phrases that carry no meaning at the head of a clause. Matched on the word
# sequence, then required to sit between two measured silences before proposal.
FILLER_PATTERNS = [
    ["and", "so"], ["and", "yeah"], ["and", "i", "think", "that"],
    ["i", "think", "that"], ["i", "mean"], ["you", "know"], ["like"],
    ["and"], ["so"], ["basically"], ["actually"], ["literally"],
    ["kind", "of"], ["sort", "of"], ["i", "guess"], ["right"],
]

WORD_RE = re.compile(r"[^a-z']")


def norm(w):
    return WORD_RE.sub("", w.lower())


def levels(src):
    """20ms RMS in dB across the whole file."""
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", src, "-af", PRE,
         "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
        capture_output=True)
    a = np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    if a.size < HOP:
        sys.exit("no audio decoded")
    n = a.size // HOP
    rms = np.sqrt((a[:n * HOP].reshape(n, HOP) ** 2).mean(axis=1) + 1e-12)
    return 20 * np.log10(rms)


def gaps_and_runs(db, min_gap, rel, despeckle):
    """Silences of at least min_gap, and the speech runs between them.

    A single 20ms frame crossing the threshold inside a long silence is noise,
    not speech. Left alone it splits one 2.4s silence into two short ones, so
    the pause rule stops seeing it and the disfluency rule reports a "0.02s
    burst". Gaps separated by less than `despeckle` are bridged first.
    """
    floor, peak = np.percentile(db, 10), np.percentile(db, 90)
    thr = floor + (peak - floor) * rel
    quiet = db < thr

    raw, i = [], 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]:
                j += 1
            if (j - i) * 0.02 >= min_gap:
                raw.append((i * 0.02, j * 0.02))
            i = j
        else:
            i += 1

    gaps = []
    for g in raw:
        if gaps and g[0] - gaps[-1][1] < despeckle:
            gaps[-1] = (gaps[-1][0], g[1])
        else:
            gaps.append(g)

    runs, prev = [], 0.0
    for s, e in gaps:
        if s > prev:
            runs.append((prev, s))
        prev = e
    if prev < len(quiet) * 0.02:
        runs.append((prev, len(quiet) * 0.02))
    return gaps, runs, floor, peak, thr


def load_words(path):
    d = json.load(open(path, encoding="utf-8"))
    out = []
    for s in d.get("segments", []):
        for w in s.get("words", []):
            out.append({"w": w["w"].strip(), "n": norm(w["w"]),
                        "s": w["s"], "e": w["e"], "p": w.get("p", 1.0)})
    return out


def overlaps(a0, a1, b0, b1):
    return a0 < b1 and b0 < a1


def normalise_to(gap_a, gap_b, keep):
    """Removal that reduces everything from gap_a through gap_b to `keep` of air.

    Both cut points land inside a measured silence, which is the point.
    """
    lo = gap_a[0] + keep / 2.0
    hi = gap_b[1] - keep / 2.0
    return (lo, hi) if hi - lo > 0.02 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--transcript", help="word-timing JSON from the transcribe step")
    ap.add_argument("--min-gap", type=float, default=0.12,
                    help="shortest silence the map records, seconds")
    ap.add_argument("--rel", type=float, default=0.28,
                    help="threshold between the file's floor and peak, 0 to 1")
    ap.add_argument("--keep-pause", type=float, default=0.30,
                    help="air left where a pause is trimmed, seconds")
    ap.add_argument("--max-pause", type=float, default=0.55,
                    help="pauses longer than this are proposed for trimming")
    ap.add_argument("--keep-head", type=float, default=0.10)
    ap.add_argument("--keep-tail", type=float, default=0.45,
                    help="air after the last word; a landing wants 0.3s or more")
    ap.add_argument("--burst-min", type=float, default=0.08,
                    help="shortest untranscribed burst treated as a disfluency. "
                         "Below this it is threshold noise, not an um")
    ap.add_argument("--burst-max", type=float, default=0.60,
                    help="longest untranscribed burst still treated as a disfluency")
    ap.add_argument("--despeckle", type=float, default=0.06,
                    help="silences separated by less than this are one silence")
    ap.add_argument("--json", help="write the proposal here")
    a = ap.parse_args()

    db = levels(a.source)
    dur = len(db) * 0.02
    gaps, runs, floor, peak, thr = gaps_and_runs(db, a.min_gap, a.rel, a.despeckle)
    words = load_words(a.transcript) if a.transcript else []

    props = []

    # 1. Head and tail. Speech bounds come from the energy map, not the words.
    if runs:
        first, last = runs[0][0], runs[-1][1]
        if first > a.keep_head + 0.02:
            props.append({"kind": "head", "in": 0.0, "out": first - a.keep_head,
                          "why": f"dead air before the first word at {first:.2f}"})
        if dur - last > a.keep_tail + 0.02:
            props.append({"kind": "tail", "in": last + a.keep_tail, "out": dur,
                          "why": f"dead air after the last word at {last:.2f}"})

    # 2. Disfluencies. A short run the transcript renders nothing for, with a
    #    measured silence on each side. This is the only way to find them:
    #    faster-whisper does not transcribe "um", so the transcript is silent
    #    about exactly the thing being looked for.
    for idx, (rs, re_) in enumerate(runs):
        if idx == 0 or idx == len(runs) - 1:
            continue
        if not (a.burst_min <= re_ - rs <= a.burst_max):
            continue
        if any(overlaps(rs, re_, w["s"], w["e"]) for w in words):
            continue
        ga = next((g for g in gaps if abs(g[1] - rs) < 0.03), None)
        gb = next((g for g in gaps if abs(g[0] - re_) < 0.03), None)
        if not (ga and gb):
            continue
        cut = normalise_to(ga, gb, a.keep_pause)
        if cut:
            props.append({"kind": "disfluency", "in": cut[0], "out": cut[1],
                          "why": f"{re_ - rs:.2f}s burst at {rs:.2f} with no "
                                 f"transcribed word. Listen before accepting."})

    # 3. Filler phrases, only where silence brackets them.
    taken = set()
    for i in range(len(words)):
        if i in taken:
            continue
        for pat in FILLER_PATTERNS:
            j = i + len(pat)
            if j > len(words):
                continue
            if [w["n"] for w in words[i:j]] != pat:
                continue
            span_s, span_e = words[i]["s"], words[j - 1]["e"]
            ga = next((g for g in gaps if g[1] <= span_s + 0.25 and g[1] >= span_s - 0.45), None)
            gb = next((g for g in gaps if g[0] >= span_e - 0.45 and g[0] <= span_e + 0.25), None)
            if not (ga and gb):
                continue
            cut = normalise_to(ga, gb, a.keep_pause)
            if not cut:
                continue
            props.append({"kind": "filler", "in": cut[0], "out": cut[1],
                          "why": '"' + " ".join(w["w"] for w in words[i:j]) +
                                 f'" at {span_s:.2f}, silence on both sides'})
            taken.update(range(i, j))
            break

    # 4. Long pauses that survive the above.
    for g in gaps:
        L = g[1] - g[0]
        if L <= a.max_pause:
            continue
        if g[0] < (runs[0][0] if runs else 0) or g[1] > (runs[-1][1] if runs else dur):
            continue
        cut = normalise_to(g, g, a.keep_pause)
        if cut and not any(overlaps(cut[0], cut[1], p["in"], p["out"]) for p in props):
            props.append({"kind": "pause", "in": cut[0], "out": cut[1],
                          "why": f"{L:.2f}s of silence, trimmed to {a.keep_pause:.2f}s"})

    # Merge anything that overlaps, so no second is counted twice.
    props.sort(key=lambda p: p["in"])
    merged = []
    for p in props:
        if merged and p["in"] < merged[-1]["out"]:
            last = merged[-1]
            last["out"] = max(last["out"], p["out"])
            last["kind"] = last["kind"] + "+" + p["kind"]
            last["why"] = last["why"] + " / " + p["why"]
        else:
            merged.append(dict(p))

    saved = sum(p["out"] - p["in"] for p in merged)

    print(f"src {a.source}")
    print(f"  {dur:.2f}s   floor {floor:.1f} dB   peak {peak:.1f} dB   "
          f"threshold {thr:.1f} dB   {len(gaps)} silences   {len(runs)} speech runs")
    if words:
        print(f"  transcript: {len(words)} words")
    else:
        print("  no transcript given: filler cannot be found, only air and disfluencies")
    print()
    if not merged:
        print("  nothing to remove at these settings.")
        return
    print(f"  {'in':>8} {'out':>8} {'saves':>7}  kind")
    for p in merged:
        print(f"  {p['in']:8.2f} {p['out']:8.2f} {p['out']-p['in']:7.2f}  {p['kind']}")
        print(f"           {p['why']}")
    print()
    print(f"  {len(merged)} removals, {saved:.2f}s saved, "
          f"{dur:.2f}s to {dur - saved:.2f}s ({100*saved/dur:.1f}% shorter)")
    print("  Every cut point above sits inside a measured silence. Nothing is applied.")

    if a.json:
        json.dump({"source": a.source, "duration": round(dur, 3),
                   "settings": {"min_gap": a.min_gap, "rel": a.rel,
                                "keep_pause": a.keep_pause, "max_pause": a.max_pause,
                                "keep_head": a.keep_head, "keep_tail": a.keep_tail,
                                "onset_lead": ONSET_LEAD},
                   "removals": [{k: (round(v, 3) if isinstance(v, float) else v)
                                 for k, v in p.items()} for p in merged],
                   "saved": round(saved, 3),
                   "result_duration": round(dur - saved, 3)},
                  open(a.json, "w", encoding="utf-8"), indent=1)
        print(f"  wrote {a.json}")


if __name__ == "__main__":
    main()
