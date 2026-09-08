---
name: stills
description: Pull the frames worth keeping out of any video, reframe them for a feed, and render a page to pick from. Use when somebody wants photographs out of a recording, stills for social, a thumbnail, a poster frame, or a contact sheet of what is in a long file. Chooses when to cut by measurement and where to crop by movement, then hands a person a page to judge, because nothing here can see a blink.
---

# Stills

Three steps, each runnable alone on the file the one before it wrote.

| Step | Script | Answers |
|---|---|---|
| 1 | `pick_stills.py` | **When.** Which moments in this video are worth a picture |
| 2 | `crop_stills.py` | **Where.** How to reframe one of those to a feed shape, per subject |
| 3 | `build_sheet.py` | **Which.** One page holding all of them, to pick from |

Nothing in any of them knows about a programme or a person. Step 2
opens the video again; steps 1 and 3 are the only ones that have to.

Needs `ffmpeg` and `ffprobe` on PATH, and `requirements.txt`.

## The one thing to know

**This shortlists. It does not judge.** There is no face detection: OpenCV 5.0
dropped `CascadeClassifier` and ships no cascade files. So nothing here sees a blink,
a half-formed word, a back of a head, or who is in the shot.

Measured on one real run of 180 shortlisted frames: **22 were rejected, every
one of them by eye and not one by a measurement.** They were inserted slides,
people cut off at the frame edge, and heads down.

So the output of step 1 is a pile to look through, and step 3 exists to make
looking cheap. Do not skip it.

## Cut from the best copy, and check which that is

The frame can only be as good as the file. Before pulling anything, compare the
sources by video bitrate rather than by which one is easiest to reach:

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,bit_rate \
  -show_entries format=duration -of default=nw=1 FILE.mp4
```

Measured on one set of files, all of them 1920x1080, all of them plausible-looking:

| | Video bitrate |
|---|---|
| The master | 20.9 Mbit/s |
| Delivered clips cut from it | 4.0 to 4.7 Mbit/s |
| Pipeline re-encodes | 2.2 to 3.1 Mbit/s |
| Vertical finals | 6.0 to 6.9 Mbit/s, and they are crops of the row above, encoded again |

A high bitrate on a second-generation crop is not detail, it is a generous
encoder. Follow the file back to the master.

## Running it

```bash
python stills/scripts/pick_stills.py --video IN.mp4 --out DIR --label "Name" --count 20
python stills/scripts/crop_stills.py --manifest "DIR/Name.stills.json" --out CROPDIR --aspect 4:5
python stills/scripts/build_sheet.py --root PARENT --title "Stills"
```

Working on one span rather than a whole file, which is how you get a set per
person when you know where their segment is:

```bash
python stills/scripts/pick_stills.py --video IN.mp4 --out DIR --label "Second slot" \
  --from 1305 --to 2298 --count 18 --every 3 --min-gap 35
```

`--keep-graphics` keeps inserted slides and screen shares, which are dropped by
default. `--centre-only` on the crop step skips subject location. `--height-frac`
below 1 frames tighter and costs resolution, which the manifest records.

The manifest also lists `graphics_at_s`, the source seconds of every sampled
frame the graphics test flagged, kept or not, and `samples`, one row per sampled
frame with its time, sharpness, motion and subject fraction. The count alone
cannot say whether 157 flagged frames were one slide section or 157 title cards;
the times can. And a moving screen share is not a graphic to this test, since
the test reads still: what marks it is that nobody is in the frame, which
`subject_frac` says. A reader works both out from the rows.

Measured on one 1:37 recording with a long slide section: 153 of 974 sampled
frames were dropped as graphics, and all 14 that came back were camera frames
of the room. The test errs toward keeping, which is the safe direction: a slide
that survives is one more frame to look at, and a camera frame wrongly dropped
is gone without being seen.

## Where the crops come from

Subject location is **not written here.** It is `shorts/scripts/analyze_source.py`,
which already does it and was measured when it was built. `crop_stills.py`
imports `motion_map` and `column_regions` from it rather than keeping a second
copy that can drift. The one thing not imported is `classify_mode`, which keys on
one programme's on-screen graphics.

On a locked-off camera the background does not move, so accumulated frame
difference marks the people. `column_regions` returns **every** band that clears
the floor, so a two-shot gives two crops and a couch gives as many as it has
movers.

**Taking the single hottest column instead does not work.** Across a ninety
second introduction it picks whoever fidgets most, who is not always the person
speaking, and a folder named for one person would hold pictures of another.

**The band midpoint does not work either.** A person gesturing throws a band
wider than their body on the side the arm goes. On a two-shot the midpoint put
the speaker hard against the frame edge with a lamp filling the middle. The crop
follows the energy-weighted centroid of the band, which sits on the body.

## Nobody is named

A crop is `a`, `b`, `c`, left to right. Which one holds who is for a person to
see. Nothing here identifies anybody, and a wide of a six-person couch holds five
people who are not the one speaking.

If a folder is named for a person, that name has to come from a document that
says where their segment is, never from looking at a face.

## Defaults, and why

**`--every 3`** for sampling. Denser buys little: adjacent frames of a talking
head measure almost identically and get thrown away by the duplicate check.

**`--min-gap 25`** between picks. Without it the top twenty scores cluster in
whichever thirty seconds were best lit.

**Seek, not decode, over five minutes.** An input seek lands on a keyframe, so it
costs about 0.4 seconds per sample and stays flat with depth into the file. That
is what makes a 15 GB master workable; decoding straight through would read
every frame to keep one in ninety.

**Full frame height by default.** Losing headroom looks worse than losing width,
which is the same call `analyze_source.crop_9x16` makes.

**Never upscaled.** A 4:5 crop of 1080p is 864x1080, and the manifest says so. A
tool that quietly upscaled to hit 1080x1350 would be reporting resolution it does
not have.

## What this does not do

It does not tell you whether a frame is any good, who is in it, or whether the
eyes are open. It does not crop to a face. It does not caption, and it writes no
text onto a picture.

It also does not choose. Steps 1 and 2 narrow a two-hour recording to a page;
step 3 is where a person decides, and that step has no script.
