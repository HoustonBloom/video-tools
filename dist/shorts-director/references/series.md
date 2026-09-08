# One question, many answers

Most of this skill assumes one clip cut from one speaker. A room does something
else sometimes: somebody asks a question out loud and several people answer it in
turn. That is not one clip with a hard choice about whose answer to use. It is a
**series**, and cutting it as a single Short throws away most of what happened.

From one episode. The host asked the room "does anyone else feel motivated by
spite?" and five people answered over about nine
minutes. Cut as one Short that is four people discarded.

## The shape

**Every clip opens on the same question, then hands to one person.** Then one
more clip puts the answers together.

| Clip | What is in it |
| --- | --- |
| One per responder | The question, then that person's answer, cut to its own build and payoff |
| One montage | The question, then one line from each responder |

Five responders means six clips off one question.

## Why it is worth the extra renders

**Each person gets a clip that is about them.** They post it because it is theirs,
and the show travels with it. This is the same mechanic as the featured founder
clip, extended to everyone who spoke, and it is the reason the couch seat already
includes a clip.

**The repeated question is the format.** Same four seconds at the head of every
clip, different answer underneath. The second one somebody sees is recognisable
as belonging to the first. A series is a thing people can follow; a clip is not.

**The montage is the only one that shows the room.** Five people answering the
same question in sequence is evidence that the room works. No single answer
carries that.

**None of this is measured on this footage.** The reasoning above is
structural, not a result. The instrument that would settle it is the retention
and share graph on a posted series against a posted single.

## Cutting the question once

The question is one span, cut once, reused at the head of all six. Practical
consequences:

- Get its cut points right once and every clip in the set inherits them.
- It must stand alone. Nobody hearing it has heard what came before, so if the
  question leans on a previous sentence, extend it until it does not.
- Keep the asker's voice on it. A question in the room's own audio is what makes
  the clip feel like a place rather than a format.

## The three forms

A plan should say which one it is, because the rules differ.

| `form` | Shape | Beat contract |
| --- | --- | --- |
| `build` | The default. One argument assembled from two to four spans | One hook, up to two builds, payoff last. Enforced |
| `answer` | Shared question, then one person | The question is the hook. The person's spans supply the rest. Payoff still last |
| `montage` | Shared question, then one line each | **No build contract.** One head, then N bodies, one per person |

`answer` fits the existing contract as it stands: treat the shared question as
the hook and give the responder up to two builds and a payoff.

**`montage` does not fit, and `build_short.py` will refuse it.** It sees one
opener, five middles and no proper close, which is exactly the failure the
contract exists to catch. Here it is a false positive: five answers to one
question is a legitimate shape and the contract was written before it existed.

Until the tool knows the form, a montage has to be assembled by hand, and that is
worth saying out loud in the proposal rather than discovering at render time.

## Ordering a montage

Chronological by default, because it is a record of a conversation.

**The exception is the last slot.** A montage has to end on the strongest line in
it, and the strongest line is rarely the one that happened to be spoken last. On
that set, one founder answered fourth and his is the only line that lands on
a claim about somebody other than the speaker, so he goes last.

Moving a person's answer changes the order the room heard, across speakers rather
than within one. That is a bigger reorder than the usual one and it gets proposed
explicitly, never done quietly.

## What to check before proposing a series

- **Attribute every answer against the picture, not the transcript.** A
  transcript gives you words, not who said them, and a room handing a microphone
  around defeats every guess. On that episode two attributions were wrong on the
  first pass and both were caught by pulling a frame at the timecode. Putting the
  wrong founder's name on a clip is the worst error this skill can make, because
  it is public and it is about a person.
- **Re-transcribe each answer at higher accuracy.** The answers are short, they
  are what the clip is, and a full-episode pass is not good enough to quote from.
- **Check every answer separately for holds.** They are different people saying
  different things. One answer being unpublishable does not hold the others, and
  one answer being fine does not clear the set. On that episode, one of five needed
  the speaker's sign-off and the other four did not.
- **Look for the shorter safe version.** Where an answer carries a hold, there is
  often a later span in the same answer that makes a claim entirely about the
  speaker's own work. That version needs nothing from anybody.

## Spotting one in the tape

The signal is a question addressed to the room rather than to a person, followed
by more than one person taking the microphone. In a transcript it looks like a
question, then a name-free stretch where the register keeps changing.

Audience blocks and open-floor segments are where these live. On that episode the
audience block was not on the run of show at all, ran about nine minutes, and
produced the best material in the episode.
