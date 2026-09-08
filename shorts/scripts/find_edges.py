"""
Find the places a cut can land, from a 20ms energy map.

A splice has to sit inside real silence. Transcript word timings are wrong by
tens of milliseconds and will slice the middle of a word: on this footage a cut
placed off the transcript turned "my driving problem" into "a driving problem".
The waveform is the authority, and this is the same 20ms method the existing cut
records used.

    python find_edges.py SOURCE.mp4 --start 1986 --end 2016
    python find_edges.py SOURCE.mp4 --start 1986 --end 2016 --min-gap 0.30

Read the output as: cut on the midpoint of a gap to enter or leave cleanly, and
cut on the *end* of the last gap when you want the clip to land, so the air
belongs to your clip rather than to the next sentence.

The threshold is relative, taken between the 10th and 90th percentile of the
region. A fixed dB floor does not travel: the same recording measured -41.8 dB
in one span and -38.7 dB in another 60 seconds later, and a fixed -38 dB floor
found twelve gaps in the first and none in the second.
"""

import argparse
import subprocess
import sys

import numpy as np

SR = 16000
HOP = 320          # 20ms
PRE = "highpass=f=75,loudnorm=I=-16:TP=-2"


def levels(src, start, dur):
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}",
         "-i", src, "-af", PRE, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
        capture_output=True)
    a = np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    if a.size < HOP:
        sys.exit("no audio decoded for that span")
    n = a.size // HOP
    rms = np.sqrt((a[:n * HOP].reshape(n, HOP) ** 2).mean(axis=1) + 1e-12)
    return 20 * np.log10(rms)


def gaps(db, base, min_gap, rel):
    floor, peak = np.percentile(db, 10), np.percentile(db, 90)
    thr = floor + (peak - floor) * rel
    quiet = db < thr
    out, i = [], 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]:
                j += 1
            if (j - i) * 0.02 >= min_gap:
                out.append((base + i * 0.02, base + j * 0.02))
            i = j
        else:
            i += 1
    return out, floor, peak, thr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--start", type=float, required=True)
    ap.add_argument("--end", type=float, required=True)
    ap.add_argument("--min-gap", type=float, default=0.16,
                    help="shortest gap worth reporting, seconds")
    ap.add_argument("--rel", type=float, default=0.28,
                    help="threshold between the region's floor and peak, 0 to 1")
    a = ap.parse_args()

    dur = a.end - a.start
    if dur <= 0:
        sys.exit("--end must be after --start")
    db = levels(a.source, a.start, dur)
    found, floor, peak, thr = gaps(db, a.start, a.min_gap, a.rel)

    print(f"src {a.start:.2f} to {a.end:.2f}   floor {floor:.1f} dB   "
          f"peak {peak:.1f} dB   threshold {thr:.1f} dB")
    if not found:
        print("  no gaps at this threshold. Try --rel 0.4 or --min-gap 0.12.")
        return
    print(f"  {len(found)} gap(s) of {a.min_gap:.2f}s or more\n")
    print(f"  {'gap start':>10} {'gap end':>10} {'length':>7}   "
          f"{'enter/leave':>11} {'land on':>8}")
    for s, e in found:
        print(f"  {s:10.2f} {e:10.2f} {e - s:7.2f}   {(s + e) / 2:11.2f} {e:8.2f}")

    longest = max(found, key=lambda g: g[1] - g[0])
    print(f"\n  longest gap {longest[1] - longest[0]:.2f}s at "
          f"{longest[0]:.2f}, the safest splice in this span")
    print("  a landing wants 0.3s or more of air. If no gap is that long, cut "
          "before the next\n  sentence starts and add tail_hold to the plan.")


if __name__ == "__main__":
    main()
