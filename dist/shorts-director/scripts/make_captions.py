"""
Write burned-in captions for a Short, from the plan that built it.

Shorts are watched muted. YouTube's auto-captions are off by default and wrong
on this footage: the existing transcripts mishear a product name, a surname and
a company name. So captions are burned, which also makes reordering cheap, because
a segment then carries its own text wherever it is moved.

Timings are taken per segment and mapped onto the output timeline, so the
captions stay correct across splices and across a reordered plan.

    python make_captions.py PLAN.json --out burned.ass
    python make_captions.py PLAN.json --out burned.ass --review captions.md

Then put the file in the plan and rebuild:

    "captions": "burned.ass"

Three traps this footage has already sprung, all handled here:

  * faster-whisper returns nothing at source level, about -34 dBFS. Audio is
    normalised to -16 LUFS before transcription.
  * It loops on repetition, repeating one word about 110 times across the
    "me me me and take take take" block. Temperature fallback and a repetition
    penalty are on.
  * It emits phantom fragments on trailing silence. Words that start after the
    last speech energy are dropped.

Nothing here invents a word. Where the model is unsure the word is still
written, but `--review` prints every word under a confidence floor so a human
can correct against the tape before anything is burned.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

W, H = 1080, 1920

# The Shorts player covers the bottom of the frame with title, channel and
# description, and the right edge with the action rail. Captions sit above it.
SAFE_BOTTOM = 1660
OUTLINE = 5
SHADOW = 2
# MarginV positions the text box, and the outline and shadow are drawn outside
# it. Setting the margin to (H - SAFE_BOTTOM) alone put the rendered glyphs 6px
# past the safe line, measured by diffing a captioned frame against an
# uncaptioned one. The border is added back, plus 5px of slack.
MARGIN_V = (H - SAFE_BOTTOM) + OUTLINE + SHADOW + 5
MARGIN_L = MARGIN_R = 90

# Reading limits. Two lines is the most a phone caption can hold without
# becoming a paragraph, and about 32 characters is where a line wraps at this
# size on a 1080 wide frame.
MAX_CHARS_PER_LINE = 32
MAX_LINES = 2
MAX_CUE_SECONDS = 3.2
MIN_CUE_SECONDS = 0.55
GAP_SPLITS_CUE = 0.42             # a pause this long ends the cue

FONT = "Plus Jakarta Sans"
FONT_SIZE = 62
LOW_CONFIDENCE = 0.55


def run(cmd, **kw):
    p = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if p.returncode != 0:
        sys.exit(f"failed: {' '.join(cmd[:6])}...\n\n{p.stderr[-2000:]}")
    return p


def segment_audio(src, start, dur, out):
    """
    Pull one segment's audio and lift it to a level the model can hear.

    -16 LUFS is not a delivery target here, it is the level at which
    faster-whisper stops returning nothing on this source.
    """
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, start - 8):.3f}",
         "-i", src, "-ss", "8", "-t", f"{dur:.3f}",
         "-af", "highpass=f=75,loudnorm=I=-16:TP=-2:LRA=11",
         "-ac", "1", "-ar", "16000", "-vn", out])


def last_speech_end(path, floor_db=-45.0):
    """Where speech actually stops, so phantom trailing words can be dropped."""
    p = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path,
         "-af", f"silencedetect=noise={floor_db}dB:d=0.20", "-f", "null", "-"],
        capture_output=True, text=True)
    import re
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", p.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", p.stderr)]
    if starts and (not ends or ends[-1] < starts[-1]):
        return starts[-1]
    return None


def transcribe(model, path):
    """Word level timings for one segment."""
    segments, _ = model.transcribe(
        path,
        word_timestamps=True,
        # the loop guard: without both of these it repeats one word ~110 times
        # across the "me me me and take take take" block
        temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
        repetition_penalty=1.15,
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
    )
    words = []
    for s in segments:
        for w in (s.words or []):
            t = w.word.strip()
            if t:
                words.append({"t": t, "start": float(w.start),
                              "end": float(w.end), "p": float(w.probability)})
    return words


def group_cues(words):
    """
    Words into cues: break on a real pause, on length, or on duration.

    Breaking on the pause rather than on a word count is what keeps a cue
    aligned with a spoken phrase instead of cutting across one.
    """
    cues, cur = [], []
    for w in words:
        if cur:
            gap = w["start"] - cur[-1]["end"]
            text = join_words(cur + [w])
            too_long = len(text) > MAX_CHARS_PER_LINE * MAX_LINES
            too_slow = w["end"] - cur[0]["start"] > MAX_CUE_SECONDS
            # A cue must never span a splice. Segments are adjacent on the
            # output timeline but can be minutes apart in the source, so
            # merging across one produces a caption joining two unrelated
            # sentences. Seen on the first two-segment build.
            crosses = w.get("seg") != cur[-1].get("seg")
            if crosses or gap >= GAP_SPLITS_CUE or too_long or too_slow:
                cues.append(cur)
                cur = []
        cur.append(w)
    if cur:
        cues.append(cur)
    return cues


def join_words(words):
    """
    Join tokens into a line.

    Whisper emits continuations as their own tokens: "real" then "-world",
    "turn" then "'t". Joining everything on a space produces "real -world",
    which is wrong on screen. Anything opening with a hyphen or an apostrophe
    attaches to the word before it.
    """
    out = ""
    for w in words:
        t = w["t"] if isinstance(w, dict) else w
        if out and not t[0] in "-'’,.!?:;":
            out += " "
        out += t
    return out


def wrap(text):
    """Balance across at most two lines, breaking on a space, never mid word."""
    if len(text) <= MAX_CHARS_PER_LINE:
        return text
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > MAX_CHARS_PER_LINE:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return "\\N".join(lines[:MAX_LINES])


def ts(t):
    """ASS timestamp, centisecond resolution."""
    t = max(0.0, t)
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def ass_document(cues):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Short,{FONT},{FONT_SIZE},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{OUTLINE},{SHADOW},2,{MARGIN_L},{MARGIN_R},{MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for c in cues:
        start = c[0]["start"]
        end = max(c[-1]["end"], start + MIN_CUE_SECONDS)
        text = wrap(join_words(c))
        lines.append(f"Dialogue: 0,{ts(start)},{ts(end)},Short,,0,0,0,,{text}")
    return head + "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--out", required=True)
    ap.add_argument("--review", help="write a markdown sheet of low confidence words")
    ap.add_argument("--model", default="small",
                    help="faster-whisper size. medium is better on proper nouns.")
    a = ap.parse_args()

    with open(a.plan, encoding="utf-8") as f:
        plan = json.load(f)
    src, segs = plan["source"], plan["segments"]

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper is not installed. pip install -r requirements.txt")

    print(f"loading {a.model} ...")
    model = WhisperModel(a.model, device="cpu", compute_type="int8")

    tmp = tempfile.mkdtemp(prefix="caps_")
    all_words, offset, low = [], 0.0, []
    try:
        for i, seg in enumerate(segs):
            dur = float(seg["out"]) - float(seg["in"])
            wav = os.path.join(tmp, f"seg{i:03d}.wav")
            segment_audio(src, float(seg["in"]), dur, wav)

            words = transcribe(model, wav)
            cutoff = last_speech_end(wav)
            if cutoff is not None:
                before = len(words)
                words = [w for w in words if w["start"] < cutoff + 0.10]
                if before != len(words):
                    print(f"  segment {i}: dropped {before - len(words)} word(s) "
                          f"after the last speech at {cutoff:.2f}s")

            for w in words:
                # clamp inside the segment, then move onto the output timeline
                w["seg"] = i
                w["start"] = min(max(w["start"], 0.0), dur) + offset
                w["end"] = min(max(w["end"], 0.0), dur) + offset
                if w["p"] < LOW_CONFIDENCE:
                    low.append((i, w))
            all_words.extend(words)
            print(f"  segment {i} {seg.get('mode','?'):6s} {dur:5.2f}s  {len(words)} words")
            offset += dur
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if not all_words:
        sys.exit("no words transcribed. Check the source path and the segment times.")

    cues = group_cues(all_words)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(ass_document(cues))

    print(f"\n{len(all_words)} words, {len(cues)} cues, {offset:.2f}s -> {a.out}")
    print(f"captions sit {MARGIN_V}px off the bottom, clear of the Shorts UI")

    if low:
        print(f"\n{len(low)} word(s) under {LOW_CONFIDENCE:.0%} confidence. "
              f"Check these against the tape before burning.")
        for i, w in low[:12]:
            print(f"   seg {i}  {w['start']:6.2f}s  {w['p']:.0%}  {w['t']}")
        if len(low) > 12:
            print(f"   ... and {len(low) - 12} more")

    if a.review:
        with open(a.review, "w", encoding="utf-8") as f:
            f.write("# Caption review\n\n")
            f.write(f"From `{os.path.basename(a.plan)}`. "
                    f"{len(all_words)} words, {len(cues)} cues.\n\n")
            f.write("Machine transcription mishears proper nouns on this footage. "
                    "Correct against the tape, then edit the `.ass` directly.\n\n")
            f.write("## Cues\n\n| # | In | Out | Text |\n|---|---|---|---|\n")
            for n, c in enumerate(cues, 1):
                txt = join_words(c).replace("|", "\\|")
                f.write(f"| {n} | {c[0]['start']:.2f} | {c[-1]['end']:.2f} | {txt} |\n")
            if low:
                f.write(f"\n## Low confidence, under {LOW_CONFIDENCE:.0%}\n\n")
                f.write("| Segment | At | Confidence | Word |\n|---|---|---|---|\n")
                for i, w in low:
                    f.write(f"| {i} | {w['start']:.2f} | {w['p']:.0%} | {w['t']} |\n")
        print(f"review sheet -> {a.review}")


if __name__ == "__main__":
    main()
