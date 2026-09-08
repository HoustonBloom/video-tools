"""
Step three of three. Questions in, one answer-form plan per responder out.

    python plan_series.py questions.json --out answers.json --plans plans/
    python plan_series.py questions.json --out answers.json --plans plans/ --video SOURCE.mp4 --stills stills/

Reads the questions file find_questions.py wrote and writes what a renderer and
a reviewer need: a plan per answer for build_short.py, and, only if asked, one
still per answer so a person can say who it is. The stills are the only part
that touches the video, and they are opt-in. Nothing here needs a model.

The plans are the shape in references/series.md. The question is the hook and
is the same span in every plan of a series; the person's answer is the payoff.
Every plan is marked unmeasured and carries the two find_edges commands that
measure its boundaries. profile is null until analyze_source.py has read the
picture. build_short.py will not render either state, which is correct.

The montage, one question then one line from each person, is not written here.
build_short.py refuses that form and series.md says to assemble it by hand.
"""

import argparse
import json
import os
import subprocess
import sys


def still(video, at, out_path):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.2f}", "-i", video,
                    "-frames:v", "1", "-q:v", "3", out_path], capture_output=True, text=True)
    return os.path.isfile(out_path)


def plan_for(sid, q, a, n, video):
    return {
        "_comment": [
            "Answer-form plan, proposed by plan_series.py. Not measured, not attributed, not renderable yet.",
            "The question is the hook and is the same span in every plan of this series. Measure it once.",
            "profile is null on purpose: nobody has measured this picture. analyze_source.py fills it."
        ],
        "form": "answer",
        "series": sid,
        "responder": f"turn {n} after the question. Attribute against the picture before this renders.",
        "source": video,
        "output": None,
        "profile": None,
        "_measured": False,
        "_measure": [
            f"python find_edges.py SOURCE --start {q['in'] - 2:.2f} --end {q['out'] + 2:.2f} --min-gap 0.30",
            f"python find_edges.py SOURCE --start {a['in'] - 2:.2f} --end {a['out'] + 2:.2f} --min-gap 0.30"
        ],
        "segments": [
            {"in": q["in"], "out": q["out"], "beat": "hook", "mode": "camera",
             "why": "the question, in the asker's voice. Same span at the head of every clip in the series."},
            {"in": a["in"], "out": a["out"], "beat": "payoff", "mode": "camera",
             "why": f"turn {n}'s whole answer. If it runs long, split it into a build and a payoff by hand; that is a choice, not a measurement."}
        ]
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("questions", help="questions.json from find_questions.py")
    ap.add_argument("--out", required=True, help="the proposal, with plan and still paths added")
    ap.add_argument("--plans", help="folder for one plan per answer")
    ap.add_argument("--video", help="the source file. Needed for stills, and written into each plan's source")
    ap.add_argument("--stills", help="folder for one frame per answer, at two seconds in. Needs --video and ffmpeg")
    a = ap.parse_args()

    Q = json.load(open(a.questions, encoding="utf-8"))
    out_dir = os.path.dirname(os.path.abspath(a.out)) or "."
    rel = lambda p: os.path.relpath(os.path.abspath(p), out_dir).replace(os.sep, "/")
    plans = stills = 0
    for s in Q["series"]:
        for ans in s["answers"]:
            ans["still"] = ans.get("still")
            ans["plan"] = ans.get("plan")
            if a.video and a.stills:
                sp = os.path.join(a.stills, f"{s['id']}_answer-{ans['turn']}.jpg")
                if still(a.video, ans["in"] + min(2.0, ans["dur_s"] / 2), sp):
                    ans["still"] = rel(sp); stills += 1
            if a.plans:
                os.makedirs(a.plans, exist_ok=True)
                pp = os.path.join(a.plans, f"{s['id']}_answer-{ans['turn']}.json")
                with open(pp, "w", encoding="utf-8") as f:
                    json.dump(plan_for(s["id"], s["question"], ans, ans["turn"], a.video), f, indent=2)
                ans["plan"] = rel(pp); plans += 1
    Q["schema"] = "shorts-answer-series/v1"
    Q["questions_file"] = a.questions
    Q["video"] = a.video
    os.makedirs(out_dir, exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(Q, f, indent=2, ensure_ascii=False)
    n = sum(len(s["answers"]) for s in Q["series"])
    print(f"{len(Q['series'])} series, {n} answers, {plans} plans, {stills} stills -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
