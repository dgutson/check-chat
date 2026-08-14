"""Every assumption this tool makes about the harness's output, in one place.

Item 25. `check-chat` reads another program's files, and it is **published**: it runs on
machines whose Claude Code version the author has never seen. Three assumptions were named
in the known-limitations register (`HISTORY.md`) as load-bearing and unchecked, and the
shape of their failure is the one this project calls its most expensive — a **confident
zero**. `cli_probes` returned 0 for its
entire shipped life, was twice queued for deletion, and the number was correct every time.
A renamed record or a reworded notice produces exactly that, with nothing to look wrong.

**The trap this module exists inside.** "The format is absent" and "the thing never happened"
are the same observation from inside a count. So a probe here fires only when the session
carries *local* evidence that the shape should be present — a `compact_boundary` record whose
metadata is empty, a spill file read back with no notice anywhere that produced it. A probe
with no such precondition would be a mood, and the one written that way was deleted: a
cross-check of the declined-call wording against `toolUseResult.interrupted` looked sound
until it was measured, and `interrupted` is true in **0 of 4,841** tool results on this
corpus. A precondition that never holds is a detector that cannot fire.

**Why the record census is the important one.** The parser's failure mode is silence: a
record type it has no branch for is skipped without a trace. So every type is counted while
parsing and walked against two declarations — `HANDLED`, what has a branch, and `IGNORED`,
what is skipped on purpose and why. A type in neither is reported. This is `cli.TEXT_OMITS`
and `sweep.sendable_strings()` a third time: default-deny over somebody else's producer,
where the declaration is both the mechanism and its soft spot, since an entry in `IGNORED`
ends this module's interest in a record type permanently.

**Three assumptions carry no probe and say so.** Naming them is the deliverable for those:
a reader deciding whether to trust a zero can see which ones were confirmed against the
transcript in front of them and which are being taken on faith.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from . import detect
from .transcript import Session

# Record types the parser reads. Split by `system` subtype because that is where its branch
# is: `compact_boundary` is read and `turn_duration` is not.
HANDLED = {
    "assistant": "a model response — its text, tool calls, model, effort and token depth",
    "user": "a human turn, a tool result, or a compaction summary, told apart by flags",
    "system/compact_boundary": "the seam, and the harness's own figures for the compaction",
}

# Skipped on purpose, each with the reason it carries nothing this tool counts. An entry
# here is a claim about another program's records, so the ones that could plausibly hold a
# human turn were opened and read rather than inferred from their names.
IGNORED = {
    "attachment": "hook output and files attached to a prompt; the prompt is a `user` record",
    "last-prompt": "a `leafUuid` pointer to the prompt record, carrying no text of its own",
    "queue-operation": "a prompt typed while the previous one was still being answered. "
                       "Measured on this corpus: of 62 enqueued inside answered sessions, 37 "
                       "arrive again as a `user` record when they are sent, 22 are machine "
                       "`<task-notification>` tags, 2 are slash commands `clean()` strips "
                       "anyway, and 1 was never sent. Counting these would double a turn",
    "mode": "which mode the session is in — UI state, not conversation",
    "permission-mode": "the permission mode in force — UI state, not conversation",
    "ai-title": "the generated session title",
    "agent-name": "a subagent's display name; its traffic is `isSidechain` and excluded",
    "file-history-delta": "the editor's undo history for files this session changed",
    "file-history-snapshot": "the same, as a whole-file snapshot",
    "system/turn_duration": "wall-clock timing for a turn",
    "system/away_summary": "the harness's own summary of the session for a user who stepped "
                           "away — machine prose *about* the conversation, not in it",
    "system/local_command": "a `/slash` invocation, in the `<command-*>` form `clean()` "
                            "already strips out of a user record",
    "system/informational": "harness notices, including a hook's message when it blocked a "
                            "prompt",
}


@dataclass(frozen=True)
class Assumption:
    """One thing this tool believes about the harness's output.

    `degrades` is the field that decides whether an assumption matters, and it is written as
    what a *silent* drift produces rather than as "it would break": every one of these
    produces a plausible number, which is why they need naming at all.
    """

    key: str
    reads: str                                   # the record, field or wording depended on
    degrades: str                                # what a silent drift produces
    probe: Callable[[Session], str] | None = None
    why_unprobed: str = ""                       # required when there is no probe


def _unknown_records(sess: Session) -> str:
    unknown = {k: n for k, n in sess.record_types.items()
               if k not in HANDLED and k not in IGNORED}
    if not unknown:
        return ""
    rows = ", ".join(f"`{k}` x{n}" for k, n in
                     sorted(unknown.items(), key=lambda kv: (-kv[1], kv[0])))
    return (f"{len(unknown)} record type(s) this parser has no branch for and no note about, "
            f"skipped silently: {rows}")


def _depth_absent(sess: Session) -> str:
    # The precondition is "responses exist", which is the state in which a depth of 0 is a
    # claim rather than an absence. `collect()` refuses a session with none of them anyway.
    if not sess.steps or any(s.depth for s in sess.steps):
        return ""
    return (f"{len(sess.steps)} responses and not one carries a token count, so every depth "
            f"figure in this report is 0 by absence and not by measurement")


def _compaction_shape(sess: Session) -> str:
    # Only a seam the harness *stated* — an orphan `isCompactSummary` legitimately has no
    # trigger and no token count, and reporting that as drift would fire on a shape the
    # parser handles on purpose.
    stated = [c for c in sess.compactions if c.from_boundary]
    bad = [c for c in stated if c.trigger == "unknown" or not c.pre_tokens]
    if not bad:
        return ""
    return (f"{len(bad)} of {len(stated)} compaction records carry no `trigger` or no "
            f"`preTokens`: the seam is known and the harness's own figures for it are not, "
            f"so this report states the seam and calls its size 0")


def _spill_notice(sess: Session) -> str:
    # Spill has two independent signatures and the code needs both: the notice names the file
    # the payload went to, and the path is what a later Read of it looks like. A file read
    # back out of `tool-results/` with no notice anywhere in the session is the notice's
    # wording having moved — the robust half surviving while the fragile half stops matching.
    read_back = any(detect.SPILL_PATH.search(detect.path_of(c)) for c in sess.calls)
    if not read_back:
        return ""
    if any(n in (c.result_head or "") for c in sess.calls for n in detect.SPILL_NOTICE):
        return ""
    return ("a file was read back out of `tool-results/` and no result in this session "
            f"carries the notice that puts one there ({' / '.join(detect.SPILL_NOTICE)}): "
            f"`spill` can still see this one by its path and would miss one without it")


ASSUMPTIONS: list[Assumption] = [
    Assumption(
        key="record_types",
        reads="`type`, and `subtype` on a `system` record",
        degrades="a renamed record type is skipped without a trace, so every count stays "
                 "arithmetically correct and describes a fraction of the conversation",
        probe=_unknown_records,
    ),
    Assumption(
        key="depth",
        reads="`message.usage.{input,cache_creation_input,cache_read_input}_tokens`",
        degrades="every depth is 0 — `grounding`, the compaction seams and the header all "
                 "report a context size of zero as though it had been measured",
        probe=_depth_absent,
    ),
    Assumption(
        key="compaction_metadata",
        reads="`compactMetadata.trigger` / `.preTokens` on a `compact_boundary` record",
        degrades="the seam is still found and its size reads as 0 tokens at trigger "
                 "`unknown` — a caveat that qualifies the report with a fabricated figure",
        probe=_compaction_shape,
    ),
    Assumption(
        key="spill_notice",
        reads="`persisted-output` / `saved to` in a tool result's first 300 characters",
        degrades="`spill` sees only the spills a later Read names by path, and reports the "
                 "rest as nothing happening",
        probe=_spill_notice,
    ),
    Assumption(
        key="declined_wording",
        reads="`transcript._DECLINED` — the harness's English for a call the human refused",
        degrades="trap 4 inverted: a person declining a command is counted as the model "
                 "failing, which punishes exactly the users who review what an agent does",
        why_unprobed="there is no structural counter-signal to cross-check it against. "
                     "`toolUseResult.interrupted` looked like one and is true in 0 of 4,841 "
                     "results on this corpus, while the wording matches 32 of them",
    ),
    Assumption(
        key="interrupt_marker",
        reads="`[Request interrupted by user…]`, stripped by `transcript._STRIP`",
        degrades="trap 5 returns: a turn nobody typed lands between a reply and the "
                 "objection to it, and `sycophancy` reports a confident zero for the "
                 "highest-signal moment it has",
        why_unprobed="the marker is an ordinary `str` user record with no flag to key on, so "
                     "its absence and a session without interruptions are the same reading",
    ),
    Assumption(
        key="blinding",
        reads="`tools: []` on a subagent dispatch granting no tools",
        degrades="the judge can read the unblinded transcript it was told not to open",
        why_unprobed="a dispatch behaviour, not a fact about any transcript — nothing in the "
                     "file this module is handed can speak to it. Already carried as a Known "
                     "Limitation, and re-test if the harness ever supports an empty grant",
    ),
]


def probe(sess: Session) -> list[str]:
    """Every assumption whose shape this transcript contradicts.

    Empty is the expected answer and is not the same as "all seven hold": three carry no
    probe by construction, which is why `unverifiable` is reported beside this.
    """
    return [w for a in ASSUMPTIONS if a.probe for w in (a.probe(sess),) if w]


__all__ = ["Assumption", "ASSUMPTIONS", "HANDLED", "IGNORED", "probe"]
