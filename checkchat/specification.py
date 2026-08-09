"""Was the work specified well enough to act on — and if not, did the assistant say so?

The loop this exists to catch: a vague question gets a generic answer, the generic
answer doesn't fit, the question gets asked again slightly differently, and several
rounds later nothing has been built. It costs far more than any single wasted payload,
and the person it happens to is the least equipped to notice, because a plausible
generic answer looks like an answer.

## Why this reads the ANSWER, not the question

The obvious design is to classify the user's prompt as vague. It is the wrong one, and
the failure mode is false negatives. *"Why doesn't my code work in parser.py?"* names a
file, so any concreteness test calls it specific — and it is still unanswerable. Worse,
judging vagueness from wording means a phrase list, and a phrase list means the
question has to be vague *in a language someone thought of*.

The response is the more honest instrument. When a request carries enough to act on,
an assistant acts: it opens files, greps, edits. When it doesn't, the assistant
produces prose — and prose with no tool calls, at length, is what an unanswerable
question looks like from the outside, in any language.

So the primary signal is **shape of the exchange**, and the prompt's concreteness is
corroboration that gets reported but never gates.

## The escape hatch that makes it fair

Answering a vague question at length is only a failure if the assistant *didn't ask*.
Asking a clarifying question is the correct handling, so a reply containing a question
never counts against it — `?` and `¿` being about as close to language-independent as
punctuation gets. That single condition is what separates "handled a vague request
well" from the loop this is looking for.
"""

from __future__ import annotations

import re

from .transcript import EDIT_TOOLS, Session
from .sycophancy import is_interjection

LONG_PROSE = 600            # a substantial answer, not an acknowledgement
UNCLARIFIED_MIN = 2         # one is an anecdote; a pattern needs repetition

# Structural marks that a request names something specific. Used as corroboration
# only — deliberately generous, so "concrete" is easy to earn and the label under-
# reports vagueness rather than over-reporting it.
_CONCRETE = re.compile(
    r"`|```|/\w|\\\w|\b\w+\.\w{1,5}\b|\b\w+_\w+\b|\b[a-z]+[A-Z]\w*\b|\bhttps?://|\d"
)
_QUESTION = re.compile(r"[?？¿]")


def _is_reaction(sess: Session, i: int) -> bool:
    """A turn that responds to the assistant's output rather than asking for work.

    Used ONLY to keep the descriptive vagueness rate meaningful — counting "ok" and
    "yes, go on" as underspecified requests is what made a naive version report 56%
    vagueness for an expert. It must never gate the firing signal: a junior re-asking
    a short question after a generic answer looks structurally identical to "go on",
    and excluding it would drop the single most important case this module exists for.
    """
    prev = sess.reply_text(i - 1, 700) if i else ""
    return is_interjection(sess.turns[i].prompt, prev)


def analyse(sess: Session) -> dict:
    """Requests that got prose instead of work, and were never asked about."""
    if not sess.turns:
        return {"requests": 0, "fired": False}

    unclarified, vague, ungrounded, requests = [], 0, 0, 0
    for t in sess.turns:
        i = t.index
        prompt = t.prompt
        reply = sess.reply_text(i, 6000)
        acted = any(s.calls for s in sess.steps_of(i))
        prose = len(reply.strip()) >= LONG_PROSE
        asked = bool(_QUESTION.search(reply))
        concrete = bool(_CONCRETE.search(prompt))

        if not _is_reaction(sess, i):
            requests += 1
            if not concrete:
                vague += 1
        if prose and not acted:
            ungrounded += 1
        # The composite, applied to EVERY turn regardless of shape. All three must
        # hold, so a turn that was acted on, or answered briefly, or asked about,
        # never lands here — that is where the precision comes from, not from
        # pre-filtering which turns were allowed to be examined.
        if prose and not acted and not asked:
            unclarified.append({
                "turn": i,
                "prompt": prompt.strip()[:200],
                "reply_chars": len(reply),
                "named_something_specific": concrete,
                "looked_like_a_reaction": _is_reaction(sess, i),
            })

    edits = [c.turn for c in sess.calls if c.tool in EDIT_TOOLS]
    return {
        "requests": requests,
        "vague_requests": vague,
        "ungrounded_answers": ungrounded,
        "unclarified": unclarified[:5],
        "unclarified_count": len(unclarified),
        # None, not 0, when the session never edited: "rounds before the first edit"
        # is meaningless for a conversation that was never going to produce one, and
        # reporting 0 there would read as a perfect score.
        "rounds_to_first_edit": min(edits) if edits else None,
        "produced_edits": bool(edits),
        "fired": len(unclarified) >= UNCLARIFIED_MIN,
    }


__all__ = ["analyse", "LONG_PROSE", "UNCLARIFIED_MIN"]
