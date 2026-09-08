---
name: tightening-pass
description: Shorten a talking-head take without changing what it says. Use when the ask is to tighten a clip, cut the ums and filler, remove dead air or long pauses, make a cut shorter or punchier, or get a take under a length limit. This is the pass that removes; the compositional pass, shorts-director, is the one that chooses and orders. Runs a measuring tool that only proposes a removal when both of its cut points land inside measured silence.
---

# Tightening pass

Take a clip that says the right thing and make it say it in less time.

**This pass never changes what the clip says.** It does not choose a span, does
not reorder, does not decide what the piece is about. If the ask involves
picking moments, sequencing beats, or building a hook, that is the compositional
pass and it lives in `shorts-director`. Do that one first.

Needs `ffmpeg` and `ffprobe` on PATH, plus numpy.

## The one rule

**A removal is only proposed when both of its cut points land inside measured
silence.**

Everything else follows from this. Transcript word timings are not cut points:
on this footage they drift, always early, by up to half a second, and a cut
placed off a transcript turned "my driving problem" into "a driving problem".
The transcript says *what* was said. The waveform says *where* to cut.

The energy map is the same 20ms measurement `find_edges.py` uses, at the same
relative threshold, so the two tools never disagree about where silence is.

## What it removes

| Kind | What it is | How it is found |
| --- | --- | --- |
| `head` / `tail` | Dead air before the first word and after the last | Speech bounds off the energy map |
| `pause` | Silence between phrases longer than the clip needs | Any gap over `--max-pause`, trimmed to `--keep-pause` |
| `disfluency` | An "um" or "uh" | A burst at speech level, bounded by silence, that the word-level transcript renders **nothing** for |
| `filler` | "And so", "I think that", "you know", a hedging "like" | Word match, then required to have silence on both sides |

**The disfluency rule exists because faster-whisper does not transcribe
disfluencies.** Grepping a transcript for "um" returns zero no matter how many
are in the audio. The only way to find one is to look for a burst of speech-level
energy that the transcript is silent about. Nothing transcribed there means a
disfluency, or it means the transcriber dropped a real word, which is why every
one is a candidate rather than an edit.

## Running it

```bash
python scripts/find_tightening.py SOURCE.mp4 --transcript words.json
python scripts/find_tightening.py SOURCE.mp4 --transcript words.json --json plan.json
```

Without `--transcript` it still finds air and disfluencies; it cannot find filler,
because filler is a word-level judgement. The transcript wants word timestamps,
which is `word_timestamps=True` on the faster-whisper call.

Knobs worth knowing, in the order they matter:

| Flag | Default | What moves |
| --- | --- | --- |
| `--keep-pause` | 0.30 | Air left where a pause is trimmed. Lower is tighter and more clipped |
| `--max-pause` | 0.55 | Pauses longer than this get proposed. Raise it to only take the worst |
| `--keep-tail` | 0.45 | Air after the last word. A landing wants 0.3s or more |
| `--burst-min` | 0.08 | Below this an untranscribed burst is threshold noise, not an um |
| `--despeckle` | 0.06 | Silences closer together than this are one silence |

**`--despeckle` is load-bearing and was added after a real failure.** A single
20ms frame crossing the threshold inside a 2.4s silence split it into two short
ones. The pause rule then stopped seeing a long pause, and the disfluency rule
reported a "0.02s burst" as an um. Both symptoms had the same cause, and both
went away when adjacent silences were bridged first.

## What it cannot decide

Hand these back to the human every time. The tool marks them; it does not resolve
them.

- **Repetition that is delivery is not stutter.** "me me me and take take take"
  keeps its pauses. Three detected gaps inside that block were deliberately
  skipped on a previous cut. The measurement cannot tell rhetoric from a stumble.
- **A meaningful "like" reads exactly like a hedging one.** "like moving from I
  must operate my computer" is an example being introduced, not filler. The
  silence-on-both-sides condition catches most of the difference and not all of
  it.
- **How many jump cuts the piece can carry.** In camera mode a splice is visible.
  A locked-off talk tolerates few; a handheld selfie reel is built out of them
  and the idiom expects it. `selection.md` says remove only pauses over about
  1.5s in camera mode, and that number was set against locked-off talk footage.
  For phone-selfie social cuts it is far too conservative. **Say which of the two
  you are in before setting `--max-pause`.**
- **Whether a pause is doing work.** Air before a payoff is not dead space. Check
  the removals that sit immediately before the clip's best line.

## Order against the compositional pass

**Compose first, tighten second.** The compositional pass reads the original
timeline, so tightening before it invalidates every timecode it produced, and
tightening a span that gets discarded is wasted work.

Two legitimate shapes:

1. **Inside a chosen span.** The normal case. Run the compositional pass, get
   approved spans, then tighten within each one. This is step 3 of
   `shorts-director`, and this skill is the detail behind its "cutting inside
   the span" rules.
2. **On a whole take.** When the take *is* the clip and nothing is being
   composed, run this alone. Say which one you are doing, because the numbers
   are not interchangeable.

**If tightening happens first for any reason, every downstream timecode has to
be recomputed against the tightened file.** Do not carry old numbers across.

## What this will not do

- **Apply anything.** It writes a proposal. The removals are candidates a human
  accepts or rejects, one at a time.
- **Claim it found every um.** Across three phone takes it found one, in 270
  seconds of speech. Either the speaker rarely says them or the detector's
  window is too narrow. **The instrument that would settle it is a human
  listening pass against the burst list**, and until one has run, "no
  disfluencies found" means the detector found none, not that there are none.
- **Guess a number.** Every duration and threshold in its output came off the
  file.
