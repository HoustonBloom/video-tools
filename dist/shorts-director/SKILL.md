---
name: shorts-director
description: Cut vertical Shorts out of long-form talk footage. Use when the ask is to make Shorts, Reels, TikToks or vertical clips from a recorded talk, panel, interview, podcast or episode; to find the moments worth cutting; to reframe 16:9 footage for mobile; or to fix a vertical clip that is framed wrong. Runs a three step loop: a cut proposal sheet the human decides from, then a plan, then a render that is measured rather than eyeballed.
---

# Shorts director

Turn a long recording into vertical clips that survive being watched on a phone,
muted, by someone who did not ask to see them.

Needs `ffmpeg` and `ffprobe` on PATH, plus `pip install -r requirements.txt`
(numpy, opencv-python-headless, faster-whisper).

## The loop

**Three steps, and the human decides at step 2.**

| Step | What | Who |
| --- | --- | --- |
| 1 | The prompt. What the footage is and what it is for. | Human |
| 2 | **A cut proposal sheet.** Candidates as hook, build, payoff, with verbatim quotes and verdicts. Nothing rendered. | You propose, human decides |
| 3 | A plan per approved Short, then captions, render, verify. | You |

Step 2 exists because a bad idea is cheap there and expensive anywhere else.
The first storyboard this skill produced was rejected on sight for proposing
eight single sentences, and that cost minutes instead of a render.

**This is the compositional pass: it chooses and orders.** Shortening a span that
has already been chosen is a different job with different rules, and it lives in
the `tightening-pass` skill at `../tighten/`. Run this one first, because it
reads the original timeline and tightening invalidates every timecode it
produced. Step 3 below is where the two meet.

## 1. Choose the moments

Full detail in `references/selection.md`. The short version:

- **A Short is a build, not a clip.** Hook, build, payoff. Usually two to four
  spans from different points in the tape.
- **The hook is a claim, a refusal, or a number that should not be true.** Never
  setup. Roughly half the viewers who leave do so in the first three seconds.
- **The payoff is a claim, not a question.** A clip that ends on "what if...?"
  has not made a point.
- **30 to 60 seconds**, and length is an outcome rather than a target. Never add
  material to reach a band. See the contract below.
- **Walk `references/patterns.md` before choosing anything.** Ten recurring
  shapes, each owing a known set of clips, plus three that look cuttable and are
  not. Reading a transcript for good lines finds whatever you happen to notice;
  walking the catalogue finds what the episode owes. The check is to put the
  proposed clips on the segment timeline: a segment that owes clips and produced
  none is the finding.
- **A question asked to a room is a series, not a clip.** If several people
  answered one question, cut one clip per answer, each opening on the same
  question, plus one montage. Five responders is six clips. Cutting it as a
  single Short discards four people. Full detail in `references/series.md`,
  including the montage that the beat contract below currently refuses.
- **Look for tension.** Someone refusing the obvious thing, someone under
  challenge and not moving, a reaction. Not a summary.

**Read the source's own cut index or show notes if it has one, for the quotes
and for anything held from publication.** Those records often carry holds that
are invisible in the footage. But do not take their clip boundaries as your
units: they were usually cut as quote cards for a different purpose, and
inheriting that unit is how you end up proposing single sentences.

## 2. Write the proposal sheet

**Full rules in `references/proposal-frame.md`.** The short version, all of it
learned by getting it wrong:

- **Write it for somebody who was not in the room**, in the third person.
  Synopsis first, then the narrative, then the highlights, then the clips.
- **Never put a name on a quote.** A transcript gives words, not speakers.
  Attribution happens at the render step, from the picture.
- **Names come from documents**, a run of show or an email, never from listening.
  Say which people the documents do not cover.
- **Duration first, timecodes in the smallest type on the page.**
- **Every clip carries a prompt that can leave the page**, generated from the
  same config, plus a box for an edit. Nothing is submitted anywhere.

The narrative of the source, then each candidate broken into its beats with the
verbatim quote and source timecode, what it costs, and a verdict.

**Say what is not yet in hand.** A build that needs a span nobody has cut is a
real proposal as long as it says so. Writing around the gap makes the sheet
useless.

Nothing is rendered here. The human names the numbers.

## 3. Execute

### The plan is a contract

Every segment declares a `beat`: `hook`, `build`, `payoff` or `landing`.
`build_short.py` refuses a plan with no hook, no payoff, a payoff that is not
last, or more than two builds.

**This is enforced because of a specific failure.** A build approved with three
beats was rendered with four; the extra one was added during the render to reach
a length band, and it ran 0:10 to 0:16, exactly where the viewer stopped
watching. **If the render needs something the sheet did not propose, that is a
new proposal, not an edit.**

### Find the cut points against the waveform

```bash
python scripts/find_edges.py SOURCE.mp4 --start 1986 --end 2016 --min-gap 0.30
```

**Never take cut points from transcript timings.** They are wrong by tens of
milliseconds and will slice a word. Enter and leave on a gap's midpoint; to land,
cut on the gap's end so the air belongs to your clip.

### Know which composition each span is in

```bash
python scripts/analyze_source.py SOURCE.mp4 --scan --start 1170 --end 1500
python scripts/analyze_source.py SOURCE.mp4 --start 1200 --end 1208
```

Classify per segment, never per clip. Camera mode takes a 9:16 crop at full
frame height aimed at the speaker. A composite where a slide fills the frame must
never take a centre crop: it halves the slide and drops the camera inset. See
`references/framing.md` for the two layouts and how to measure a new source.

**When a layout choice is open, render both and let the human pick from the
result rather than from a description.**

### Caption, render, verify

```bash
python scripts/make_captions.py PLAN.json --out cut.ass --review cut.captions.md
python scripts/build_short.py PLAN.json --proof 0 --at 2.0 --out proof.png
python scripts/build_short.py PLAN.json
python scripts/verify_short.py OUT.mp4
```

**Correct the captions before burning.** Transcription runs about 90% word
accurate on talk footage and is non-deterministic: two passes over one span
disagreed about whether a sentence was there. `--review` lists everything under
the confidence floor.

**Add `"tail_hold": 0.45`** unless the span already ends on 0.3s or more of quiet.
Most do not.

**Look at the proof frame.** It is the only check that catches a filter graph
that returned success and produced an empty panel.

## Porting to a new source

Everything source-specific lives in one profile JSON: the composite geometry and
the canvas colour. `references/worked-example.md` is a full one with every number
measured and the method for each. To set up a new source:

1. `analyze_source.py --scan` over a stretch, to see how many compositions it has.
2. For a slide composite, measure the inset and slide rectangles **against the
   backdrop, not from motion**. Motion bounds clip static regions and overrun
   into background. The check is aspect ratio: a camera inset should come out at
   or very near 16:9.
3. Write them into a profile and reference it from every plan.

## What this will not do

- **Invent a number.** The retention and length figures in the references are
  published studies of other people's data. The instrument that would settle any
  of them is the retention graph on a posted Short.
- **Trust a render because it returned zero.** A clip can play perfectly with no
  audio stream; captions can sit 6px into the UI; a checker can report a good
  landing as a failure. All three happened. Measure.
- **Post anything.** It writes files. Publishing is the human's, per action.
