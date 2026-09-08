# Delivery

## Targets

| | Value | Why |
| --- | --- | --- |
| Canvas | 1080x1920, H.264, yuv420p | Shorts standard. Anything square or taller counts as a Short |
| Frame rate | 30fps | Matches the source. Do not resample |
| Duration ceiling | 3:00 | YouTube's cutoff for Shorts |
| Loudness | -14 LUFS integrated | Where YouTube normalises, so hitting it means no gain change on upload |
| True peak | -1.5 dBTP | Headroom for the lossy encode YouTube applies after |
| Loudness range | under about 12 LU, nearer 2 to 5 for speech | Flatter than natural speech, deliberately, for phone speakers |

## The audio chain

The source recording sits about 20 dB below any delivery target, and lifting it
without correction brings up room rumble and leaves it muffled. This chain was
measured against the LinkedIn and YouTube cuts:

```
highpass=f=75
afftdn=nr=6:nf=-45:tn=1
acompressor=threshold=-24dB:ratio=2.5:attack=20:release=250
loudnorm=I=-14:TP=-1.5:LRA=11
```

**Hold the denoiser at 6 dB.** At 10 dB it softens consonants enough to change
words: "We had platforms" re-transcribed as "If you had platforms".

If a clip sounds muffled rather than quiet, measure the spectrum before reaching
for the denoiser. On the Instagram cut the fault was a 13.3 dB hole between 2400
and 4800 Hz, exactly where consonants carry, against a 41 dB speech to noise
floor. That is corrective EQ, not a noise problem, and denoising it would have
made it worse.

## Assembly

Cut each segment to its own file, then concatenate. A single `filter_complex`
over all spans never finishes, because each `trim` rescans the whole source.

Fast-seek with an 8 second keyframe lead before the cut point, then trim
precisely.

**Concatenate through MPEG-TS**, not the concat demuxer directly. On the YouTube
feature cut the demuxer produced 193 consecutive non-monotonic DTS frames where
re-encoded pieces met stream-copied ones. Timebases matched, so that was not the
cause. Remuxing every segment to TS and joining through the concat protocol
cleared all 193.

## Verifying

```bash
python scripts/verify_short.py OUT.mp4
```

Measures dimensions, Shorts eligibility, loudness, true peak, loudness range,
and the length of air after the last sound.

Two things it does not measure, both still required:

- **Re-transcribe the finished file and compare against the captions.** This is
  how clipped consonants at splices get caught, and it has caught them: "my
  driving problem" decoded as "a driving problem", "stop becoming the product"
  as "I'll be coming the product". Both were splices resuming exactly on a word
  onset. Backing the resume point up 70ms fixed them.
- **Look at a proof frame.** Safe area and crop aim are visual, and the checker
  reports canvas size, not whether the speaker is in the crop.

Transcription needs temperature fallback and a repetition penalty on this
footage. Without them it loops and repeats one word about 110 times across the
"me me me" block. It also returns nothing at all on source-level audio, around
-34 dBFS, so normalise to about -16 LUFS before transcribing anything, and it
emits phantom trailing fragments on clips ending in silence. Settle anything
ambiguous against the waveform at 20ms, not against the model.

## Captions

```bash
python scripts/make_captions.py PLAN.json --out cut.ass --review cut.captions.md
```

Burned, positioned clear of the Shorts UI, two lines maximum, breaking on real
pauses rather than on a word count so a cue lines up with a spoken phrase.

**Measure the burn, do not look at it.** Checking a captioned frame for white
pixels finds the lamp, the wall and a light shirt. Diff a captioned frame
against an uncaptioned render of the same timestamp; the difference is the
caption and nothing else. That is how the first version was caught sitting 6px
past the safe line, because `MarginV` positions the text box and the outline
draws outside it.

**Correct before burning.** About 90% word accurate at the `small` model here.
`--review` lists every word under the confidence floor and those are the ones
to check. Machine transcription also mishears proper nouns.

## Naming and filing

Follow the existing convention:

```
YYYYMMDD_<platform>_<form>_<slug>.mp4
20260827_youtube_full-feature_talk-title.mp4
20260827_linkedin_clip_overview.mp4
```

Write a `.md` beside every cut that ships, carrying the edit decision list, what
was removed and why, the measured audio numbers, and an `Open` section for what
is not done. Every existing cut has one. The one shipping file that does not is
`IG_01_pillage-and-extract_coldopen_110x.mp4`, and the gap is visible.

Superseded versions move to a `_deprecated/` folder beside the repo, outside it, with a `(superseded YYYY-MM-DD)`
suffix. Nothing is deleted.
