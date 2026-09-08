# tighten

**Shortens a take without changing what it says.** Dead air, long pauses,
disfluencies, filler. Nothing is chosen, reordered or rewritten.

For when a clip is right but slow.

```bash
pip install -r requirements.txt          # plus ffmpeg and ffprobe on PATH
```

**It only proposes a removal where both cut points land inside measured
silence.** Transcript timings are wrong by tens of milliseconds and will slice
the middle of a word, so nothing here trusts them.

**Every candidate is a candidate, not an edit.** A short burst the transcript
renders nothing for is a disfluency *or* a word the transcriber dropped. Measured
on one set of footage: five candidates, four of them real words, one an "um", and
one of the four a negation. Read them before applying them.

`SKILL.md` has the run order and what each script measures.
