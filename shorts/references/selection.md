# Choosing the span, and writing the cut

The editing is the easy half. Picking the forty seconds is the job.

## The test a build has to pass

Read the build's transcript with nothing around it. It ships only if all five hold.

1. **It makes one claim, and finishes it.** Two claims is a worse clip than
   either claim alone. A claim with its reasoning missing is a slogan.
2. **It does not reach outside itself.** No "as I mentioned", no "this slide",
   no pronoun whose antecedent is three minutes upstream. In a Q&A span, the
   question has to be audible or restated, or the answer is orphaned.
3. **The first line is a claim.** Not a greeting, not a credential, not a
   throat clear.
4. **The last line lands.** It resolves. A clip that stops because the span ran
   out reads as an accident.
5. **Nothing in it is on hold.** Check the cut index for per clip warnings.
   Employment status, unannounced partners, figures from someone else's slide,
   and anything about an open claim or application are the recurring ones.

## Open on the claim

In a talk the quotable line arrives *after* the reasoning, because the speaker
is earning it. A Short inverts that: the claim goes first and the reasoning
becomes the payoff.

This is settled house practice, not a suggestion. The Instagram cut
`IG_01_pillage-and-extract_coldopen_110x.mp4` opens frame one on "which is
pillage and extract while the system collapses", and the plane and film setup
that used to open it now lands around five seconds in. The earlier tight cut,
which spent its first four seconds on setup, was deprecated on 2026-08-12.

Reordering is cheap when captions are burned in, because the caption travels
with its own frames. A segment moved to the front carries its text with it.

What it costs: reordering changes the speaker's delivery order. That is the
speaker's call, so propose it, do not do it silently.

## Ending

The last word spoken should be the last word in the clip, followed by roughly
0.5s of clean air. Two failure modes, both seen and both fixed on
`pillage-and-extract`:

- **Cutting too tight.** Ending 0.12s after the last word reads as clipped.
- **Leaving a mumble.** Quiet fragments after the final word that the captions
  do not carry read as an unresolved cut off, even when the level is corrected.
  Cut them. The caption is the record of what was said; audio the caption does
  not carry is not part of the clip.

## A Short is a build, not a clip

**This is the correction that matters.** The first storyboard produced from this
skill proposed eight single sentences, and it was rejected on sight. The failure
was picking lines instead of moments, and it came from taking the unit of
analysis from a cut index that had cut quote cards for a different purpose.

A Short that works has four beats, and it usually needs **two to four spans from
different points in the tape** to get them:

| Beat | Job | Length |
| --- | --- | --- |
| **Hook** | Open an information gap. A claim, a refusal, a number that should not be true. Not a greeting, not setup. | 0 to 3s |
| **Build** | The tension the hook implies. The felt cost, the objection, the question being answered. | 3 to 6s, then as needed |
| **Payoff** | The resolution. What the hook promised, delivered. | to the end |
| **Loop** | Land on a reframe rather than a conclusion, so the viewer goes back to check the hook. | last beat |

Content with a clear narrative structure gets **two to three times the completion
rate** of content without one, and completion is what the Shorts algorithm
weights most heavily.

**Invert the talk.** In a talk the quotable line arrives after the reasoning,
because the speaker is earning it. Shorts want the opposite: start with the
payoff, then show how you got there. A cold open on the answer, with the question
revealed after, is stronger than the order it was said in.

**Splices are cheap where the frame is static.** In slide mode a join between two
points ten minutes apart is invisible, which is what makes a build possible at
all. In camera mode a join reads as a jump cut, so builds there want fewer,
longer spans.

## The plan is a contract

**The single most expensive mistake made with this skill so far: a build was
approved with three beats and rendered with four.** The extra segment was added
during the render, to reach a length band. It ran 0:10 to 0:16, and that is
exactly where the viewer said she stopped watching. The deviation was the defect.

Three rules follow, and the first two are enforced by `build_short.py` rather
than trusted:

1. **Every segment declares its beat.** `hook`, `build`, `payoff`, or `landing`.
   One hook, the payoff last, no more than two builds. A segment that cannot be
   named as a beat is a segment nobody chose. The build refuses a plan that
   fails this.
