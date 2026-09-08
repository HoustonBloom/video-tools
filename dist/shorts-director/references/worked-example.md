# A worked example

Every number here was measured on one real source: a 1:37:23 recording of a
founder talk show, one locked-off camera, 1920x1080.
None of it transfers to your footage. It is here because the *method* transfers,
and a method is easier to follow when you can see what its output looked like.

## What the source turned out to be

`analyze_source.py --scan` over the 31 minute segment returned nine runs and two
compositions:

| From | To | Mode | Length |
| --- | --- | --- | --- |
| 19:31 | 20:51 | camera | 80s |
| 20:51 | 26:51 | slide | 360s |
| 26:51 | 27:39 | **mislabelled** | 48s |
| 27:39 | 31:47 | slide | 248s |
| 31:47 | 32:27 | camera | 40s |
| 32:27 | 37:15 | slide | 288s |
| 37:15 | 47:39 | camera | 624s |
| 47:39 | 50:19 | slide | 160s |
| 50:19 | 50:35 | camera | 16s |

**The mislabelled row is the useful one.** That stretch is a full-screen screen
share of a live demo: no lower-third graphic, no two-shot, no camera inset. The
classifier is binary, so anything that is not the slide composite falls through
to camera, and it named a third composition as the one it least resembles.

Check the boundaries your scan produces against frames before trusting them. On
this source the scan disagreed with the show's own written index twice: once the
scan was right and the index's label was too coarse for an arc spanning both
compositions, and once the scan was wrong in the way above.

## The composite geometry

| | Value | How it was measured |
| --- | --- | --- |
| Camera inset | x 0 to 424, y 420 to 658 | White fraction across the inset columns drops 0.62 to 0.00 at y=420; last video column 423 |
| Lower-third bar top | y 935 | First row from which the rest of the frame is predominantly bar |
| Slide panel | x 460 to 1920, y 90 to 935 | Union of per-slide content boxes across four arcs |
| Canvas | black | Chosen, not sampled |

**The inset was measured wrong first, and the wrong method is instructive.**
Deriving it from motion bounds gave `[0, 452, 432, 678]`: it clipped 68px of
static wall off the top, where nobody moves, and ran 20px past the bottom of the
video into the white backdrop. Against a coloured canvas nobody could see it.
Against black there was an obvious white strip under the camera panel.

**The check that settles it is aspect ratio.** The corrected rect is 424 x 238,
which is 1.781, within 0.2% of 16:9. The motion-derived one was 1.912. A camera
inset that does not come out at its own aspect ratio has been measured wrong.

Two more traps from this source:

- **The slide panel cannot be detected directly.** The decorative border around
  it is static and full of line art, so edge density, saturation and
  non-backdrop masking all returned a box spanning the full frame width on three
  different arcs. It is derived from the inset position instead, erring outward,
  which never crops slide content.
- **A fixed dB floor does not travel.** The same recording measured -41.8 dB in
  one span and -38.7 dB sixty seconds later. A fixed -38 dB threshold found
  twelve gaps in the first and none in the second. `find_edges.py` uses a
  threshold relative to each region for this reason.

## Audio

The source sat about 20 dB below any delivery target and sounded muffled rather
than quiet. Measuring the spectrum found a 13.3 dB hole between 2400 and 4800 Hz,
exactly where consonants carry, against a 41 dB speech to noise floor. **That is
corrective EQ, not a noise problem, and denoising it would have made it worse.**

Hold a denoiser low. At 10 dB on this source it softened consonants enough to
change words: "We had platforms" re-transcribed as "If you had platforms".

## One finished Short

26.96s, three spans, two of them 60 seconds apart in the tape.

| Beat | Source | Runs |
| --- | --- | --- |
| Hook | 1991.71 to 2001.81 | 0:00 |
| Build | 2053.04 to 2064.80 | 0:10 |
| Payoff | 2069.03 to 2073.58 | 0:22 |
| Landing | 0.45s hold | 0:26.5 |

**Its first version was worse and the reasons are the point of this file.** It
ran 28.37s with a fourth segment between the build and the payoff, added during
the render to reach a length band. The viewer's note was "after second 15 you
lose me", and the added segment ran 0:10 to 0:16. It also ended on a question,
"what if I gave you all the timestamps...?", and her other note was "you never
make a point". The claim was four seconds past the out point and had been cut
off: "so it becomes more like proof of action that is anonymized."

Both failures are now refused by `build_short.py`, which will not build a plan
whose beats do not make a Short.
