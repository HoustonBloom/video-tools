---
name: loudness
description: Measure a render's loudness, and correct it until it lands on target. Use when a cut is too quiet or too loud, when a delivery target names a LUFS figure, or before handing over any render. One loudnorm pass does not land on target; it caps its gain at the true-peak ceiling and reports success anyway, so this measures the output and corrects until it is right.
---

# Loudness

Measure a file, and correct it until it lands on target.

Works on any video or audio file. Nothing in it knows about a project.

Needs `ffmpeg` and `ffprobe` on PATH.

## The one thing to know

**One `loudnorm` pass does not land on target.** It caps its gain at the
true-peak ceiling and then reports success, so the log says it worked and the
file is still wrong. Measured against a -14 LUFS target on real footage:

| What was run | Result |
|---|---|
| One pass at TP -2.0 | -15.0 LUFS. Fails. |
| One pass at TP -2.0, different file | -14.5 LUFS. Fails. |
| TP -3.0, then a linear +0.5 dB | -14.0 LUFS. Passes. |

So the two jobs are separated. `loudnorm` gets the shape and leaves headroom, a
plain linear gain closes the distance, and the result is measured rather than
assumed. If it still misses after two corrections, the tool throws instead of
writing a file that fails verification in somebody else's hands.


## Running it

```bash
node loudness/scripts/loudness.mjs measure IN.mp4
node loudness/scripts/loudness.mjs normalise IN.mp4 OUT.mp4
node loudness/scripts/loudness.mjs normalise IN.mp4 OUT.mp4 --target -16 --tp -2.0
```

`measure` reports integrated loudness, true peak, range and threshold, and
changes nothing.

`normalise` writes a new file. It refuses if the input and output paths match,
because normalising in place destroys the original, and it never deletes the
file it was handed.

Video is copied, not re-encoded. Only the audio is touched.

## As a module

```js
import { measure, normalise } from "../video-tools/loudness/scripts/loudness.mjs";

const r = normalise(raw, out, { target: -14, tp: -3.0, cleanup: true });
// { before, after, peak, passes }
```

`cleanup: true` removes the input after a successful landing. Pass it only for an
intermediate your own code created. It is deliberately not on the command line.

## Defaults, and why

**-14 LUFS** is the target most platforms normalise toward, so a file already at
-14 is left alone rather than turned down on upload.

**TP -3.0** rather than -2.0. Asking for more headroom than the check requires is
what makes the second pass land: at -2.0 the output came back at -0.9 dBFS and
failed a headroom check that wanted -1.0 or lower.

**Tolerance 0.3 dB.** Tighter than that and the loop chases noise.

## What this does not do

It does not tell you whether the cut is any good, whether a splice ate a
consonant, or whether the audio and video are the same length. That last one is
`tighten/scripts/verify_cut.py`, which should run on anything before it is
handed over.
