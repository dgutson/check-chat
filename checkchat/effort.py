"""Is the reasoning-effort setting matched to the work being asked for?

Two opposite wastes, and the second is the expensive one:

* **Overkill** — `xhigh` or `max` spent on a turn that was one question with one
  answer. Asking how to write a `for` loop in bash does not need maximum reasoning.
* **Circling** — a turn that went round and round: many responses, the same file
  edited over and over, calls failing and being retried. Thinking harder once is
  cheaper than flailing twenty times, so here the *low* setting is what cost money.

Both are read off structure — response counts, edit repetition, failures — so neither
depends on what language anyone is typing in.

Effort is recorded on every assistant record, so this needs no inference. What it
cannot know is whether a short turn was *meant* to be cheap: a one-line question that
genuinely needs deep reasoning looks identical to a trivial one from the outside. So
overkill is reported as a **rate over the session**, never as a verdict on any single
turn, and the threshold is set where a run of such turns is unambiguous.
"""

from __future__ import annotations

from collections import Counter

from .transcript import EDIT_TOOLS, Session

ORDER = {"medium": 0, "high": 1, "xhigh": 2, "max": 3}
EXPENSIVE = ("xhigh", "max")

# A turn that asked one thing and got one answer.
TRIVIAL_RESPONSES = 2
TRIVIAL_CALLS = 1
# A turn that went round in circles.
CIRCLING_RESPONSES = 10
CIRCLING_REPEATS = 3
CIRCLING_FAILURES = 2


def _turn_shape(sess: Session, turn: int) -> dict:
    steps = sess.steps_of(turn)
    calls = [c for s in steps for c in s.calls]
    edits = Counter(
        c.params.get("file_path", "") for c in calls
        if c.tool in EDIT_TOOLS and c.params.get("file_path")
    )
    return {
        "responses": len(steps),
        "calls": len(calls),
        "edits": sum(edits.values()),
        "max_edits_one_file": max(edits.values(), default=0),
        "failures": sum(1 for c in calls if c.ok is False),
        "effort": next((s.effort for s in steps if s.effort), None),
    }


def analyse(sess: Session) -> dict:
    """Per-turn effort against per-turn work, aggregated over the session."""
    turns = [_turn_shape(sess, t.index) for t in sess.turns]
    turns = [t for t in turns if t["responses"]]
    if not turns:
        return {"turns": 0, "fired": False}

    overkill = [
        t for t in turns
        if t["effort"] in EXPENSIVE
        and t["responses"] <= TRIVIAL_RESPONSES
        and t["calls"] <= TRIVIAL_CALLS
        and t["edits"] == 0
    ]
    circling = [
        t for t in turns
        if t["responses"] >= CIRCLING_RESPONSES
        and (t["max_edits_one_file"] >= CIRCLING_REPEATS or t["failures"] >= CIRCLING_FAILURES)
        and ORDER.get(t["effort"] or "", 9) <= ORDER["high"]
    ]
    efforts = Counter(t["effort"] for t in turns if t["effort"])

    return {
        "turns": len(turns),
        "effort_mix": dict(efforts),
        "overkill_turns": len(overkill),
        "overkill_rate": round(len(overkill) / len(turns), 3),
        "circling_turns": len(circling),
        "circling_detail": [
            {"responses": t["responses"], "repeat_edits": t["max_edits_one_file"],
             "failures": t["failures"], "effort": t["effort"]}
            for t in circling[:3]
        ],
        # Deliberately conservative: one cheap-looking turn proves nothing, because a
        # short question can legitimately need deep reasoning. A run of them is a
        # setting left too high, not a coincidence.
        "fired": len(overkill) >= 3 or bool(circling),
    }


__all__ = ["analyse", "ORDER", "EXPENSIVE"]
