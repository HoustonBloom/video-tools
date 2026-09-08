# readthrough

**One page that says what is in a recording.** The show as a timeline, every
segment with who and what, the guest and the featured people with a frame and
their words, every moment found with a filter per kind, and a cut prompt for
each part. One file, opens by double-clicking, no server.

For when somebody hands over a long video and wants to know what is in it
without watching it, or before choosing clips from footage nobody has read.

```bash
python scripts/run.py --captions C.vtt --video IN.mp4 --out-dir DIR --title "..."
```

Needs Python and Node. ffmpeg if you want frames. Captions come from the
platform (YouTube Studio, Zoom, Teams) or from `../transcribe/`.

## Four steps, one of them yours

| Step | In | Out |
|---|---|---|
| `find_moments.py` | captions | `moments.json`: every phrase-matched moment, by kind |
| **the read** | the whole transcript, read by the agent | `segments.json`: who was up, when, what they said |
| `pick_turn_stills.py` | video plus either JSON | one frame per segment |
| `build_readthrough.mjs` | all of the above | **`readthrough.html`** |

`run.py` runs the three scripts and, when `segments.json` is missing, prints
the prompt for the read, builds the page anyway, and the page says at the top
that the recording has not been read. Do the read, then rebuild:

```bash
node scripts/build_readthrough.mjs DIR
```

**Why the read is a step.** The scripts match phrases. A host who introduces a
guest in words the list does not carry produces no boundary, and the page
shows an hour as one card with nobody named. Reading the transcript against
the checklist in `SKILL.md` is what finds the guest, the featured people, the
demo, the sponsor, the round of names, the questions and the close.

## What is on the page

In order: a stamp saying when it was read; stat cards; the filters, every kind
looked for with its count, zeros included, click one to show only that kind;
the timeline, one block per segment and a tick per moment; the segment list;
the people, each with a frame, in and out, a lede and their words as quote
cards; every moment in order; every segment as a ranked card with the lines
that passed the test and a Copy button holding a prompt that cuts from it.

## What comes from the picture

The stills pass writes four numbers per sampled frame. **Slides on screen** are
runs of crisp still frames. **Screen only** is a run of frames with nobody in
shot that the slide test did not take: a screen capture, or the camera on the
screen; the page says which was measured and a person says which it was. Both
are named in and out on the card.

## What a moment is

A point where something known happens. The kinds are rows in
`scripts/moment_kinds.py`, and adding a kind is adding a row: someone
introduced, introduced themselves, asked to introduce, put to the room,
sponsor named, the recording describing itself, closing. A kind with a count
of zero was looked for and not found; the page shows it.

A name in `moments.json` is a reading of a sentence, never a fact about who
is speaking. A `who` in `segments.json` is the reader's, and marked known or
as heard.

## What a candidate line is

The mechanical half of the test in `../shorts/references/selection.md`: a
complete sentence at or above the word floor, not a greeting or a thank-you,
nothing reaching outside itself, not a question, at most one disfluency,
something asserted, at least 30 seconds past the boundary. Ranked, not
chronological. It proposes; a person chooses.

## Checking a change

```bash
python tests/run_tests.py
```

Fixtures are verbatim slices of real captions and do not ship. Cut a `.vtt`
slice of your own footage into `tests/fixtures/`, run once with `--accept` to
record what it finds, and from then on a pattern change that loses something
fails here in under two seconds. Read the diff before accepting.

## What it does not do

- It does not say who is speaking.
- It cannot place a cut. Every time is a caption timing and locates a passage;
  cut points are `../shorts/scripts/find_edges.py`.
- The scripts do not read. They match. The read is the agent's, every
  recording.
