# What not to cut

The tool finds removable time. This is the list of times it is wrong, gathered
from cuts that were made and then corrected.

## Air before a payoff

A pause before the best line in the clip is the line's setup. It reads as
weight, not as dead space, and the tool cannot tell the difference: it sees the
same silence either way.

**Check every removal that sits within about two seconds of the clip's payoff.**
On the three phone takes of 2026-08-29 the tool proposed trimming 1.22s of
silence at 62.78 in v1, which sits directly after "truly frictionless", the line
the whole take is built toward. Taking it makes the ending sound rushed.

## Repetition that is delivery

"me me me me me and take take take take take" is rhetoric with pauses inside it.
Three detected gaps in that block were skipped deliberately on the
`pillage-and-extract` cut. Nothing in the energy map distinguishes it from a
stumble.

The test is whether the repetition is doing work in the argument. If it is, the
pauses are part of it.

## A "like" that introduces an example

`FILLER_PATTERNS` includes `like`, because most of the time it is a hedge. In v2
at 22.82, "frictionless experiences **like** moving from I must operate my
computer to I can prompt my computer", it is introducing the example that makes
the abstract claim concrete. Cutting it strands the example.

The silence-on-both-sides condition removes most of these before they are ever
proposed, because a meaningful "like" is usually spoken continuously with what
follows it. It does not remove all of them.

## The first pause after a hard claim

A hook that lands and then sits for a beat is doing what a hook does. Tightening
the beat out of it is the most common way a tightened clip ends up worse than the
one it replaced, because every individual removal was defensible and the sum was
not.

## An "And" that is carrying a turn

Most sentence-initial "And"s are removable. Some are the join in a two-part
thought: "And at the same time, what is able to be done is..." depends on the
"And" to signal the reversal. Read the sentence with the word gone before
accepting the removal.

## What the tool has no opinion about

- **How many jump cuts the piece can carry.** Every accepted removal in camera
  mode is a visible cut. A locked-off talk tolerates few. A handheld phone reel
  is built out of them. `selection.md`'s "only pauses over about 1.5s in camera
  mode" was set against locked-off talk footage and is much too conservative for
  social vertical.
- **Whether the result is still the same argument.** Removals are local, and
  meaning is not. Read the tightened transcript end to end before rendering.

## The check that catches all of it

**Re-transcribe the tightened cut and diff it against the intended words.** A
splice that ate a consonant does not show up in the waveform, in the removal
list, or in a proof frame. It shows up when the words come back different.
