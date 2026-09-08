"""
The one-command path over three steps. Captions in, a proposal and plans out.

    python find_answers.py CAPTIONS.vtt --out answers/answers.json --plans answers/plans --video SOURCE.mp4 --stills answers/stills

This runs, in order, and leaves each step's file beside the output:

    read_turns.py      CAPTIONS.vtt   -> turns.json        who spoke when, no names
    find_questions.py  turns.json     -> questions.json    questions the room answered
    plan_series.py     questions.json -> answers.json      a plan per answer, stills if asked

Each of those runs alone on the file before it, and that is the point: design
for sufficiency. A community that wants only the summary
runs step one and reads it. One that wants only the questions runs two. Only
the one that wants clips pays for three, and only the one that wants stills
opens the video. This wrapper exists for the case that wants all of it and does
not want to type three commands.

An earlier version of this file did all three jobs itself. It was split because
a bundled tool forces everyone to pay for every step. The shape it proposes is in
references/series.md.
"""

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(HERE, script), *args], text=True)
    if r.returncode:
        sys.exit(r.returncode)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("vtt")
    ap.add_argument("--out", required=True, help="answers.json. turns.json and questions.json land beside it")
    ap.add_argument("--plans")
    ap.add_argument("--video")
    ap.add_argument("--stills")
    ap.add_argument("--min-answer", type=float)
    ap.add_argument("--min-answer-words", type=int)
    ap.add_argument("--max-answer", type=float)
    ap.add_argument("--max-answers", type=int)
    ap.add_argument("--min-answers", type=int)
    ap.add_argument("--any-question", action="store_true")
    a = ap.parse_args()

    out_dir = os.path.dirname(os.path.abspath(a.out)) or "."
    turns = os.path.join(out_dir, "turns.json")
    questions = os.path.join(out_dir, "questions.json")

    run("read_turns.py", a.vtt, "--out", turns)

    qargs = [turns, "--out", questions]
    for flag, val in (("--min-answer", a.min_answer), ("--min-answer-words", a.min_answer_words),
                      ("--max-answer", a.max_answer), ("--max-answers", a.max_answers), ("--min-answers", a.min_answers)):
        if val is not None:
            qargs += [flag, str(val)]
    if a.any_question:
        qargs.append("--any-question")
    run("find_questions.py", *qargs)

    pargs = [questions, "--out", a.out]
    if a.plans: pargs += ["--plans", a.plans]
    if a.video: pargs += ["--video", a.video]
    if a.stills: pargs += ["--stills", a.stills]
    run("plan_series.py", *pargs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
