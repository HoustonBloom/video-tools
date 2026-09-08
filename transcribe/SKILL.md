---
name: transcribe
description: Make a caption file from a whole video that arrived with none, so the readthrough and the other caption-reading tools can run on it. Use when somebody hands over a recording as a file and there is no .vtt or .srt beside it. It names no speakers and invents no words.
---

# Transcribe

A whole recording in, a `.vtt` out. Needs Python, faster-whisper and ffmpeg.

```bash
python scripts/transcribe.py --video IN.mp4 --out captions.vtt
```

Flags: `--model` (default `small`, the one measured on this footage),
`--language` (default `en`), `--beam` (default 5).

## The one thing to know

**The file is the only proof.** The script exits non-zero when the model
returns no speech, and it prints the cue and word counts and where the
transcript runs to. Read those before calling it done, and read the names
against the tape: proper nouns are the least reliable part of any transcript
from this model.

## What it handles

Audio lifted to -16 LUFS before the model hears it, because faster-whisper
returns nothing at source level. Repetition loops damped. Phantom words in
silence filtered. All three lifted from `shorts/scripts/make_captions.py`,
which met them first.

## What it does not do

No speaker names. No invented words. No cut points: a cue time locates a
passage, and `shorts/scripts/find_edges.py` places the cut.

## Where it sits

Before `readthrough` when the recording came as a file. There is no
fetch-from-a-link step any more; downloading from a platform by script is
against its terms, and the file comes from whoever owns it.
