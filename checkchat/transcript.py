"""Read a Claude Code transcript into a shape the detectors can work on.

Self-contained on purpose — check-chat is meant to be installable on its own.

Five things about the wire format are easy to get wrong, and each of them silently
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
    truncated: bool = False
    dropped_bytes: int = 0       # bytes ahead of the read window, when truncated
    model: str | None = None

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
            continue
        if not isinstance(rec, dict):
            continue
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
            # not one fall of any magnitude — and no compaction marker exists anywhere
            # in the wire format to check a replacement against. See the roadmap: it is
            # blocked on a compacted transcript, not on a better threshold.
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

        if rec.get("isMeta"):
            continue
        text = clean(_text_of(content))
        if text:
            turn = len(sess.turns)
            sess.turns.append(Turn(index=turn, prompt=text, first_step=len(sess.steps)))

    return sess


__all__ = [
    "Call", "Session", "Step", "Turn",
    "load", "clean", "target_key",
    "EDIT_TOOLS", "READ_TOOLS", "SEARCH_TOOLS",
]
