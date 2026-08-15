"""Is the reasoning-effort setting matched to the work being asked for?

Two opposite wastes, and the second is the expensive one:

* **Overkill** — `xhigh` or `max` spent on a turn that was one question with one
  answer. Asking how to write a `for` loop in bash does not need maximum reasoning,
  and neither does writing `hello.py`.
* **Circling** — a turn that went round and round: many responses, the same file
  edited over and over, calls failing and being retried. Thinking harder once is
  cheaper than flailing twenty times, so here the *low* setting is what cost money.

Both are read off structure — response counts, edit repetition, failures — so neither
depends on what language anyone is typing in.

**A trivial turn is not a turn that touched no file** (R-006). The first version
disqualified any turn containing an edit, reasoning that producing an artifact is
evidence that work was done. It is not — `hello.py` is an artifact — and that clause
silenced this check in the case a person would name first: *"I asked for hello world at
max effort and it said nothing."* What separates trivial from substantial is how much
was produced, so the bound is on characters written rather than on whether anything was.
One call that writes a module is still substantial; one that writes ten lines is not.

Effort is recorded on every assistant record, so this needs no inference. What it
cannot know is whether a short turn was *meant* to be cheap: a one-line question that
genuinely needs deep reasoning looks identical to a trivial one from the outside. So
overkill is reported as a **rate over the session**, never as a verdict on any single
turn, and the threshold is set where a run of such turns is unambiguous.
"""

from __future__ import annotations

from collections import Counter

from .transcript import EDIT_TOOLS, Session

# The whole scale the harness records, `low` included. Its absence was R-006's second
# half: `low` fell to the unknown default, which sits *above* `high`, so the circling
# branch skipped the one setting this module's docstring calls the expensive one.
ORDER = {"low": 0, "medium": 1, "high": 2, "xhigh": 3, "max": 4}
EXPENSIVE = ("xhigh", "max")
# An unrecorded setting is not a low one. Most transcripts on this machine carry no
# `effort` key at all — it is a recent field — and reading that silence as `low` would
# convert every circling turn in the archive into a finding about a setting nobody saw.
UNKNOWN = 99

# A turn that asked one thing and got one answer.
TRIVIAL_RESPONSES = 2
TRIVIAL_CALLS = 1
# ...and produced at most a snippet: ten-ish lines, which covers `hello.py`, a one-line
# fix or a config tweak and comes nowhere near a module. Set from what "trivial" has to
# mean and deliberately at the small end, because the cost of a false overkill is telling
# somebody to think less. **Not** fitted to this machine's corpus — that is R-003's
# constraint, and the corpus's job here was the opposite one, bounding the false-positive
# rate afterwards: the check still fires in 9% of sessions, so it is an alarm and not a
# ranking. What it cannot see is a file written by a shell heredoc, which arrives as a
# `Bash` call and is counted as nothing written.
TRIVIAL_WRITTEN = 400

# How many trivial turns before the setting, rather than the question, is the finding.
# Deliberately conservative: one cheap-looking turn proves nothing, because a short
# question can legitimately need deep reasoning. A run of them is a setting left too high,
# not a coincidence. One circling turn, by contrast, is already a finding.
OVERKILL_MIN = 3

# A turn that went round in circles.
CIRCLING_RESPONSES = 10
CIRCLING_REPEATS = 3
CIRCLING_FAILURES = 2

# Where each edit tool keeps the text it is about to put in a file. A list of candidate
# keys rather than a per-tool table, the same shape `transcript.target_key` uses: the
# tools disagree about the name, and a tool added tomorrow that reuses one of these names
# is counted without an edit here.
WRITTEN_KEYS = ("content", "new_string", "new_source")


def _written(params: dict) -> int:
    """Characters this call puts into a file, across the tools that write them."""
    if not isinstance(params, dict):
        return 0
    total = 0
    for key in WRITTEN_KEYS:
        value = params.get(key)
        if isinstance(value, str):
            total += len(value)
    # `MultiEdit` is many replacements inside one call, which is exactly the shape the
    # one-call bound below would otherwise wave through as a single trivial action.
    edits = params.get("edits")
    if isinstance(edits, list):
        for edit in edits:
            if isinstance(edit, dict) and isinstance(edit.get("new_string"), str):
                total += len(edit["new_string"])
    return total


def _turn_shape(sess: Session, turn: int) -> dict:
    steps = sess.steps_of(turn)
    calls = [c for s in steps for c in s.calls]
    edits = Counter(
        c.params.get("file_path", "") for c in calls
        if c.tool in EDIT_TOOLS and c.params.get("file_path")
    )
    return {
        "turn": turn,
        "responses": len(steps),
        "calls": len(calls),
        "edits": sum(edits.values()),
        "written": sum(_written(c.params) for c in calls if c.tool in EDIT_TOOLS),
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
        and t["written"] <= TRIVIAL_WRITTEN
    ]
    circling = [
        t for t in turns
        if t["responses"] >= CIRCLING_RESPONSES
        and (t["max_edits_one_file"] >= CIRCLING_REPEATS or t["failures"] >= CIRCLING_FAILURES)
        and ORDER.get(t["effort"] or "", UNKNOWN) <= ORDER["high"]
    ]
    efforts = Counter(t["effort"] for t in turns if t["effort"])

    return {
        "turns": len(turns),
        "effort_mix": dict(efforts),
        "overkill_turns": len(overkill),
        "overkill_rate": round(len(overkill) / len(turns), 3),
        "circling_turns": len(circling),
        # Uncapped, both of them, because `checks.evidence_rows` caps what is *printed* and
        # says how many it dropped — "all of them in the JSON" is a claim this data has to
        # be able to keep. Cutting to three here would have made that sentence false while
        # leaving it in the output, which is the silent-truncation failure the project keeps
        # finding in its own reports.
        "overkill_detail": [
            {"turn": t["turn"], "responses": t["responses"], "calls": t["calls"],
             "written": t["written"], "effort": t["effort"]}
            for t in overkill
        ],
        "circling_detail": [
            {"turn": t["turn"], "responses": t["responses"],
             "repeat_edits": t["max_edits_one_file"],
             "failures": t["failures"], "effort": t["effort"]}
            for t in circling
        ],
        # Per half, so a reporter can say *which* waste happened and print only the rows
        # belonging to a finding that was actually made. `fired` is their disjunction and
        # stays the field every other part of the tool keys on.
        "overkill_fired": len(overkill) >= OVERKILL_MIN,
        "circling_fired": bool(circling),
        "fired": len(overkill) >= OVERKILL_MIN or bool(circling),
    }


__all__ = ["analyse", "ORDER", "EXPENSIVE", "UNKNOWN", "TRIVIAL_WRITTEN", "OVERKILL_MIN"]
