---
name: readthrough
description: Read a whole recording and produce one HTML page saying what is in it, who was up and when, where the demo and the sponsor were, and what is worth cutting. Use when somebody hands over a long video and wants to know what is in it without watching it, or before choosing clips from footage nobody has read yet. It proposes and never chooses.
---

# Readthrough

Captions in, one page out: `readthrough.html`. The show as a timeline, every
segment with who and what, the guest and the featured people with a frame and
their words, every moment found with a filter per kind, and a cut prompt for
each part.

Needs Python and Node. ffmpeg if you want frames.

## The one thing to know

**Two reads make the page, and you are the second one.** The scripts match
phrases in the captions and are the same every time. They cannot find a guest
speaker or a featured founder unless the host used a phrase they already know.
You read the whole transcript against the checklist below and write
`segments.json`. The page is built from both. Without yours it still builds,
and it says at the top that the recording has not been read.

## Running it

```bash
python scripts/run.py --captions C.vtt --video IN.mp4 --out-dir DIR --title "..."
```

It starts from a file you were given, with captions from the platform or from
`../transcribe/`. Nothing here downloads from a platform.

| Step | In | Out |
|---|---|---|
| `find_moments.py` | captions | `moments.json` |
| **the read** | the whole transcript, and you | `segments.json` |
| `pick_turn_stills.py` | video plus either JSON | `turn-stills.json`, `segment-stills.json` |
| `build_readthrough.mjs` | everything above | **`readthrough.html`** |

When `segments.json` is missing, `run.py` prints the prompt for the read,
builds the page anyway, and the page carries the same prompt with a copy
button. Do the read, then rebuild:

```bash
node scripts/build_readthrough.mjs DIR
```

## The read, and the checklist

Read every caption line from the first to the last. Not the moments file, not
a search: the transcript, end to end. Then write `segments.json` beside it.

Look for every one of these, and when you find none, say so in the file:

- **The opening**, and who is introduced in it.
- **A guest speaker**: who, their company, what they talked about.
- **Each featured person**: who, their company, in and out, what they said,
  and the lines worth quoting with their times.
- **A demo**: who, in, out, what was on the screen. The page checks it against
  the picture and says whether the screen filled the frame there.
- **The sponsor**: who, and the sentence that named them.
- **The round of introductions**: every name, in order, with the company the
  captions heard.
- **Questions from the room**: each one, in a line.
- **The closing**: who, and what they asked the room to do.

Names are as the captions heard them unless you know them, and you say which.
Machine captions mishear names; read every one against the tape.

Every time is a caption timing. Find it in the caption file, do not estimate
it. A time locates a passage; a cut point comes off the waveform.

## The shape of segments.json

```json
{
  "schema": "readthrough-segments/v1",
  "title": "Recording title",
  "runs_to_s": 5828,
  "read": {"by": "an agent, reading the captions end to end", "on": "YYYY-MM-DD", "captions": "captions.vtt"},
  "segments": [
    {"id": "guest", "kind": "guest", "title": "Guest speaker", "who": "Guest Name", "who_known": false,
     "company": "Their Company", "in": 65, "out": 1136, "what": "one paragraph, what was said",
     "quotes": [{"at": 260, "text": "the line, verbatim"}],
     "marks": [{"at": 1084, "what": "something worth knowing is here"}]},
    {"id": "featured-1", "kind": "featured", "order": "first", "title": "Featured founder, first",
     "who": "Founder Name", "who_known": true, "company": "Their Company", "in": 1154, "out": 3035, "what": "...", "quotes": [], "marks": []}
  ],
  "demos": [{"in": 1606, "out": 1659, "who": "Founder Name", "what": "what was on the screen"}],
  "sponsor": {"at": 1138, "who": "Sponsor Name", "said": "the sentence"}
}
```

Segment `kind` is one of `opening`, `guest`, `featured`, `round`, `questions`,
`closing`, or anything else the recording needs. Segments do not overlap and
together they cover the recording. `guest` and `featured` get the person block
on the page, with a frame, the quotes as cards and the marks as a list.
Everything else gets a timeline block, a link and a ranked card.

## What the page shows

In order: the stamp saying when it was read, stat cards, the filters (every
kind looked for with its count, zeros included, click one to show only that
kind), the show timeline with one block per segment and a tick per moment, the
segment list, the people, every moment in order, then every segment as a ranked
card with the lines that passed the test and a Copy button holding a prompt
that cuts from it.

## What comes from the picture

The stills pass writes four numbers per sampled frame. Slides on screen are
runs of crisp still frames; "screen only" is a run of frames with nobody in
shot that the slide test did not take: a capture, or the camera on the screen.
Both are named in and out on the page. A stills manifest without those numbers
says so instead of guessing.

## What a candidate line is

The mechanical half of the test in `../shorts/references/selection.md`: a
complete sentence at or above the word floor, not a greeting or a thank-you,
nothing reaching outside itself, not a question, at most one disfluency,
something asserted, at least 30 seconds past the boundary. Ranked, not
chronological.

**It proposes and never chooses.** The other four parts of the test are
judgment and a person applies them.

## What it does not do

- **It does not say who is speaking.** A `name_read` in `moments.json` is a
  reading of a sentence. A `who` in `segments.json` is your reading of the
  transcript, and you mark whether it is known.
- **It cannot place a cut.** Cut points are `../shorts/scripts/find_edges.py`.
- **The scripts do not read.** They match. The read is yours, every recording.

## Checking a change

```bash
python tests/run_tests.py
```

Fixtures are verbatim slices of real captions and do not ship. Cut a `.vtt`
slice of your own footage into `tests/fixtures/`, run once with `--accept` to
record what it finds, and from then on a pattern change that loses something
fails here in under two seconds. Read the diff before accepting.
