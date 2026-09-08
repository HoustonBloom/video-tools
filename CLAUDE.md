# Working in video-tools

Rules for an agent running these tools or changing them.

## 1. Never commit media

`.gitignore` refuses video, audio and caption files by extension, and refuses
`renders/`, `proofs/` and `out/`. Do not add an exception. A master can be
15GB and a single proof frame several MB. If a clip needs to be shown, write it
beside the footage and give the path.

## 2. The plan is the deliverable

Do not render a cut nobody approved. Write the plan, show it, then build. Every
segment carries a `why`; a segment that cannot say why it is there has not been
chosen. A render is disposable because its plan is not.

## 3. Proof frame before film

Render one still and look at it before rendering the whole clip. It is the
only check that catches a filter graph that returned success and produced an
empty panel.

```bash
python shorts/scripts/build_short.py PLAN.json --proof 0 --at 2.0 --out proof.png
```

## 4. Measure, do not estimate

Geometry off pixels. Loudness off the file. Cut points off the waveform at
20ms, not off transcript timings, which are wrong by tens of milliseconds and
will slice the middle of a word.

A number with no measurement behind it is written as absent, with the
instrument that would fill it named beside it. No "roughly", "~" or "[est]"
without an estimation process.

Two facts about faster-whisper:

- It does not transcribe disfluencies. Grepping a transcript for "um" returns
  zero however many are in the audio. Find them as short bursts at speech level
  isolated by silence on both sides.
- It returns nothing at source-level audio, around -34 dBFS, and emits phantom
  trailing fragments on clips ending in silence. Normalise to about -16 LUFS
  before transcribing, and settle anything ambiguous against the waveform.

## 5. Verify before calling it done

```bash
python shorts/scripts/verify_short.py OUT.mp4
```

It measures loudness, true peak, loudness range, dimensions, Shorts eligibility
and the air after the last word. It does not measure whether the crop is aimed
at the right person or whether a splice ate a consonant. Those need the proof
frame and a re-transcribe.

## 6. The read is a step, and a script cannot take it

`readthrough` matches phrases in captions. It cannot find a guest speaker or a
featured founder unless the host used a phrase it already knows. The agent
reads the whole transcript against the checklist in `readthrough/SKILL.md` and
writes `segments.json`. Without it the page builds and says at the top that the
recording has not been read.

## 7. Nothing is published

These tools write files. No upload, no post, no push. The owner decides what
leaves an account, per action.

## 8. Nothing is deleted

A superseded cut, plan or script moves out of the repo with a
`(superseded YYYY-MM-DD)` suffix. It does not get deleted.

## 9. Nothing is fetched from a platform

A recording comes as a file from whoever owns it: the channel owner downloads
from YouTube Studio, or hands over the master. Downloading from a platform by
script is against its terms and nothing here does it. No file, no run.

## 10. The system page is updated by hand

`system.html` explains what every tool is for and how they fit together. It is
built from `datasets/system.json`, which is written, not scanned. Change a
tool, change that file, rebuild with `node build_system_page.mjs`. Never edit
`system.html` directly.
