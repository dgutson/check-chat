"""Build the excerpt the judging subagent reads — with position information removed.

Blinding is not politeness, it is the difference between a judgment and a prior. A
judge that can see "exchange 180 of 200" does not need to read anything: it will
report degradation, because long conversations are supposed to be degraded. It would
score depth, which is already known and needs no LLM, instead of behaviour, which is
the only thing worth asking a model about.

So exchanges are renumbered from 1, absolute positions are dropped, and nothing
states how long the session is. What survives is the goal (the opening turns, where
constraints get stated and against which drift is measurable) and the recent work.
A gap marker sits between them: it admits that material was cut without revealing
how much.

A second marker was designed and then removed: one saying the excerpt straddled a
**compaction**, because re-asking for something stated above such a seam is correct
behaviour rather than `confusion`, and a constraint from above it was lost rather than
ignored. The reasoning holds; there is just no way to detect a compaction yet. See the
roadmap — it is worth restoring in full the day a compacted transcript exists to check
it against, and the marker itself is six lines.
"""

from __future__ import annotations

import re

from .transcript import Session

HEAD_TURNS = 2              # where the goal and the constraints live
TAIL_TURNS = 10             # where drift shows up
PROMPT_CHARS = 1200
REPLY_CHARS = 1400

GAP = "[... earlier exchanges omitted ...]"

# Blinding has to survive the conversation not being in English. A Spanish session
# saying "como dije en el turno 47" leaks exactly what an English one saying "as I
# said in turn 47" leaks, and a judge that learns the position stops judging.
_POSITION = re.compile(
    r"\b(?:turns?|exchanges?|messages?|steps?"                      # en
    r"|turnos?|mensajes?|pasos?|intercambios?"                      # es
    r"|mensagens?|passos?"                                          # pt
    r"|tours?|étapes?|messages?"                                    # fr
    r"|Schritte?n?|Nachrichten?)\s+#?\d+\b"
    r"|\b\d+\s*(?:of|/|de|von)\s*\d+\s*"
    r"(?:turns?|messages?|turnos?|mensajes?|mensagens?|Nachrichten?)\b",
    re.I,
)


def _tools_line(sess: Session, turn: int) -> str:
    counts: dict[str, int] = {}
    for s in sess.steps_of(turn):
        for c in s.calls:
            counts[c.tool] = counts.get(c.tool, 0) + 1
    if not counts:
        return ""
    parts = [f"{t}x{n}" if n > 1 else t for t, n in sorted(counts.items(), key=lambda kv: -kv[1])]
    return "[tools: " + ", ".join(parts[:6]) + "]"


def _scrub(text: str) -> str:
    """Remove position references the excerpt itself might contain."""
    return _POSITION.sub("[position removed]", text or "")


def selected(sess: Session) -> tuple[list[int], bool]:
    """Which turns go in the digest, and whether anything was cut between them."""
    n = len(sess.turns)
    if n <= HEAD_TURNS + TAIL_TURNS:
        return list(range(n)), False
    head = list(range(HEAD_TURNS))
    tail = list(range(n - TAIL_TURNS, n))
    return head + tail, True


def build(sess: Session) -> str:
    """A blinded transcript excerpt, ready to hand to a subagent verbatim."""
    idxs, gapped = selected(sess)
    lines: list[str] = []
    prev = None

    for label, i in enumerate(idxs, start=1):
        if gapped and prev is not None and i != prev + 1:
            lines.append(f"\n{GAP}\n")
        prev = i
        t = sess.turns[i]
        lines.append(f"### Exchange {label}")
        lines.append("USER: " + _scrub(t.prompt.strip())[:PROMPT_CHARS])
        reply = _scrub(sess.reply_text(i, REPLY_CHARS)).strip()
        lines.append("ASSISTANT: " + (reply[:REPLY_CHARS] if reply else "(no prose; tool calls only)"))
        tools = _tools_line(sess, i)
        if tools:
            lines.append(tools)
        lines.append("")

    return "\n".join(lines).strip()


def stats(sess: Session) -> dict:
    """The unblinded facts — for the user's report, never for the judge."""
    idxs, gapped = selected(sess)
    return {
        "turns": len(sess.turns),
        "responses": len(sess.steps),
        "calls": len(sess.calls),
        "depth_tokens": sess.depth,
        "truncated": sess.truncated,
        "dropped_bytes": sess.dropped_bytes,
        "model": sess.model,
        "digest_exchanges": len(idxs),
        "digest_gapped": gapped,
    }


__all__ = ["build", "stats", "selected", "GAP", "HEAD_TURNS", "TAIL_TURNS"]
