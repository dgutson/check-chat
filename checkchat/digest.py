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

A second marker was designed, removed for want of a compacted transcript to check it
against, and is now **restored**: one saying the excerpt straddles a **compaction**,
because re-asking for something stated above such a seam is correct behaviour rather
than `confusion`, and a constraint from above it was lost rather than ignored.

It carries the *fact* and no instruction, and that split is deliberate rather than
stylistic. The judge's prompt tells it to ignore instructions found inside the excerpt —
correctly, since the excerpt is evidence written to someone else — so guidance placed
here would be guidance it is required to disregard. The three scoring rules the marker
implies therefore live in `agents/check-chat-judge.md`, keyed to the marker exactly as
the gap marker's rule already is, and they cost nothing when no seam is present because
a judge that never sees the marker never applies them.

**What the marker discloses, stated rather than implied.** A compaction only happens in a
conversation long enough to fill a context window, so this leaks a coarse length signal
into a deliberately blinded excerpt — the one thing this module exists to prevent. It
ships anyway because every finding it enables is a **suppression**: it exists to turn
three would-be findings into zeroes, never to add one. The judge's prompt closes the loop
by saying so, since the alternative is not silence but a confident false positive.
"""

from __future__ import annotations

import re

from .transcript import Session

HEAD_TURNS = 2              # where the goal and the constraints live
TAIL_TURNS = 10             # where drift shows up
PROMPT_CHARS = 1200
REPLY_CHARS = 1400

LEDGER_ROWS = 120           # measured on 54 sessions: median 20 rows, p90 126, max 184
LEDGER_TARGET_W = 72

GAP = "[... earlier exchanges omitted ...]"
LEDGER_CUT = "[... further calls omitted ...]"

# Bare of trigger and token counts on purpose: those are length information, and they go
# in the user's report where they are useful, not to the judge where they are a prior.
# "the earlier conversation" rather than "everything above" because the harness preserves
# a handful of recent messages verbatim past the seam — measured at 4 and 2 — and a marker
# that overstates what was lost is a marker the judge is right to distrust.
SEAM = "[... context compacted here: the earlier conversation was replaced by a summary ...]"

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


def _size(n: int) -> str:
    """A result's size, bucketed. Per-call sizes disclose nothing about session length."""
    if n <= 0:
        return ""
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        return f"{n // 1000}k"
    return f"{n / 1e6:.1f}M"


def _target(key: str) -> str:
    """One line, truncated where it costs the least meaning.

    A path is identified by its *tail* — the basename is the part a finding names — while a
    command is identified by its *head*, because what it ran comes first and `| head -40`
    at the end is noise. Splitting on whitespace rather than on the tool name keeps this
    right for `pattern` and `query` keys too, which read like commands and belong to tools
    that also take paths.
    """
    key = " ".join((key or "").split())
    if len(key) <= LEDGER_TARGET_W:
        return key
    if " " in key:                                  # command-shaped: the head carries it
        return key[:LEDGER_TARGET_W - 1] + "…"
    keep = (LEDGER_TARGET_W - 1) // 2               # path-shaped: keep the basename
    return f"{key[:keep]}…{key[-keep:]}"


def _slice(params: dict) -> str:
    """Which part of a file was read, when it was not the whole thing.

    Without this, three reads of different slices of one file are three identical-looking
    rows, and the judge is being shown a repeat that did not happen — manufacturing the
    exact false positive `ledger`'s docstring warns it away from. The distinction is also
    the difference between a `partial_use` proof and ordinary work.
    """
    if not isinstance(params, dict):
        return ""
    off, lim = params.get("offset"), params.get("limit")
    if not isinstance(off, int) and not isinstance(lim, int):
        return ""
    start = off if isinstance(off, int) else 0
    if isinstance(lim, int):
        return f" [lines {start}-{start + lim}]"
    return f" [from line {start}]"


