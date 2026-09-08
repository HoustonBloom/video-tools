"""
Step one of three. Captions in, speaker turns out. No video, no model.

    python read_turns.py CAPTIONS.vtt --out turns.json

Reads YouTube rolling captions in WebVTT. They carry a time on every word and
a ">>" wherever the captioner heard the speaker change. This writes every word
with its time, grouped into turns at those markers. That is the whole job.

This is the cheapest reading of a recording there is: who spoke when, as far
as the captioner could tell, without saying who. A summary sheet, a question
finder, or anything else that wants turns reads this file and does not have to
parse captions again.

Runs alone. Design for sufficiency: a community that wants only this should
pay only for this.
"""

import argparse
import html
import json
import os
import re
import sys

TIME = re.compile(r"(\d+):(\d\d):(\d\d)\.(\d{3})")
TAG = re.compile(r"<(\d+:\d\d:\d\d\.\d{3})>")


def t2s(m):
    h, mi, s, ms = m.groups()
    return int(h) * 3600 + int(mi) * 60 + int(s) + int(ms) / 1000.0


def hms(s):
    s = max(0, s)
    h, r = divmod(int(s), 3600)
    m, x = divmod(r, 60)
    return (f"{h}:{m:02d}:{x:02d}" if h else f"{m}:{x:02d}")


def words_from_vtt(path):
    """Every word once, with its time and whether a speaker change precedes it.

    The rolling format repeats each line: once bare, once with word tags. Only
    the tagged lines carry new words, so those are the ones read. The first
    token of a tagged line has no tag of its own and takes the cue start."""
    out = []
    cue_start = None
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.rstrip("\n")
            hdr = TIME.match(line)
            if hdr and "-->" in line:
                cue_start = t2s(hdr)
                continue
            if cue_start is None or "<c>" not in line:
                continue
            pieces = TAG.split(line)
            times = [cue_start] + [t2s(TIME.match(t)) for t in pieces[1::2]]
            texts = pieces[0::2]
            for t, chunk in zip(times, texts):
                chunk = re.sub(r"</?c>", "", chunk)
                chunk = html.unescape(chunk)
                new_speaker = ">>" in chunk
                chunk = chunk.replace(">>", " ")
                for w in chunk.split():
                    out.append({"t": round(t, 3), "w": w, "turn": new_speaker})
                    new_speaker = False
    return out


def turns_from_words(words):
    """Split at speaker markers. A turn ends where the next begins, or 0.6s
    after its last word when there is no next; never more than 2s after."""
    turns, cur = [], None
    for w in words:
        if w["turn"] or cur is None:
            if cur:
                turns.append(cur)
            cur = {"start": w["t"], "words": []}
        cur["words"].append({"t": w["t"], "w": w["w"]})
    if cur:
        turns.append(cur)
    for i, t in enumerate(turns):
        nxt = turns[i + 1]["start"] if i + 1 < len(turns) else t["words"][-1]["t"] + 0.6
        t["end"] = round(min(nxt, t["words"][-1]["t"] + 2.0), 3)
        t["text"] = " ".join(x["w"] for x in t["words"])
        t["dur"] = round(t["end"] - t["start"], 2)
        t["n_words"] = len(t["words"])
        t["at"] = hms(t["start"])
    return turns


def read(vtt):
    words = words_from_vtt(vtt)
    turns = turns_from_words(words)
    return {
        "schema": "shorts-turns/v1",
        "captions": vtt,
        "words": len(words),
        "speaker_markers": sum(1 for w in words if w["turn"]),
        "turns": turns,
        "_note": "A turn is where the captioner heard a new voice. It says someone else, never who."
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("vtt")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = read(a.vtt)
    if not d["words"]:
        print("no word-timed cues found. This reads YouTube rolling captions with <c> tags.", file=sys.stderr)
        return 1
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    print(f"{d['words']} words, {len(d['turns'])} turns from {d['speaker_markers']} speaker markers -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
