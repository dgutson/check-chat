"""Read a Claude Code transcript into a shape the detectors can work on.

Self-contained on purpose — check-chat is meant to be installable on its own.

Six things about the wire format are easy to get wrong, and each of them silently
corrupts every count downstream:

1. One API response is written as SEVERAL records, one per content block, sharing a
   `requestId`. Treating each record as a turn doubles every rate's denominator.
2. Tool results arrive wearing a `user` role. Counting them as human turns inflates
   the conversation's apparent length several-fold.
3. Subagent traffic (`isSidechain`) lives in the same file but is a separate context.
4. A tool call the human *declined* is flagged `is_error`. It is a decision about the
   work, not a failure, and counting it punishes people who review what the agent does.
5. An interruption is written as a `user` record reading
   `[Request interrupted by user for tool use]`. Kept, it becomes a **turn nobody
   typed** — 15 of them across 9 sessions in the development corpus — and the damage
   is not the inflated count. The phantom sits between the reply and the objection that
   followed it, so `sycophancy` sees a short "interjection" with no reply after it,
   discards that, and then finds the *real* objection preceded by an empty reply and
   rejects it too. Interrupting and then pushing back is the highest-signal sycophancy
   moment there is, and this returned a confident zero for it.
6. A **compaction** writes its summary as a `user` record flagged `isCompactSummary`,
   and — measured on a real compacted transcript — that record carries no `isMeta`, so
   trap 5 arrives a second time by a different door. It is the same defect and worse in
   every dimension: the phantom is ~4,000 characters of the *machine's own prose* rather
   than one bracketed line, it is long enough to be selected into the excerpt as the
   stated goal, and the auto-compaction seam falls **between a real prompt and its
   reply** — so the human's question is left with no reply at all and its answer is
   credited to the phantom. On the transcript this was measured against, the tool
   reported 5 turns where a human typed 3.

   The seam itself is a separate `type: "system"` record, `subtype: "compact_boundary"`,
   and it is worth far more than the phantom it precedes: above it the assistant held a
   summary, not the text. Re-asking there is correct behaviour rather than `confusion`,
   and a constraint stated above it was *lost* rather than disregarded. So the seam is
   kept (see `Compaction`) rather than merely skipped.
"""

from __future__ import annotations

import json
import re
import zlib
from dataclasses import dataclass, field
from pathlib import Path

_STRIP = re.compile(
    r"<system-reminder>.*?</system-reminder>"
    r"|<local-command-std(?:out|err)>.*?</local-command-std(?:out|err)>"
    r"|<(command-\w+)>.*?</\1>"
    # The harness writes this as a user record of its own. Left in, it becomes a turn
    # nobody typed — see trap 5 above.
    r"|\[Request interrupted by user[^\]]*\]",
    re.S,
)

_DECLINED = re.compile(
    r"user doesn'?t want to proceed"
    r"|tool use was rejected"
    r"|request interrupted by user"
    r"|user (?:rejected|denied|cancelled|canceled|aborted)",
    re.I,
)

EDIT_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})
READ_TOOLS = frozenset({"Read", "NotebookRead"})
SEARCH_TOOLS = frozenset({"Grep", "Glob"})


@dataclass
class Call:
    """One tool invocation and what came back."""

    tool: str
    params: dict
    key: str                     # stable identity of what it acted on
    step: int                    # index of the response that made it
    turn: int                    # index of the human turn it belongs to
    ok: bool | None = None       # None until the result arrives
    declined: bool = False       # the human said no; not a failure
    error_text: str = ""
    result_chars: int = 0
    result_head: str = ""        # enough to see a spill notice, not enough to cost anything


@dataclass
class Step:
    """One API response: thinking + prose + tool calls, merged from its records."""

    index: int
    turn: int
    model: str | None = None
    effort: str | None = None    # medium | high | xhigh | max
    depth: int = 0
    out_tokens: int = 0
    text: str = ""
    calls: list[Call] = field(default_factory=list)