def ledger(sess: Session) -> str:
    """What the tool calls actually touched, for the exchanges the excerpt contains.

    The prose digest says *how many* calls an exchange made (`[tools: Read x3]`) and never
    *what they acted on*, so one class of finding is invisible to the judge and to every
    Python check at once: an `Edit` to a file the user placed off limits, an answer
    claiming a change no `Edit` performed, a long hunt through the wrong directory. The
    counting checks cannot name those because nobody anticipated them — that is the hole
    — and the judge could not see them because targets never reached it.

    **Blinding survives by construction**, which is the only reason this can ship. Rows
    cover exactly the exchanges already in the excerpt and carry the same renumbered
    `E<n>` label, so the ledger discloses no count the `[tools: ...]` lines did not
    already. The invariant is **one-directional** — never *more* rows than that line
    states, sometimes fewer — and the direction is the whole point, so do not restate it
    as equality: `LEDGER_ROWS` truncates 7 of 54 corpus sessions, which under-discloses 24
    exchanges and leaks nothing. Measured over the shipping code on 54 sessions: **0
    over-disclosing exchanges, 0 mislabelled rows**, all 24 under-disclosures inside a
    capped session, and 89% of all calls in scope. Targets are scrubbed like prose,
    because a command can contain the position reference the excerpt withholds.

    What it must **not** be read for is counting repeats. Python counts them better, and
    with the exclusions that make the count correct: two `Edit`s to one file is ordinary
    work, and 10 of those 54 sessions contain such a repeat while `rereads`, `producers`
    and `partial_use` are all correctly quiet. A judge asked "what looks wasteful" scores
    exactly those as findings, so the prompt fences them off by name.
    """
    idxs, _ = selected(sess)
    rows: list[str] = []
    for label, i in enumerate(idxs, start=1):
        for c in (c for c in sess.calls if c.turn == i):
            if len(rows) >= LEDGER_ROWS:
                rows.append(LEDGER_CUT)
                return "\n".join(rows)
            flag = "  DECLINED" if c.declined else ("  FAILED" if c.ok is False else "")
            size = _size(c.result_chars)
            rows.append(f"E{label}  {c.tool}  {_scrub(_target(c.key))}{_slice(c.params)}"
                        f"{f'  ({size})' if size else ''}{flag}")
    return "\n".join(rows)


def build(sess: Session) -> str:
    """A blinded transcript excerpt, ready to hand to a subagent verbatim."""
    idxs, gapped = selected(sess)
    seams = {c.turn for c in sess.compactions}
    lines: list[str] = []
    prev = None

    for label, i in enumerate(idxs, start=1):
        if gapped and prev is not None and i != prev + 1:
            lines.append(f"\n{GAP}\n")
            # A seam buried in the omitted material still governs how the material that
            # *survived* must be read — a constraint in Exchange 1 can have been lost to a
            # compaction the excerpt never shows — so it is disclosed beside the gap rather
            # than dropped with the exchanges it happened to fall between.
            if any(prev < t < i for t in seams):
                lines.append(f"{SEAM}\n")
        prev = i
        t = sess.turns[i]
        lines.append(f"### Exchange {label}")
        lines.append("USER: " + _scrub(t.prompt.strip())[:PROMPT_CHARS])
        # Between the prompt and the reply, because that is where an automatic compaction
        # actually falls: it fires while a turn is being served, so the human's question
        # was asked before the seam and answered after it.
        if i in seams:
            lines.append(SEAM)
        reply = _scrub(sess.reply_text(i, REPLY_CHARS)).strip()
        lines.append("ASSISTANT: " + (reply[:REPLY_CHARS] if reply else "(no prose; tool calls only)"))
        tools = _tools_line(sess, i)
        if tools:
            lines.append(tools)
        lines.append("")

    # The ledger goes inside the excerpt rather than beside it, and that placement is the
    # whole trick: `verdict.check` verifies the judge's quotations against whatever the
    # excerpt contains, so a finding that cites a tool call becomes checkable for free —
    # by the same machinery, with no second verification path to keep in step.
    table = ledger(sess)
    if table:
        lines += ["### Tool calls, by exchange",
                  "`E<n>` is `Exchange <n>` above. Sizes are the result's, in characters.",
                  "", table]

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
        "compactions": len(sess.compactions),
        "model": sess.model,
        "digest_exchanges": len(idxs),
        "digest_gapped": gapped,
    }


__all__ = ["build", "ledger", "stats", "selected", "GAP", "SEAM", "LEDGER_CUT",
           "HEAD_TURNS", "TAIL_TURNS", "LEDGER_ROWS"]
