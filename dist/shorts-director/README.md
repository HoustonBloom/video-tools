# shorts

**Long-form 16:9 talk footage in, a vertical 1080x1920 Short out.** The
compositional pass: it chooses what to cut and what order to put it in.

For when you have an hour of talk footage and want forty seconds of it that
stands on its own.

```bash
pip install -r requirements.txt          # plus ffmpeg and ffprobe on PATH
python scripts/analyze_source.py SOURCE.mp4 --scan --start 1170 --end 1500
python scripts/build_short.py plans/my-cut.json --proof 0 --at 2.0 --out proof.png
python scripts/build_short.py plans/my-cut.json
python scripts/verify_short.py renders/my-cut.mp4
```

**The plan is the deliverable, not the render.** Every framing and cutting
decision lives in one JSON file naming its source, its segments and its reasons.
A clip whose plan is lost is a clip nobody can explain.

**Proof frame before film.** Render one still and look at it. That is the only
check that catches a filter graph returning success over an empty panel, which
has happened.

`SKILL.md` is the workflow and `references/` is the craft: what makes a span
worth cutting, how each shot mode reframes, delivery targets, and the checks.