@dataclass
class Compaction:
    """One point where the harness replaced the history above it with a summary.

    Read from the `compact_boundary` record rather than inferred. That distinction is the
    whole reason this ships: a detector can be wrong, and a marker the harness wrote about
    its own action cannot. A depth-drop heuristic was built for this and cut for want of
    evidence — the drop turns out to be real (100,212 -> 26,146 tokens on the transcript
    measured here, a ratio of 0.26 against a 0.6 threshold) but it is strictly worse than
    reading the record, so it stays cut.

    `step` is the index of the first response *after* the seam, which is what makes one
    field serve both triggers: an automatic compaction fires while a turn is being served,
    so its seam falls mid-turn, while a manual `/compact` lands between turns. Both were
    produced and measured; both reduce to "everything from this response onward was
    generated from a summary".

    `pre_tokens` and `post_tokens` are the harness's own figures for the compaction. **This
    docstring said for two days that there is no `post_tokens`** — that the field is set in
    the harness's source and assigned after serialisation, so the written record lacks it —
    and item 25's format census found that false. All four `compact_boundary` records on this
    machine carry `postTokens`, including both in `tests/fixtures/compacted.jsonl`, the file
    the original claim was measured against. The lesson recorded from it ("read a real record
    to find out what is there") was right; it was drawn from an example nobody had read.

    `post_tokens` is **not** the depth after the seam and must never be paired with a
    measured one: on the fixture the harness records 100,817 -> 2,455 while the next request
    measures 26,146, because the summary is re-sent with the system prompt, the tools and the
    project files behind it. The harness's own pair is internally consistent —
    `pre - post` accumulates exactly into `cumulative_dropped` — so both are read and reported
    as the harness's figures, beside the measured depths rather than mixed into them.
    """

    step: int
    trigger: str = "unknown"     # "auto" | "manual" — the harness's own word for it
    pre_tokens: int = 0
    post_tokens: int = 0         # the compacted payload, NOT the depth of the next request
    cumulative_dropped: int = 0  # the harness's running total across this session's seams
    summary_chars: int = 0       # size of the phantom turn this replaced
    preserved: int = 0           # messages kept verbatim past the seam, per the record
    turn: int = -1               # resolved after parsing: the turn owning `step`
    from_boundary: bool = False  # a `compact_boundary` record, not an orphan summary


@dataclass
class Turn:
    """One human instruction and everything the assistant did in response."""

    index: int
    prompt: str
    first_step: int
    last_step: int = -1


@dataclass
class Session:
    path: str = ""
    session_id: str = ""
    started: str = ""            # first record's timestamp; half of the fork fingerprint
    steps: list[Step] = field(default_factory=list)
    turns: list[Turn] = field(default_factory=list)
    calls: list[Call] = field(default_factory=list)
    compactions: list[Compaction] = field(default_factory=list)
    truncated: bool = False
    dropped_bytes: int = 0       # bytes ahead of the read window, when truncated
    model: str | None = None
    # Every record in the file by type, including the ones no branch below reads. Item 25:
    # this parser's failure mode is silence — a type it has no branch for is skipped without
    # a trace, so a renamed record leaves every count correct-looking and zero. The census
    # costs one dict increment per line and is what `formats.py` walks against its
    # declaration of what is handled and what is ignored on purpose.
    record_types: dict[str, int] = field(default_factory=dict)

    @property
    def depth(self) -> int:
        return self.steps[-1].depth if self.steps else 0

    def steps_of(self, turn: int) -> list[Step]:
        return [s for s in self.steps if s.turn == turn]

    def reply_text(self, turn: int, cap: int = 8000) -> str:
        return " ".join(s.text for s in self.steps_of(turn) if s.text)[:cap]


def clean(raw: str) -> str:
    """Strip harness boilerplate so a turn reads as what the human actually said."""
    return _STRIP.sub(" ", raw or "").strip()


