#!/usr/bin/env python3
"""One picked frame per speaker turn, using the stills tool rather than a midpoint.

    python pick_turn_stills.py --video IN.mp4 --speakers speakers.json --out stills/

Reads the turns that find_speakers.py found, runs
video-tools/stills/scripts/pick_stills.py over each turn's span, and writes
turn-stills.json mapping a turn to the frame chosen inside it.

WHY NOT A MIDPOINT. The first version of the read-through page took the still
already sitting beside the segment index, which is the frame at a segment's
middle. A midpoint is near the right moment rather than chosen: it lands on a
lamp, on someone mid-blink, or on the back of a head, because nothing looked at
it. `pick_stills.py` scores sharpness, contrast, motion and how much of the frame
the moving subject occupies, and drops inserted slides and screen shares.

WHAT IT STILL DOES NOT KNOW. There is no face model on this machine, so nothing
here can say who is in the frame or whether their eyes are open. It shortlists.
A person looks at every frame. The stills manifest repeats that on every run and
it is carried through into turn-stills.json.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PICKER = HERE.parent.parent / "stills" / "scripts" / "pick_stills.py"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--speakers", default="speakers.json")
    ap.add_argument("--out", default="stills")
    ap.add_argument("--per-turn", type=int, default=1,
                    help="frames to shortlist inside each turn")
    ap.add_argument("--every", type=float, default=6.0,
                    help="analysis sampling interval in seconds, passed through")
    ap.add_argument("--page-width", type=int, default=900,
                    help="also write a downscaled copy for embedding in a page. "
                         "The full size pick is left alone. 0 turns it off.")
    ap.add_argument("--head", type=float, default=45.0,
                    help="seconds to skip at the start of a turn, where the host "
                         "is still on camera handing over")
    a = ap.parse_args()

    if not PICKER.is_file():
        print("pick_stills.py not found at " + str(PICKER), file=sys.stderr)
        return 1

    spk = json.loads(Path(a.speakers).read_text(encoding="utf-8"))
    # moments.json calls them stretches, speakers.json called them turns, and
    # segments.json, the read an agent writes, calls them segments and names
    # them by id rather than number. All three are a span with in and out.
    turns = spk.get("stretches") or spk.get("turns_list") or []
    if not turns and spk.get("segments"):
        turns = [dict(s, n=i + 1, label=s.get("id") or ("seg%02d" % (i + 1)))
                 for i, s in enumerate(spk["segments"])]
    if not turns:
        print("No stretches, turns or segments in " + a.speakers, file=sys.stderr)
        return 1

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    result = []

    for t in turns:
        label = t.get("label") or ("turn%02d" % t["n"])
        lo = t["in"] + a.head
        hi = t["out"]
        if hi - lo < 10:
            lo = t["in"]
        who = t.get("who") or t.get("name_read") or (t.get("opened_by") or {}).get("name_read") or "unnamed"
        print("%s  %s  %.0fs to %.0fs" % (label, who, lo, hi), flush=True)
        cmd = [sys.executable, str(PICKER), "--video", a.video, "--out", str(out),
               "--label", label, "--count", str(a.per_turn),
               "--every", str(a.every), "--from", "%.3f" % lo, "--to", "%.3f" % hi]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print("  picker failed: " + (r.stderr or "").strip()[:300], flush=True)
            result.append({"n": t["n"], "still": None, "why": "picker failed"})
            continue

        man = out / (label + ".stills.json")
        if not man.is_file():
            result.append({"n": t["n"], "still": None, "why": "no manifest written"})
            continue
        m = json.loads(man.read_text(encoding="utf-8"))
        picks = m.get("picks") or []
        if not picks:
            result.append({"n": t["n"], "still": None, "why": "nothing passed the picker"})
            continue
        best = picks[0]
        # A page embeds these as base64 and a 1080p frame off a 4.5GB source is
        # about 280KB, so seven of them made a 2MB page. The full size pick is a
        # deliverable and is not touched; this is a second, smaller copy that
        # only the page uses.
        # Never upscale. One source here is 1920 wide and the other is 640, so a
        # flat scale to 900 made the second one a bigger blurry frame. Only a
        # source wider than the target gets a web copy; a narrow one is already
        # small and the page embeds it as it is.
        web = None
        if a.page_width and (best.get("width") or 0) > a.page_width:
            src_img = out / best["file"]
            web_name = best["file"].replace(".jpg", " - web.jpg")
            r2 = subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-i", str(src_img),
                 "-vf", "scale=%d:-2" % a.page_width, "-q:v", "4", str(out / web_name)],
                capture_output=True, text=True)
            if r2.returncode == 0 and (out / web_name).is_file():
                web = out.name + "/" + web_name

        result.append({
            "n": t["n"],
            "id": t.get("label"),
            "still": web or (out.name + "/" + best["file"]),
            "still_full": out.name + "/" + best["file"],
            "at_seconds": best["at_seconds"],
            "at_timecode": best["at_timecode"],
            "sharpness": best.get("sharpness_fullres"),
            "subject_frac": best.get("subject_frac"),
            "frames_analysed": m.get("frames_analysed"),
            "graphics_dropped": m.get("graphics_dropped"),
            "graphics_at_s": m.get("graphics_at_s"),
            "sampled_every_s": m.get("sampled_every_s"),
            "subject_floor": m.get("subject_floor"),
            "samples_fields": m.get("samples_fields"),
            "samples": m.get("samples"),
        })
        print("  picked %s at %s" % (best["file"], best["at_timecode"]), flush=True)

    doc = {
        "schema": "readthrough-turn-stills/v1",
        "video": a.video,
        "speakers": a.speakers,
        "settings": {"per_turn": a.per_turn, "every_s": a.every, "head_skip_s": a.head},
        "not_measured": "No face detection. Nothing here knows who is in a frame or "
                        "whether their eyes are open. Look at every frame before it goes out.",
        "turns": result,
    }
    # Beside the stills folder, not in the working directory. A run driven
    # from run.py has a different cwd and the manifest went missing.
    # Named for the folder, so segment-stills/ writes segment-stills.json
    # beside it and does not overwrite the stretch manifest.
    manifest_path = out.parent / (out.name + ".json")
    manifest_path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    got = sum(1 for x in result if x["still"])
    print("picked %d of %d turns, wrote %s" % (got, len(result), manifest_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
