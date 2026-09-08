#!/usr/bin/env python3
"""A whole recording in, a caption file out.

    python transcribe.py --video IN.mp4 --out captions.vtt
    python transcribe.py --video IN.mp4 --out captions.vtt --model small --language en

For a file that arrived with no captions. Every other tool here reads captions
and none of them made any from a whole file: make_captions.py in shorts/
transcribes one cut plan's segments, for burning in. This is the step before
readthrough when the recording came as a file from whoever owns it, which is
the only way a recording arrives now.

WHAT IT REUSES. The three traps make_captions.py already paid for, unchanged:

  * faster-whisper returns nothing at source level, about -34 dBFS. The audio
    is lifted to -16 LUFS first, mono, 16 kHz, with a 75 Hz high-pass.
  * It loops on repetition. Temperature fallback and a repetition penalty are
    on, and each window is transcribed without the previous text as context.
  * It emits phantom words in silence at the end. The VAD filter is on.
  * Handed a whole hour at once, its feature pass asks for the memory of the
    whole hour at once and on this machine did not get it. The audio goes in
    ten minute windows, and a cue that spans a window edge is split there.

WHAT IT DOES NOT DO. It does not name speakers, and it does not invent a word:
where the model is unsure the word is still the model's. Proper nouns are the
least reliable part, as every transcript in this folder has shown: a surname,
a company and a product all misheard. Read the names against the tape.

Nothing here invents a time either. Every cue is the model's segment timing on
the normalised audio, which is the source audio's timing. It locates a passage;
a cut point comes off the waveform.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def hms(s):
    ms = int(round(s * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    sec, ms = divmod(ms, 1000)
    return "%02d:%02d:%02d.%03d" % (h, m, sec, ms)


def normalise(src, wav):
    """Mono 16 kHz at -16 LUFS. Not a delivery level: the level at which the
    model stops returning nothing on this kind of source."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn",
                        "-af", "highpass=f=75,loudnorm=I=-16:TP=-2:LRA=11",
                        "-ac", "1", "-ar", "16000", str(wav)], capture_output=True, text=True)
    if r.returncode != 0 or not wav.is_file() or not wav.stat().st_size:
        sys.exit("ffmpeg could not write the audio: " + (r.stderr or "").strip()[:400])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True, help="the .vtt to write")
    ap.add_argument("--model", default="small",
                    help="faster-whisper model. small is the one measured on this footage; "
                         "medium is untested here (TODO 4 in video-tools)")
    ap.add_argument("--language", default="en")
    ap.add_argument("--beam", type=int, default=5)
    ap.add_argument("--window", type=float, default=600.0,
                    help="seconds of audio handed to the model at a time. A cue "
                         "spanning a window edge is split there.")
    a = ap.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is not on PATH.")
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper is not installed: pip install -r requirements.txt")

    src = Path(a.video).resolve()
    if not src.is_file():
        sys.exit("no file at " + str(src))
    out = Path(a.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    work = Path(tempfile.mkdtemp(prefix="transcribe_"))
    try:
        wav = work / "audio.wav"
        t0 = time.time()
        print("normalising audio to -16 LUFS ...", flush=True)
        normalise(src, wav)
        print("  %.0fs" % (time.time() - t0), flush=True)

        print("loading " + a.model + " ...", flush=True)
        model = WhisperModel(a.model, device="cpu", compute_type="int8")
        total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                      "-of", "csv=p=0", str(wav)], capture_output=True, text=True).stdout.strip() or 0)
        print("transcribing %s, %s, in %d second windows ..." % (src.name, hms(total)[:8], a.window), flush=True)

        # In windows, not in one call. The first run handed the model 71
        # minutes at once and the VAD's feature pass asked for 616 MiB in one
        # array and did not get it. Ten minutes at a time is a tenth of that,
        # and prints progress a person can read.
        cues, words = [], 0
        t1 = time.time()
        start = 0.0
        while start < total:
            dur = min(a.window, total - start)
            chunk = work / ("chunk_%05d.wav" % int(start))
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % start, "-t", "%.3f" % dur,
                            "-i", str(wav), "-c", "copy", str(chunk)], capture_output=True)
            segments, _ = model.transcribe(
                str(chunk), language=a.language, beam_size=a.beam,
                temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
                repetition_penalty=1.15,
                condition_on_previous_text=False,
                vad_filter=True, vad_parameters={"min_silence_duration_ms": 300},
            )
            for s in segments:
                text = " ".join(s.text.split())
                if not text:
                    continue
                cues.append((start + s.start, start + s.end, text))
                words += len(text.split())
            chunk.unlink(missing_ok=True)
            start += dur
            print("  %s  %d cues, %d words, %.0fs elapsed" % (hms(min(start, total))[:8], len(cues), words, time.time() - t1), flush=True)

        with out.open("w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n")
            for i, (b, e, text) in enumerate(cues, 1):
                f.write("%d\n%s --> %s\n%s\n\n" % (i, hms(b), hms(e), text))
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if not cues:
        sys.exit("the model returned no speech at all. Check the audio has a voice track.")
    print("wrote %s: %d cues, %d words, runs to %s, %.0fs in all"
          % (out, len(cues), words, hms(cues[-1][1])[:8], time.time() - t0))
    print("  names are the model's hearing, not facts. Read them against the tape.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
