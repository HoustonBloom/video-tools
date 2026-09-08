#!/usr/bin/env python3
"""The kinds of moment worth finding in a recording, in one place.

A moment is a point in a recording where something known happens: somebody is
introduced, somebody introduces themselves, a question goes to the room, a
sponsor is thanked. Each kind is a row here. Adding a kind is adding a row.

WHY A REGISTRY. A pass that reads one kind, the host handing over to the next
speaker, returns nothing at all on a recording without one. A conversation
format has no host handoffs and does have sponsors, a question to the room and
the show describing itself, so a pass that reads one kind reports an hour of
it as empty. A pass that reads every kind reports what is in it.

`bounds` marks a kind that can start a stretch of the recording. Handoffs do.
A sponsor thank-you does not: it is a moment, not a boundary.

`names` marks a kind that can carry a person's name. A name read here is always
a reading of a quotation, never a fact, and both the reading and the sentence it
came from travel together so a person can check one against the other.
"""

import re

KINDS = [
    {
        "id": "handoff",
        "label": "Someone introduced",
        "what": "The host hands over and says who is next.",
        "bounds": True,
        "names": "after",
        # The last three came from one recording: "Today, our guest
        # speaker is [name]", "this gentleman over here [name] is going to talk
        # about [product]", "move on over to [name]". None matched, so the guest
        # and both featured founders were not on the page. Every recording
        # that goes through adds the phrasing its host used; the fixture keeps
        # it from being lost again.
        "pattern": re.compile(
            r"(next up|come on up|give it up for|invite you to come|please welcome|"
            r"let's bring up|welcome up|coming up next|take it away|the stage is yours|"
            r"our guest speaker is|our guest today is|is going to talk about|"
            r"is going to tell us|move on over to|hand (?:it|the mic) over to)", re.I),
    },
    {
        "id": "self-intro",
        "label": "Introduced themselves",
        "what": "Somebody says their own name.",
        "bounds": True,
        "names": "self",
        # Not "this is". On one gathering it read "this is [a river]", "this
        # is [a town] school district" and "this is America": three places, no
        # person, and each one opened a stretch.
        # A name has to follow, or "I'm going to" and "I'm excited" swamp it.
        # Measured before this rule: 60 matches on one recording and 31 on the
        # other, nearly all of them a contraction with no name behind it.
        # Case-insensitive on the trigger. While it was not, "My name is [First
        # Last]" was skipped and a weaker "i am My" later in the same line won
        # the match, so a featured founder's own introduction lost its name.
        # And the word after the trigger has to be one that could be a name.
        # "I'm I'm really curious" opened a stretch at 45:23 of one recording
        # and "I'm I guess" opened one at 1:33:08. The first of those was the
        # only boundary in the first 79 minutes, so the page read the whole
        # opening as somebody's introduction.
        "gap": 30,
        "pattern": None,  # built below, once NOT_A_NAME exists
    },
    {
        "id": "invite-intro",
        "label": "Asked to introduce themselves",
        "what": "The host opens the floor for people to introduce themselves.",
        "bounds": True,
        "names": None,
        "pattern": re.compile(
            r"(introduce yourself|introduce yourselves|introduce themselves|"
            r"quick introduction|give yourself a|tell us who you are|"
            r"say who you are|do the introductions)", re.I),
    },
    {
        "id": "to-room",
        "label": "Put to the room",
        "what": "A question aimed at everybody rather than one person.",
        "bounds": False,
        "names": None,
        "pattern": re.compile(
            r"(anyone else|does anyone|has anyone|did anyone|show of hands|"
            r"raise your hand|who here|who knows|any questions|questions from the)", re.I),
    },
    {
        "id": "sponsor",
        "label": "Sponsor named",
        "what": "Who paid for the room, said out loud.",
        "bounds": False,
        "names": None,
        "pattern": re.compile(
            r"(thank our sponsor|thanks to our sponsor|thank you to our sponsor|"
            r"shout out to our sponsors?|our sponsors|sponsored by|made possible by|"
            r"brought to you by|"
            r"our partners for|thank our partner)", re.I),
    },
    {
        "id": "what-this-is",
        "label": "What this is",
        "what": "The recording describing itself, which is the line a stranger needs.",
        "bounds": False,
        "names": None,
        "pattern": re.compile(
            r"(welcome to [A-Z]|(?i:welcome (?:everybody|everyone|all|y'all) to)|"
            r"is a live|is a monthly|happens on the [\w]+ "
            r"(friday|saturday|sunday|monday|tuesday|wednesday|thursday|day)|"
            r"the idea behind|what we do here|the whole point of this)"),
    },
    {
        "id": "closing",
        "label": "Closing",
        "what": "The end, said out loud.",
        "bounds": False,
        "names": None,
        "pattern": re.compile(
            r"(thank you all for coming|thank you so much for coming|that's a wrap|"
            r"see you next|until next time|that's all we have|wrap (it|this) up)", re.I),
    },
]

