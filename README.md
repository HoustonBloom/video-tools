# video-tools

Six tools that read and cut video. Each runs alone, on any video, from the
command line or through an AI agent that can run commands. No media lives here.

| Tool | What it does | In | Out |
|---|---|---|---|
| [`transcribe/`](transcribe/) | Makes a caption file from a recording that has none. | a video | a `.vtt` |
| [`readthrough/`](readthrough/) | Reads a whole recording and writes one page: who was up, when, what they said, where the demo was, and the lines worth cutting. | a video and its captions | `readthrough.html` |
| [`shorts/`](shorts/) | Cuts a vertical Short out of long-form talk footage, from a plan you approve first. | a video and a plan | a 1080x1920 render |
| [`tighten/`](tighten/) | Shortens a take without changing what it says: dead air, pauses, filler. | a clip | the same clip, shorter |
| [`stills/`](stills/) | Pulls the frames worth keeping, reframes them for a feed, and renders a page to pick from. | a video | pictures and `contact-sheet.html` |
| [`loudness/`](loudness/) | Measures a render's loudness and corrects it to a target. | any render | the same file, on target |

Each folder has a `README.md` for a person and a `SKILL.md` for an agent.

## Install

Python 3.12 or later, Node for the two page builders, and `ffmpeg` and
`ffprobe` on PATH.

```bash
pip install -r requirements.txt          # opencv and numpy
pip install -r transcribe/requirements.txt   # faster-whisper, only if you transcribe
```

Check: `ffmpeg -version` and `ffprobe -version` both answer.

## The front door

Most people want the readthrough. Put the video in a folder, then:

```bash
python transcribe/scripts/transcribe.py --video IN.mp4 --out captions.vtt   # if there are no captions
python readthrough/scripts/run.py --captions captions.vtt --video IN.mp4 --out-dir . --title "..."
```

It ends in `readthrough.html`, or exits non-zero. Part of that run is a read of
the transcript by the agent, against the checklist in `readthrough/SKILL.md`;
`run.py` prints the prompt for it.

## Packaging

```bash
python package.py              # every tool
python package.py stills       # one
python package.py --check      # gate only, write nothing
```

Each tool packages into `dist/<name>/` and `dist/<name>.zip`, self-contained,
with a `check_install.py` that reports what is missing. The gate refuses a
package that carries a path off the machine it was built on.

## What is not here

- **Captions are machine transcribed and need correcting.** Proper nouns are
  the least reliable part. Read names against the tape.
- **Nothing chooses.** The tools propose spans, frames and lines. A person
  decides.
- **No publishing.** These tools write files. Nothing uploads, posts or pushes.
- **No fetching from a platform.** A recording comes as a file from whoever
  owns it. Downloading from YouTube by script is against its terms and nothing
  here does it.
- **No face detection.** Nothing here knows who is in a frame.
- **No performance data.** Length and framing defaults are craft defaults with
  reasons, not measured optimums.

## License

See the repository's license file.