2. **Do not add a beat after approval.** If the build needs something the sheet
   did not propose, that is a new proposal, not an edit. Go back to step 2.
3. **Length is an outcome, not a target.** Never add material to reach a band.
   A build that lands short is telling you something true: either it is a quote
   card rather than a Short, or a beat is missing. In the case above
   both were true, and the missing beat was the payoff, which had been cut off
   four seconds early.

## The payoff has to be a claim

A clip that ends on a question has not made a point. The same build ended on
"what if I gave you all the timestamps...?" and the viewer's note was "you never
make a point". The declarative line was four seconds past the out point:
"so it becomes more like proof of action that is anonymized."

**When you cannot find the claim, the span is wrong, not too short.** Look
further along the tape before looking for filler.

## Length

**30 to 60 seconds.** An Inflow Network study of 5,400 Shorts found that band
earned nearly **22 times more views than clips under 10 seconds**.

| Band | Completion | Use |
| --- | --- | --- |
| Under 10s | high | **Almost no reach.** A stitch or a quote card, not a post |
| 10 to 30s | 70 to 85% | One moment with a single turn |
| **30 to 60s** | **50 to 65%** | **The default. An argument with a build and a payoff** |
| 60 to 120s | 30 to 45% | Only with something happening on screen |
| 120s to 3:00 | 15 to 25% | A demo, or a story with real stakes |

The trade is completion against reach: a 20 second Short at 90% completion can be
beaten by a 50 second one at 60%, because the second is watched by far more
people. Do not optimise completion by making things short.

**The first three seconds decide it.** 50 to 60% of the viewers who leave do so
inside them. Intro retention above 70% is the bar. Script the opening line
word for word rather than trusting a span boundary to land it.

**None of this is measured on this footage.** These are published figures
from other people's data. The instrument that would settle any of it is the
retention graph on a posted Short, and until one exists these are defaults with
reasons, not results.

## Cutting inside the span

**This section is a summary. The tightening pass is its own skill now**, at
`../../tighten/`, with a measuring tool that finds these cases instead of
leaving them to be spotted by ear: `tighten/scripts/find_tightening.py`. The
rules below are kept because they are the source the tool was built from, and
because they are what a reader of this file needs in hand. Where the two
disagree, the skill is newer.

Once the span is chosen, the tightening rules from the existing cut records apply:

- Remove pauses inside slide mode freely. The frame is static, so the splice is
  invisible.
- In camera mode remove only long pauses, over about 1.5s. Splices there read as
  visible jump cuts. **This number was set against locked-off talk footage and
  is far too conservative for handheld phone-selfie social cuts**, where the jump
  cut is the idiom rather than a defect. On the three phone takes of 2026-08-29 a
  0.55s threshold was used instead.
- Repetition that is delivery is not stutter. "me me me and take take take" keeps
  its pauses; three detected gaps inside that block were deliberately skipped.
- Disfluencies do not appear in a faster-whisper transcript, so searching the
  transcript for "um" returns zero no matter how many are in the audio. Find them
  by looking for short bursts at speech level isolated by silence on both sides,
  then checking whether the word level transcript renders anything there. Nothing
  transcribed means a disfluency.
- Resume a splice about 70ms before a word onset. Landing exactly on the onset
  clips the attack, which turns "my driving problem" into "a driving problem".

## Writing the plan

The plan is the deliverable of this stage, and it is what gets approved.

```json
{
  "source": ".../SOURCE.mp4",
  "output": ".../20260828_short_regeneration-vs-extraction.mp4",
  "profile": { "inset": [0,452,432,678], "slide": [460,90,1920,935], "bg": "0x2E173D" },
  "segments": [
    {"in": 1690.20, "out": 1704.60, "mode": "camera", "crop_x": 1306,
     "why": "the claim, cold"},
    {"in": 1660.00, "out": 1689.10, "mode": "slide", "layout": "solo",
     "why": "the reasoning, on the slide it belongs to"}
  ],
  "captions": ".../burned.ass"
}
```

Carry a `why` on every segment. A plan that cannot say why a segment is there
is a plan that has not chosen anything.