BY_ID = {k["id"]: k for k in KINDS}

# `gap` is the seconds two moments of one kind must be apart to count twice.
# A kind without one takes the run's --min-gap. A round of self-introductions
# goes faster than that: on one recording five founders introduced themselves
# in four and a half minutes, about 50 seconds each, and a 120 second gap
# kept two of them.

# Words that arrive where a name would and are not one.
NOT_A_NAME = {
    "i", "we", "you", "he", "she", "they", "it", "us", "me", "my", "our", "your",
    "uh", "um", "so", "and", "but", "the", "a", "an", "this", "that", "next",
    "up", "everyone", "everybody", "somebody", "anyone", "please", "thank",
    "thanks", "let's", "lets", "all", "right", "okay", "ok", "yeah", "going",
    "here", "just", "not", "really", "excited", "glad", "happy", "gonna",
    # "That's the laser pointing dude" read "That's" as a name on one recording.
    "that's", "thats", "there's", "theres", "it's", "its", "he's", "she's",
    "still", "pretty", "sure", "sorry", "actually", "definitely", "kind",
    # "I am [Name] Welcome, good to meet you" read the greeting as a surname.
    "welcome", "hello", "hi", "hey", "good", "nice", "everyone", "everybody",
    # "My name is [Name] I'm the co-host" read the name as "[Name] I'm".
    "i'm", "im", "i've", "ive", "i'll", "we're", "we've", "they're", "you're",
}

_NOT = "|".join(sorted((re.escape(w) for w in NOT_A_NAME), key=len, reverse=True))
BY_ID["self-intro"]["pattern"] = re.compile(
    r"(?i:\b(?:my name is|my name's|i'm|i am))\s+(?!(?i:" + _NOT + r")\b)[A-Z][\w'-]+")

NAME_AFTER = re.compile(
    r"(?i:next up|give it up for|please welcome|let's bring up|welcome up|coming up next|"
    r"our guest speaker is|our guest today is|move on over to|hand (?:it|the mic) over to|"
    r"gentleman over here|lady over here)"
    r"(?i:[,\s]*(?:we're gonna have|we are going to have|we have|i have|it is|it's|we've got)?)"
    r"[,\s]*([A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,2})")
NAME_BEFORE = re.compile(
    r"\b([A-Z][\w'-]+(?:\s+[A-Z][\w'-]+)?)\s+(?i:i'd like to invite|you ready|is going to talk about|is going to tell us)")
# Only an explicit naming reads a name. "I'm" and "I am" still mark a self
# introduction, and they do not name one: on a recording where people talk about
# where they are from, "I'm America", "[a town]" and "[a river]" were all read as
# people. Somebody saying "my name is" is stating a name. Somebody saying "I'm"
# is starting a sentence.
NAME_SELF = re.compile(
    r"(?i:\b(?:my name is|my name's))\s+([A-Z][\w'-]*(?:\s+[A-Z][\w'-]*){0,2})")
# "I'm [First Last]" is also stating a name, and what separates it from "I'm
# America" is the second capitalised word. Two or more, or nothing is read.
NAME_SELF_IM = re.compile(
    r"\b(?:I'm|I am)\s+([A-Z][\w'-]+(?:\s+[A-Z][\w'-]+){1,2})")


def read_name(sentence, how):
    """A reading of a name out of a sentence, or None. Never a fact."""
    if not how:
        return None
    pats = (NAME_SELF, NAME_SELF_IM) if how == "self" else (NAME_AFTER, NAME_BEFORE)
    for pat in pats:
        m = pat.search(sentence)
        if not m:
            continue
        parts = [p for p in m.group(1).strip(" ,.").split() if p.lower() not in NOT_A_NAME]
        if pat is NAME_SELF_IM and len(parts) < 2:
            continue
        if parts and parts[0][:1].isupper():
            return " ".join(parts)
    return None
