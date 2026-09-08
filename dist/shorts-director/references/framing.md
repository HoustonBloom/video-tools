# Framing 16:9 talk footage for a phone

A 9:16 frame is 32% of the pixels of the 16:9 frame it came from. Something is
always thrown away. The whole job is choosing what.

## Classify per segment, never per clip

An edited talk alternates compositions, and the composition decides what
reframing is even possible. Classifying once for a whole clip is the single
most common way to produce an unwatchable Short.

`analyze_source.py` reports the mode from the lower-third graphic: present and
static means slide mode, absent means camera mode. Two tests, both required,
because a purple cushion on a couch passes the colour test and fails the static
one as soon as anyone moves in front of it.

Verified against the four arcs whose modes the cut index had already established
independently, from frames: B and D as slide, A and F as camera. Four for four.

## Locating the subject

Motion, not faces. OpenCV 5.0 dropped `CascadeClassifier` and ships no cascade
files, `FaceDetectorYN` needs ONNX weights that are not on this machine, and
fetching them needs a network connection.

Motion is the better locator here regardless. The camera is locked off, so the
background does not move and whatever does is a person. It finds someone turned
away from the lens, which a frontal face detector does not, and in slide mode it
finds the camera inset for free, because the slide is static and the inset is the
only thing changing.

Measured on a couch two-shot: two regions, one speaker at x 64 to 708 and the
other at x 1356 to 1864. Consistent across arcs A and F.

## Camera mode

Take a 9:16 window at **full frame height**, centred on the speaker, clamped
inside the frame. 608x1080 out of 1920x1080.

**Never crop the height.** Losing headroom reads as a mistake. Losing the sides
of a room shot does not, and nobody watching knows what was there.

- **Crop per segment.** A speaker's position in frame changes between segments,
  so one crop for the whole clip will drift off them.
- **Reframe on a speaker change, not mid sentence.** Cutting from a crop on one
  speaker to a crop on the other when the speaker changes reads as coverage, the way a two
  camera shoot would. The same reframe in the middle of one person's sentence
  reads as a mistake.
- **Do not follow a face frame by frame.** Continuous tracking on a locked-off
  shot looks like a phone gimbal. Hold a crop, and change it on a cut.

Cost, measured: 608 wide upscaled to 1080 is a **1.78x** blow-up. Unavoidable
when cropping 9:16 out of 16:9, and acceptable on this footage.

## Slide mode

**A centre crop is not an option.** It cuts the slide in half and drops the
camera inset, which sits on the left edge, entirely. Two layouts instead.

### stacked

Slide on top, camera inset scaled up underneath. This is the build the cut index
prescribed on 2026-08-06.

Use it when the viewer needs the speaker: a claim delivered to camera, anything
with a reaction in it, the opening of a clip where a face earns attention.

Cost, measured: the inset is 424px wide in the source, so filling 1080 is a
**2.5x** blow-up, against 1.78x for a camera-mode crop. It is soft. It is legible
at phone size, and it is the only camera angle slide mode has.

### solo

Slide on top, empty lower panel, no camera. The panel is for burned captions.

Use it when the slide is the argument, when the slide is dense enough to need
the height, or when the inset would be soft for long enough to notice.

**Which one is an art direction call, not a rule.** Render both proof frames and
look. The trade is a soft face against no face at all.

## Composite geometry

Slide mode geometry is fixed for a given edit, so measure it once per source and
put it in the plan's `profile`. Detecting the slide panel per frame does not
work: the decorative border around it is static and full of line art, so edge
density, saturation and non-backdrop masking all return a box spanning the full
frame width. Measured on arcs B, D and E1, all three returned x0=0, which is the
border, not the slide.

What does work is restricting the search to the columns right of the inset, and
bounding it above the lower-third bar.

Measured on one 1920x1080 source:

| | Value | How |
| --- | --- | --- |
| Camera inset | x 0 to 424, y 420 to 658 | White-backdrop edge detection. 424x238 is aspect 1.781, within 0.2% of 16:9, which is the check |
| Lower-third bar top | y 935 | First row from which the rest of the frame is predominantly bar |
| Slide panel | x 460 to 1920, y 90 to 935 | Union of per-slide content boxes across arcs B, D, E1, E2 |

The bar carries white text, which breaks a strict run of "is this row purple",
so the bar top is found by testing the tail rather than the run. Looking for the
last unbroken run returns 1028, which is below the text and 93px wrong.

Use one slide rect per source rather than per segment. Per-segment bounds are
measurable and correct, but the panel then changes size between slides, and the
layout jitters.

## Safe areas

The Shorts player puts title, channel and description across the bottom of the
frame and the action rail up the right side.

- Nothing that has to be read goes below **y 1660** of 1920.
- Keep text clear of the right **130px**.
- Panels are centred in the band between y 120 and y 1660, computed from the
  actual panel heights, so the layout adapts instead of assuming source geometry.

## Captions

Burn them. Shorts are watched muted, and auto-captions are off by default,
mispositioned, and wrong on domain words. The existing transcripts mishear
a product name, a surname and a company name.

Burned captions also make reordering cheap, because a segment carries its own
text wherever it is moved to.