def target_key(tool: str, params: dict) -> str:
    """A stable identity for the thing a call acted on."""
    if not isinstance(params, dict):
        return ""
    for k in ("file_path", "notebook_path", "path", "pattern", "url", "command", "query"):
        v = params.get(k)
        if isinstance(v, str) and v:
            return v if len(v) <= 200 else f"{v[:200]}#{zlib.crc32(v.encode()):x}"
    try:
        blob = json.dumps(params, sort_keys=True)[:400]
    except Exception:
        blob = str(params)[:400]
    return f"#{zlib.crc32(blob.encode()):x}"


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "\n".join(
        b.get("text") or "" for b in content if isinstance(b, dict) and b.get("type") == "text"
    )


def _result_text(block: dict) -> str:
    body = block.get("content")
    if isinstance(body, str):
        return body
    if isinstance(body, list):
        return "\n".join(
            b.get("text") or "" for b in body if isinstance(b, dict) and isinstance(b.get("text"), str)
        )
    return ""


def _record_kind(rec: dict) -> str:
    """How a record identifies itself, at the granularity the parser branches on.

    `system` is split by `subtype` because that is where the branch is: `compact_boundary`
    is read and `turn_duration` is not, and one census key for both would call a handled
    record and an ignored one the same thing.
    """
    if rec.get("type") == "system":
        return f"system/{rec.get('subtype')}"
    return str(rec.get("type"))


def _census(sess: Session, kind: str) -> None:
    sess.record_types[kind] = sess.record_types.get(kind, 0) + 1


