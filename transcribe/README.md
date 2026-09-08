# transcribe

**A caption file from a recording that has none.** One script. Everything else
in this folder reads captions; this makes them.

For when a video arrives as a file with nothing beside it.

```bash
pip install -r requirements.txt          # faster-whisper; plus ffmpeg on PATH
python scripts/transcribe.py --video IN.mp4 --out captions.vtt
```

| Flag | Default | What it does |
|---|---|---|
| `--model` | `small` | The faster-whisper model. `small` is the one measured here. |
| `--language` | `en` | |
| `--beam` | `5` | Beam size. |
| `--window` | `600` | Seconds of audio handed to the model at a time. A cue that spans a window edge is split there. |

**What it does on the way in.** Lifts the audio to -16 LUFS, mono, 16 kHz,
because the model returns nothing at source level. Damps repetition loops.
Filters phantom words in silence. Feeds the model ten minutes at a time so the
feature pass fits in memory on a whole hour.

**What it does not do.** It does not name speakers; Zoom and Teams transcripts
do, and if you have one of those, use it instead. It does not invent a word:
where the model is unsure the word is still the model's, and proper nouns are
the least reliable part. Read names against the tape. A cue time locates a
passage; it cannot place a cut.

**Measured.** One 1:10:38 talk, `small`, CPU, no GPU: 1,398 cues, 9,822
words, 23m49s wall time, 4m15s of it normalising. About a third of the
recording's length. The first run downloads the model once, 464MB.
