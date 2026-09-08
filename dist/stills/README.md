# stills

**Photographs out of a recording.** Three steps, each runnable alone: pick which
moments are worth a frame, reframe each to a feed shape with one crop per person
in shot, render a page to choose from.

For when you need images from footage and do not want to scrub for them.

```bash
pip install -r requirements.txt          # plus ffmpeg and ffprobe on PATH
python scripts/pick_stills.py --video IN.mp4 --out DIR --label "Name" --count 20
python scripts/crop_stills.py --root DIR
python scripts/build_sheet.py --root DIR --title "Contact sheet"
```

**Cut from the master, not from a delivered copy.** A high bitrate on a
second-generation crop is a generous encoder rather than detail. `SKILL.md`
carries the ffprobe line for checking which you have.

**There is no face detection.** OpenCV 5 dropped `CascadeClassifier` and ships no
cascade files, so subject location here is motion. A crop is `a`, `b`, `c` left
to right and nobody is named. It shortlists; a person looks at every frame. On
one real run, 22 of 180 shortlisted frames were rejected, every one by eye.
