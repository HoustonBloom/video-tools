# Writing the proposal, step 2 of the loop

The proposal is the document the human decides from. It is the only step where a
bad idea is cheap, so it is worth writing properly.

This file is what it has to be. Every rule below came from an earlier version
being rejected, and names the thing that was wrong.

## It is a document, not a cut list

**Write it for somebody who was not in the room.** They should finish it knowing
what the episode was about, what the good parts were, and why. Somebody who did
attend already knows all of that, so writing for them produces a document that is
useless to everyone else and only marginally useful to them.

**Do not address the human directly.** No "you asked the room", no "your own
line". The person deciding is not the subject of the recording, and even when
they are in it, second person turns a record into a note. Third person
throughout.

**One sentence at the top, then the time breakdown.** Not paragraphs. The
sentence says what the thing is; the breakdown below it says what happened, in
order, with the prose folded into its rows. See "One control, not three prose
blocks".

**Then the featured segments, then the series, then the other clips, then the
rest of the moments.** Evaluate what the recording is, then derive what could be
cut. A document that opens on a cut list has skipped the part where anybody
decides whether the material is worth cutting.

## Never put a name on a quote

**This is the rule that has been broken most.** Two attributions in one episode
were wrong, both were caught only by pulling a frame at the timecode, and one of
them turned a common adjective into a person's name and then held it against her.

A transcript gives words, not speakers. Diarisation is not run here. A run of
show does not settle it either, because a show that runs ahead of its schedule
breaks the mapping between a planned slot and a position in the file.

So, in the proposal:

- **Quotes carry no name unless a document supports one.** Otherwise locate them
  by segment, which is a fact about the file: "in the audience block", "late in
  the second interview".
- **Describe what a passage is about**, not who said it. The subject is what a
  reader needs to judge whether it is worth cutting.
- **Attribution happens at the render step**, from the picture, and it goes in
  the prompt as an instruction rather than in the proposal as a claim.

## Names come from documents, never from the tape

Get them from the show's own records rather than from listening: the run of show
sheet, the email announcing the stream, the registration list. Those carry the
correct spellings, which is what titles, descriptions and captions need.

**A name goes on the page only where a document supports it, and it goes next to
the person, not in a roster section.** On one show the run of show assigns the
two featured slots and each founder states their company in the recording, so
company to person is a document match. Those two are named. The couch and the
audience are on no document, so their quotes carry no name.

**Do not write an explanation of that split onto the page.** Name who you can
name, leave the rest unattributed, and put the reasoning in the config.

## Highlights are themes, clips are operations

Two different sections doing two different jobs.

| Section | Job | Contains |
| --- | --- | --- |
| Highlights | What the recording is about | A theme, where it sits, what it covers, the quotes, why it is worth cutting |
| Clips | What to make from it | Spans, beats, runtime, costs, holds, and a prompt |

A clip points back at the highlight it came from. That way somebody can read the
top half and understand the episode, or the bottom half and go make something,
and neither half repeats the other.

## Duration first, timecodes last

Source timecodes mean nothing to a person deciding what to make. They led on the
first version and read as the content.

- Lead each clip with **how long it runs**.
- Say **where it sits in plain language**, not in timecode.
- Put the raw timecodes in the smallest type on the page. They matter to the
  render step and to nobody else.

## Give every clip a prompt that can leave the page

The proposal proposes. The work happens in whatever tool the reader uses next, so
each clip carries a prompt they can take there.

- **Generate the prompt from the same config** that renders the sheet, so a
  prompt cannot disagree with the proposal above it.
- **It has to stand alone.** Name the source file, the spans, what to read first,
  and the rules that are easy to get wrong. It will land somewhere with no page
  around it.
- **Include the attribution instruction in every prompt.** Work out who is
  speaking from the picture. Do not take a name from the transcript, and do not
  infer one from the run of show.
- **A text box, and a second button that appends it.** The reader will want to
  change something, and making them retype the whole prompt to do it is how the
  prompt stops being used.

Nothing is submitted anywhere. See `_publishing/copy-out-not-submit.md` in the
workspace for the pattern and the clipboard mechanics, including the fallback for
a page opened from disk, where the clipboard API is usually refused.

## What the proposal still owes

- **A refusal, when there is one.** The passage that looks most postable and
  should not be cut is worth its own section. On one episode it was a method
  whose arithmetic did not close.
- **Holds, per passage, with severity.** Whether each one is inside a proposed
  clip or not.
- **What is not in hand.** A beat with no span yet is a real proposal as long as
  it says so.

## Propose the featured segments first

If the episode has featured founders, guests or headliners, their clips come
before anything else. They are the reason the episode exists and they are the
people most likely to post what they are sent.

Each one needs four things, and none of them is a transcript dump:

| | What it is |
| --- | --- |
| What the thing is | In their own words, one quote, the plainest description they give |
| The vision | What they are building towards, not what it does today |
| The interesting part | The one turn of thought worth stealing. An inversion, a refusal, a number that should not be true |
| Why they built it | The origin, where they give one |

Then one proposed clip built from those, with its prompt.

## Caveats belong in the config, not on the page

An earlier version of this frame opened with a block explaining that speaker
identity was not established, followed by a section on which names the documents
did and did not cover. That is a page documenting the writer's confusion, and
nobody asked for one. The rule generalises. Uncertainty about method is the
pipeline's business. It goes in three places:

- **the config**, as the reason a field is shaped the way it is,
- **the generated prompt**, where the person cutting will meet it at the moment
  it matters,
- **the feedback log**, kept outside the repo, so it costs once.

It goes on the page only when it changes what the reader does next, and then it
sits next to that decision rather than in a preamble.

## One control, not three prose blocks

A synopsis in paragraphs, a narrative walk-through and a planned-against-actual
table all describe the same recording. Collapse them into a **time breakdown**:
one row per segment showing its duration, its name, a bar scaled to the longest
segment, and where it starts, with the description folded into the row.

The bar is the point. It shows the shape of the episode before a word is read,
and it makes an overrun or an unplanned segment obvious. Keep it on narrow
screens by wrapping it to its own line rather than hiding it.
