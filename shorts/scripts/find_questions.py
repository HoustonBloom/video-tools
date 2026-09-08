"""
Step two of three. Turns in, questions the room answered out. No video, no model.

    python find_questions.py turns.json --out questions.json
    python find_questions.py turns.json --out questions.json --any-question

Reads the turns file read_turns.py wrote. Finds a question put to the room and
takes the run of speaker turns after it as the answers. Writes the series it
found: the question span, each answer span, the short turns it skipped between
them, and why it decided each one was a question.

This is the step a community wants when they want the questions and nothing
else. It does not need the video and it does not write a plan.

WHAT IT DOES NOT DO. It names nobody: a turn is "someone else". It places no
cut: every time here is a caption timing and locates a passage, no more. It
does not decide: a run of turns after a question is a candidate, and a person
says whether it was one question and these were answers to it.

The room-only rule is the default because the first run without it, on a three
hour recording, proposed 17 series and 97 clips: every question to one person
followed by eight turns of conversation. A question to one person is a
conversation. A question to the room is what a series is made of.
"""

import argparse
import json
import os
import re
import sys

TO_ROOM = re.compile(
    r"\b(anyone|anybody|everyone|everybody|you all|y'?all|who here|how many of you|"
    r"raise your hand|show of hands|the room|does anybody|does anyone|has anyone|is anyone|"
    r"who else|anyone else|anybody else|who wants|who would)\b", re.I)
OPENER = re.compile(r"^(who|what|when|where|why|how|does|do|did|is|are|can|could|would|should|has|have|will)\b", re.I)


def hms(s):
    s = max(0, s)
    h, r = divmod(int(s), 3600)
    m, x = divmod(r, 60)
    return (f"{h}:{m:02d}:{x:02d}" if h else f"{m}:{x:02d}")


def sentences(turn):
    out, cur = [], []
    for w in turn["words"]:
        cur.append(w)
        if re.search(r"[.?!]$", w["w"]):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return [{"start": s[0]["t"], "end": s[-1]["t"], "text": " ".join(x["w"] for x in s)} for s in out]


def question_in(turn, room_only=True):
    """The last question sentence in a turn, if the room would answer it."""
    sents = sentences(turn)
    for i in range(len(sents) - 1, -1, -1):
        s = sents[i]
        text = s["text"]
        marked = text.endswith("?")
        room = bool(TO_ROOM.search(text))
        opener = bool(OPENER.match(text))
        if not (marked or (room and opener)):
            continue
        if room_only and not room:
            continue
        if not room and len(text.split()) < 5:
            continue
        span_start, text_out, why = s["start"], text, []
        if marked: why.append("ends with a question mark")
        if room: why.append("addressed to the room: " + TO_ROOM.search(text).group(0))
        if opener and not marked: why.append("interrogative opening")
        if s["end"] - s["start"] < 2.5 and i > 0:
            span_start = sents[i - 1]["start"]
            text_out = sents[i - 1]["text"] + " " + text
            why.append("under 2.5s alone, so the sentence before it is included")
        return {"in": round(span_start, 3), "out": round(s["end"], 3), "text": text_out, "why": why}
    return None


def find(turns, *, min_answer_s=6.0, min_answer_words=15, max_answers=6, max_answer_s=240.0, min_answers=2, room_only=True):
    series, i = [], 0
    while i < len(turns):
        q = question_in(turns[i], room_only)
        if not q:
            i += 1
            continue
        answers, skipped, j = [], [], i + 1
        while j < len(turns) and len(answers) < max_answers:
            t = turns[j]
            if question_in(t, room_only=True):
                break
            if t["dur"] > max_answer_s:
                break
            (answers if (t["dur"] >= min_answer_s and t["n_words"] >= min_answer_words) else skipped).append((j, t))
            j += 1
        if len(answers) >= min_answers:
            sid = f"q{len(series) + 1:02d}-{hms(q['in']).replace(':', '')}"
            series.append({
                "id": sid,
                "question": {
                    "dur_s": round(q["out"] - q["in"], 2), "in": q["in"], "out": q["out"],
                    "at": hms(q["in"]), "text": q["text"], "recognised_by": q["why"],
                    "asker_turn": i, "asker_turn_dur_s": turns[i]["dur"]
                },
                "answers": [{
                    "turn": n, "turn_index": j2, "dur_s": t["dur"], "in": t["start"], "out": t["end"],
                    "at": t["at"], "words": t["n_words"], "text": t["text"],
                    "attributed": None
                } for n, (j2, t) in enumerate(answers, 1)],
                "skipped_between": [{"turn_index": j2, "at": t["at"], "dur_s": t["dur"], "words": t["n_words"], "text": t["text"][:80]} for j2, t in skipped]
            })
            i = j
        else:
            i += 1
    return series


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("turns", help="turns.json from read_turns.py")
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-answer", type=float, default=6.0, help="seconds. Shorter turns are backchannel, not answers")
    ap.add_argument("--min-answer-words", type=int, default=15)
    ap.add_argument("--max-answer", type=float, default=240.0, help="seconds. Longer means somebody is giving a talk")
    ap.add_argument("--max-answers", type=int, default=6)
    ap.add_argument("--min-answers", type=int, default=2, help="one answer is a clip, not a series")
    ap.add_argument("--any-question", action="store_true", help="count a question to one person too")
    a = ap.parse_args()

    T = json.load(open(a.turns, encoding="utf-8"))
    series = find(T["turns"], min_answer_s=a.min_answer, min_answer_words=a.min_answer_words,
                  max_answers=a.max_answers, max_answer_s=a.max_answer, min_answers=a.min_answers,
                  room_only=not a.any_question)
    out = {
        "schema": "shorts-questions/v1",
        "turns_file": a.turns,
        "captions": T.get("captions"),
        "words": T.get("words"),
        "turns": len(T["turns"]),
        "speaker_markers": T.get("speaker_markers"),
        "room_only": not a.any_question,
        "measured": False,
        "_read_this_first": [
            "Every in and out is a caption timing. It locates a passage and cannot place a cut.",
            "No answer is attributed. Turn N means the captioner heard a new voice, not who it was.",
            "A series is a question-shaped sentence to the room followed by two or more turns long enough to be answers. A person confirms it."
        ],
        "series": series
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"{len(series)} series, {sum(len(s['answers']) for s in series)} answers -> {a.out}")
    for s in series:
        print(f"  {s['id']}  {s['question']['at']}  {s['question']['dur_s']}s question, {len(s['answers'])} answers  \"{s['question']['text'][:70]}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
