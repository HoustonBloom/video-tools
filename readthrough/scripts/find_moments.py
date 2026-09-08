#!/usr/bin/env python3
"""Captions in, every moment worth knowing about out.

    python find_moments.py CAPTIONS.vtt --out moments.json

A moment is a point in the recording where something known happens. The kinds
live in moment_kinds.py, one row each, and adding a kind is adding a row. This
reports every kind it finds and says plainly which kinds it found none of.

WHY EVERY KIND. A pass that reads one kind, the host handing over, returns
nothing at all on a recording with none, and a conversation format has no
handoffs while it does have sponsor thank-yous, questions to the room and the
show describing itself. Reading every kind reports what is in a recording
rather than what is in one format.

STRETCHES. A kind marked `bounds` can open a stretch of the recording, and the
stretches partition it. A recording with no bounding moment gets one stretch,
which is the whole thing, and the moments still land inside it.

NAMES. Every name is a reading of a quotation and travels beside the sentence it
was read from. Nothing here knows who is speaking.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from moment_kinds import KINDS, BY_ID as KINDS_BY, read_name  # noqa: E402

OPENERS = {
    "and", "but", "so", "or", "then", "it", "he", "she", "they", "them", "that",
    "this", "those", "these", "there", "which", "who", "because", "also", "well",
    "yeah", "yes", "no", "okay", "ok", "uh", "um", "i",
}
GREETING = re.compile(
    r"\b(thank you|thanks for|thanks so much|welcome|good evening|good morning|"
    r"give it up|round of applause|nice to (meet|see)|glad to be|happy to be|"
    r"my name is|i'm here to|excited to be)\b", re.I)
REACHES_OUT = re.compile(
    r"\b(as i (mentioned|said)|like i said|as we (discussed|talked)|this slide|"
    r"that one|earlier|back there|as you (saw|heard)|the previous)\b", re.I)
DISFLUENCY = re.compile(r"\b(uh|um|erm|uhh|umm)\b", re.I)
HAS_SUBSTANCE = re.compile(
    r"(\d|\b(is|are|was|were|can|will|should|need|means|makes|takes|costs|grows|"
    r"want|keep|becomes|turns|matters|works|happens)\b)", re.I)

TS = re.compile(r"(\d\d):(\d\d):(\d\d)[.,](\d+)\s+-->")


def hms(s):
    s = int(round(s))
    return "%d:%02d:%02d" % (s // 3600, (s % 3600) // 60, s % 60)


def read_vtt(path):
    raw = Path(path).read_text(encoding="utf-8", errors="replace")
    out, seen, when = [], set(), None
    for block in re.split(r"\n\s*\n", raw):
        m = TS.search(block)
        if m:
            h, mi, s, frac = m.groups()
            when = int(h) * 3600 + int(mi) * 60 + int(s) + float("0." + frac)
        if when is None:
            continue
        body = block[block.index("\n") + 1:] if "\n" in block else ""
        for line in body.splitlines():
            line = re.sub(r"<[^>]+>", "", line)
            line = re.sub(r"&gt;&gt;|&gt;|>>", " ", line)
            line = re.sub(r"&amp;", "&", line)
            line = re.sub(r"\s+", " ", line).strip()
            if not line or TS.search(line) or line in seen:
                continue
            seen.add(line)
            out.append((when, line))
    return out


def sentences(lines, cap=40):
    """Caption lines break mid-sentence, so rejoin and split on terminators.

    `cap` is the escape hatch and it is the difference between the two recordings
    this was measured on. One transcript is punctuated and splits at 10.3
    sentences a minute. The other has almost no full stops and split at 4.4,
    which is not longer sentences but 200-word run-ons: a match for a sponsor or
    a name landed somewhere inside a wall of text and the sentence reported back
    was useless. Past `cap` words with no terminator in sight, break at the
    caption boundary, which is where the transcriber heard a pause."""
    out, buf, start = [], "", None
    for t, line in lines:
        if start is None:
            start = t
        buf = (buf + " " + line).strip()
        while True:
            m = re.search(r"[.?!]+(\s|$)", buf)
            if not m:
                break
            sent, buf = buf[: m.end()].strip(), buf[m.end():].strip()
            if sent:
                out.append((start, sent))
            start = t
        if len(buf.split()) >= cap:
            out.append((start, buf.strip()))
            buf, start = "", t
    if buf:
        out.append((start or 0.0, buf))
    return out


def excerpt(sentence, lo, hi, pad=110):
    """The matched phrase in context, not the whole sentence it landed in.

    A poorly punctuated transcript yields long runs, and reporting the run put
    the match 200 characters from the start of the line shown. Three of ten
    moments on one recording read as false positives for that reason alone, and one
    of them was a correct sponsor match nobody could see."""
    a = max(0, lo - pad)
    b = min(len(sentence), hi + pad)
    while a > 0 and sentence[a] not in " \t":
        a -= 1
    while b < len(sentence) and sentence[b] not in " \t":
        b += 1
    return (("... " if a > 0 else "") + sentence[a:b].strip()
            + (" ..." if b < len(sentence) else ""))


def find_moments(sents, min_gap):
    """Every kind, over every sentence. Two of the same kind inside one window
    collapse to the one that reads a name, else to the earlier."""
    found = []
    for kind in KINDS:
        hits = []
        for t, s in sents:
            m = kind["pattern"].search(s)
            if not m:
                continue
            nm = read_name(s, kind["names"])
            h = {"kind": kind["id"], "label": kind["label"], "at_s": round(t, 2),
                 "at": hms(t), "said": excerpt(s, m.start(), m.end()),
                 "matched": s[m.start():m.end()],
                 "name_read": nm, "bounds": kind["bounds"]}
            if hits and h["at_s"] - hits[-1]["at_s"] < kind.get("gap", min_gap):
                if nm and not hits[-1]["name_read"]:
                    hits[-1] = h
                continue
            hits.append(h)
        # One person announced twice reads as two moments.
        merged = []
        for h in hits:
            if merged and h["name_read"] and merged[-1]["name_read"] == h["name_read"]:
                continue
            merged.append(h)
        found += merged
    found.sort(key=lambda h: h["at_s"])
    return found


def score_line(text, words, since_start):
    if since_start < 30:
        return False, 0
    if text.rstrip().endswith("?") or GREETING.search(text) or REACHES_OUT.search(text):
        return False, 0
    if re.sub(r"[^\w']", "", text.split()[0]).lower() in OPENERS:
        return False, 0
    if not HAS_SUBSTANCE.search(text):
        return False, 0
    disf = len(DISFLUENCY.findall(text))
    if disf > 1:
        return False, 0
    score = (2 if disf == 0 else 0)
    score += 2 if re.search(r"\d", text) else 0
    score += 1 if 12 <= words <= 40 else 0
    score += 1 if re.search(r"\b[A-Z][a-z]{2,}", text[1:]) else 0
    return True, score


def candidates(sents, lo, hi, min_words):
    out = []
    for t, s in sents:
        if not (lo <= t < hi):
            continue
        w = s.split()
        if len(w) < min_words or not re.search(r"[.?!]$", s):
            continue
        keep, score = score_line(s, len(w), t - lo)
        if keep:
            out.append({"at_s": round(t, 2), "at": hms(t), "words": len(w),
                        "score": score, "text": s})
    out.sort(key=lambda c: (-c["score"], c["at_s"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("captions")
    ap.add_argument("--out", default="moments.json")
    ap.add_argument("--min-gap", type=float, default=120.0)
    ap.add_argument("--min-words", type=int, default=12)
    a = ap.parse_args()

    lines = read_vtt(a.captions)
    if not lines:
        print("No caption lines read from " + a.captions, file=sys.stderr)
        return 1
    sents = sentences(lines)
    moments = find_moments(sents, a.min_gap)
    end = max(t for t, _ in sents)
    start = min(t for t, _ in sents)

    # The gap rule runs per kind, so two different bounding kinds can fire
    # seconds apart and cut a sliver. One recording opened a stretch at 2:09 on
    # "give yourself a quick introduction" and another at 2:12 on the answer to
    # it, leaving a three second stretch with nothing in it. A bounding moment
    # inside the gap of the last one folds into it, and a named one wins.
    # An opening stretch, from the first caption to the first bounding moment.
    # Without it, everything before the first introduction is in no stretch and
    # the page drops it in silence. On a talk that opens with a guest, the first
    # bound can land 46 minutes in, and everything before it would be gone. It
    # carries no opened_by, so the page names it "The opening".
    def gap(m):
        return KINDS_BY[m["kind"]].get("gap", a.min_gap)

    bounds = []
    for m in [x for x in moments if x["bounds"]]:
        if bounds and m["at_s"] - bounds[-1]["at_s"] < min(gap(m), gap(bounds[-1])):
            if m["name_read"] and not bounds[-1]["name_read"]:
                m = dict(m, at_s=bounds[-1]["at_s"], at=bounds[-1]["at"])
                bounds[-1] = m
            continue
        bounds.append(m)
    stretches = []
    if bounds and bounds[0]["at_s"] - start > a.min_gap:
        lo, hi = start, bounds[0]["at_s"]
        stretches.append({
            "n": 1, "in": round(lo, 2), "out": round(hi, 2), "dur_s": round(hi - lo, 2),
            "at": hms(lo), "opened_by": None,
            "sentences": sum(1 for t, _ in sents if lo <= t < hi),
            "candidates": candidates(sents, lo, hi, a.min_words)[:12],
            "moments": [{k: m[k] for k in ("kind", "label", "at", "said", "name_read")}
                        for m in moments if lo <= m["at_s"] < hi],
        })
    if bounds:
        for i, b in enumerate(bounds):
            lo = b["at_s"]
            hi = bounds[i + 1]["at_s"] if i + 1 < len(bounds) else end
            stretches.append({
                "n": len(stretches) + 1, "in": lo, "out": round(hi, 2), "dur_s": round(hi - lo, 2),
                "at": b["at"], "opened_by": {k: b[k] for k in ("kind", "label", "said", "name_read")},
                "sentences": sum(1 for t, _ in sents if lo <= t < hi),
                "candidates": candidates(sents, lo, hi, a.min_words)[:12],
                "moments": [{k: m[k] for k in ("kind", "label", "at", "said", "name_read")}
                            for m in moments if lo <= m["at_s"] < hi and m is not b],
            })
    else:
        stretches.append({
            "n": 1, "in": round(start, 2), "out": round(end, 2), "dur_s": round(end - start, 2),
            "at": hms(start), "opened_by": None,
            "sentences": len(sents),
            "candidates": candidates(sents, start, end, a.min_words)[:12],
            "moments": [{k: m[k] for k in ("kind", "label", "at", "said", "name_read")} for m in moments],
        })

    counts = {k["id"]: sum(1 for m in moments if m["kind"] == k["id"]) for k in KINDS}
    doc = {
        "schema": "readthrough-moments/v1",
        "captions": str(a.captions),
        "caption_lines": len(lines),
        "sentences": len(sents),
        "runs_to_s": round(end, 2),
        "settings": {"min_gap_s": a.min_gap, "min_words": a.min_words},
        "counts": counts,
        "kinds_absent": [k for k, v in counts.items() if v == 0],
        "_read_this_first": [
            "A moment is a point where something known happens. The kinds are rows in moment_kinds.py.",
            "`name_read` is a reading of the sentence beside it, never a fact about who is speaking. Check it against the picture.",
            "Every time is a caption timing. It locates a passage and cannot place a cut.",
            "A kind with a count of zero was looked for and not found. It is not an error.",
        ],
        "moments": moments,
        "stretches": stretches,
    }
    Path(a.out).write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")

    print("read     %d caption lines, %d sentences, runs to %s" % (len(lines), len(sents), hms(end)))
    print("moments  %d across %d kinds" % (len(moments), sum(1 for v in counts.values() if v)))
    for k in KINDS:
        n = counts[k["id"]]
        print("  %-14s %3d  %s" % (k["id"], n, "" if n else "none found"))
    print("stretches %d%s" % (len(stretches), "" if bounds else "  (nothing bounds this recording, so one stretch is the whole thing)"))
    print("wrote    " + a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
