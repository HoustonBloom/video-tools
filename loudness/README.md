# loudness

**Measures a render's loudness and corrects it until it lands on target.** Works
on any video or audio file. Nothing in it knows about a project.

For before you hand over any render, and for when a cut is too quiet or too loud.

```bash
node scripts/loudness.mjs               # needs node, ffmpeg and ffprobe on PATH
```

**One `loudnorm` pass does not land on target.** It caps its gain at the
true-peak ceiling and then reports success, so the log says it worked and the
file is still wrong. So this measures the output and corrects until it is right,
rather than trusting the first pass.

Measured on this machine, one pass against a -16 LUFS target landed at -19.2.

`SKILL.md` has the targets and the measured table.