def load(path: str | Path, max_bytes: int = 24 * 1024 * 1024) -> Session:
    """Parse a transcript. Never raises on malformed input."""
    sess = Session(path=str(path))
    p = Path(path)
    try:
        size = p.stat().st_size
        sess.truncated = size > max_bytes
        with p.open("rb") as fh:
            if sess.truncated:
                fh.seek(size - max_bytes)
                fh.readline()               # discard the record we landed in the middle of
                sess.dropped_bytes = fh.tell()
            raw = fh.read()
    except Exception:
        return sess

    pending: dict[str, Call] = {}
    prev_depth = 0
    last_group = None
    turn = -1

    for line in raw.split(b"\n"):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except Exception:
            _census(sess, "<unparsed>")
            continue
        if not isinstance(rec, dict):
            _census(sess, "<not-an-object>")
            continue
        _census(sess, _record_kind(rec))
        if not sess.started:
            sess.started = rec.get("timestamp") or ""
            sess.session_id = rec.get("sessionId") or ""
        if rec.get("isSidechain"):
            continue
        rtype = rec.get("type")
        msg = rec.get("message") if isinstance(rec.get("message"), dict) else {}

        if rtype == "assistant":
            group = rec.get("requestId") or msg.get("id")
            merging = group is not None and group == last_group and sess.steps
            usage = msg.get("usage") or {}
            depth = (
                int(usage.get("input_tokens") or 0)
                + int(usage.get("cache_creation_input_tokens") or 0)
                + int(usage.get("cache_read_input_tokens") or 0)
            )
            # There was a compaction detector here: a large drop in context depth was
            # read as the harness having replaced the history with a summary. It was
            # removed after being measured. Across 232 transcripts, depth above the 40k
            # floor rose monotonically in **4,155 of 4,155** consecutive measurements —
            # not one fall of any magnitude. That zero was ambiguous at the time and is
            # not any more: the harness states the seam outright, this file reads it
            # below, and on the produced transcript depth falls 100,212 -> 26,146. So
            # the rule was right and simply never triggered. The heuristic stays cut
            # anyway, because the record carries the trigger and the token count too and
            # cannot false-fire on a session that merely got smaller.
            if depth:
                prev_depth = depth

            if merging:
                step = sess.steps[-1]
                extra = _text_of(msg.get("content"))
                if extra:
                    step.text = f"{step.text}\n{extra}".strip()
            else:
                step = Step(
                    index=len(sess.steps),
                    turn=max(0, turn),
                    model=msg.get("model"),
                    effort=rec.get("effort"),
                    depth=depth or prev_depth,
                    out_tokens=int(usage.get("output_tokens") or 0),
                    text=_text_of(msg.get("content")),
                )
                sess.steps.append(step)
                if turn >= 0:
                    sess.turns[turn].last_step = step.index
            last_group = group
            if step.model is None:
                step.model = msg.get("model")
            if step.model:
                sess.model = step.model

            for b in msg.get("content") or []:
                if not isinstance(b, dict) or b.get("type") != "tool_use":
                    continue
                tool = b.get("name") or "?"
                params = b.get("input") or {}
                call = Call(
                    tool=tool,
                    params=params if isinstance(params, dict) else {},
                    key=target_key(tool, params),
                    step=step.index,
                    turn=step.turn,
                )
                step.calls.append(call)
                sess.calls.append(call)
                if b.get("id"):
                    pending[b["id"]] = call
            continue

        if rtype == "system" and rec.get("subtype") == "compact_boundary":
            meta = rec.get("compactMetadata")
            meta = meta if isinstance(meta, dict) else {}
            kept = meta.get("preservedMessages")
            kept = kept.get("uuids") if isinstance(kept, dict) else None
            sess.compactions.append(Compaction(
                step=len(sess.steps),
                trigger=str(meta.get("trigger") or "unknown"),
                pre_tokens=int(meta.get("preTokens") or 0),
                post_tokens=int(meta.get("postTokens") or 0),
                cumulative_dropped=int(meta.get("cumulativeDroppedTokens") or 0),
                preserved=len(kept) if isinstance(kept, list) else 0,
                from_boundary=True,
            ))
            continue

        if rtype != "user":
            continue

        content = msg.get("content")
        if isinstance(content, list):
            saw_result = False
            for b in content:
                if not isinstance(b, dict) or b.get("type") != "tool_result":
                    continue
                saw_result = True
                call = pending.pop(b.get("tool_use_id"), None)
                if call is None:
                    continue
                text = _result_text(b)
                call.result_chars = len(text)
                call.result_head = text[:300]
                if _DECLINED.search(text[:400]):
                    call.declined, call.ok = True, True
                    continue
                failed = bool(b.get("is_error")) or text[:80].lstrip().startswith(
                    ("Error:", "<tool_use_error>")
                )
                tur = rec.get("toolUseResult")
                if isinstance(tur, dict) and (tur.get("is_error") or tur.get("interrupted")):
                    failed = True
                call.ok = not failed
                if failed:
                    call.error_text = text[:2000]
            if saw_result:
                continue

        # Trap 6. Keyed on the flag, never on the summary's opening sentence: the record
        # says what it is, and matching its prose would also match a human quoting it.
        if rec.get("isCompactSummary"):
            at = len(sess.steps)
            for c in sess.compactions:
                if c.step == at:
                    c.summary_chars = len(_text_of(content) or "")
                    break
            else:
                # No boundary record alongside it. The summary alone still proves a seam,
                # and a seam with an unknown trigger beats a phantom turn.
                sess.compactions.append(Compaction(
                    step=at, summary_chars=len(_text_of(content) or "")))
            continue

        if rec.get("isMeta"):
            continue
        text = clean(_text_of(content))
        if text:
            turn = len(sess.turns)
            sess.turns.append(Turn(index=turn, prompt=text, first_step=len(sess.steps)))

    # Which exchange the seam falls in — the turn that owns the first post-seam response.
    # A seam with no response after it belongs to the last turn: the compaction is the
    # final thing that happened, which is exactly what a manual `/compact` looks like.
    for c in sess.compactions:
        c.turn = (sess.steps[c.step].turn if c.step < len(sess.steps)
                  else len(sess.turns) - 1)

    return sess


__all__ = [
    "Call", "Compaction", "Session", "Step", "Turn",
    "load", "clean", "target_key",
    "EDIT_TOOLS", "READ_TOOLS", "SEARCH_TOOLS",
]
