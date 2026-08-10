"""The deterministic half of the diagnosis: everything computable, computed here.

Nothing in this module asks a model anything. That is the point — the rule this
plugin exists to enforce is "don't spend tokens on what a script can do", and a
plugin that violated it while reporting on it would be worthless.

Every detector below fires on real transcripts; the ones that looked equally
plausible but measured at chance were deliberately left out, and the docstrings say
which, so nobody rebuilds them from intuition. Two rules shaped the design:

* **Rank, don't alarm.** A signal present in 86% of sessions cannot discriminate.
  Its value is ordering the worst offenders, so it ships as a sorted table.
* **Subtract the legitimate cases first.** The naive redundant-read rule overstates
  waste by 66% because re-reading a file you just edited is correct behaviour. A
  detector that calls good work waste teaches the user to ignore it.
"""

from __future__ import annotations

import os
import re
import statistics
from collections import Counter, defaultdict

from . import transcript
from .transcript import EDIT_TOOLS, READ_TOOLS, SEARCH_TOOLS, Call, Session

DUMP_MIN = 5000            # measured floor: below this, payloads are not the problem
REREAD_MIN = 3             # no-mutation repeats before it is worth mentioning
PRODUCER_MIN = 3           # re-runs of one expensive pipeline head

GROUND_TOOLS = READ_TOOLS | SEARCH_TOOLS | frozenset({"WebFetch", "WebSearch"})

# A shell command that pours a file into context, and the filters that mean it didn't.
_DUMPY_CMD = re.compile(r"(?:^|[;&|]\s*)(?:cat|head|tail|sed -n)\b")
_FILTERED = re.compile(r"\b(?:grep|rg|jq|gron|fastgron|awk|wc\s+-l|python3?\s+-c)\b")

# A *windowed* access — evidence that only part of the file was ever needed.
_WINDOWED_CMD = re.compile(r"\b(?:grep|rg|sed\s+-n|awk)\b")

# Anything that could have changed a file, so a later re-read is re-grounding.
_MUT_REPO = re.compile(r"\bgit\s+(?:checkout|apply|pull|stash|reset|merge|rebase)\b")
# `(?<![0-9&])>(?!&)` is a redirect to a *file*. Plain `>` also matches `2>/dev/null`
# and `2>&1`, which write nothing — and counting those as mutations makes every
# command its own alibi, which silently zeroes out the repeated-producer detector.
_MUT_CMD = re.compile(
    r"(?<![0-9&])>(?!&)|(?:^|[;&|]\s*)(?:tee|mv|cp|touch|patch)\b|\bsed\s+-i|\bdd\b"
)
_PATHY = re.compile(r"[A-Za-z0-9_./~-]*[A-Za-z0-9_-]\.[A-Za-z0-9]+|[A-Za-z0-9_.~-]*/[A-Za-z0-9_.-]+")

# The harness's own notice that a result was too big to keep.
_SAVED_TO = re.compile(r"saved to:\s*(\S+)")
_SPILL_PATH = re.compile(r"tool-results/[\w.-]+\.\w+")

# `foo bar --help`, plus the wrappers that hide the real command name.
_HELP = re.compile(r"([\w./-]+(?:\s+[a-z][\w-]*){0,2})\s+--help")
_WRAPPERS = re.compile(
    r"^(?:cd\s+\S+\s*(?:&&|;)\s*|sudo\s+(?:-A\s+)?|env\s+\w+=\S+\s+|timeout\s+\S+\s+|nohup\s+)+"
)


def _path_of(call: Call) -> str:
    p = call.params
    v = p.get("file_path") or p.get("notebook_path") or p.get("path")
    return v if isinstance(v, str) else ""


def _cmd_of(call: Call) -> str:
    v = call.params.get("command")
    return v if isinstance(v, str) else ""


# ---------------------------------------------------------------- 1. context dumps

def dump_reason(call: Call) -> str:
    """Why this call was a context dump, or "" if it wasn't."""
    if call.result_chars < DUMP_MIN or call.declined:
        return ""
    if call.tool in READ_TOOLS:
        p = call.params
        if not p.get("limit") and not p.get("offset"):
            return "whole file read into context"
    elif call.tool == "Bash":
        cmd = _cmd_of(call)
        if _DUMPY_CMD.search(cmd) and not _FILTERED.search(cmd):
            return "shell dump with no filter in the pipeline"
    elif call.tool == "WebFetch":
        return "fetched page held in full"
    return ""


def dumps(sess: Session, top: int = 5) -> dict:
    """The biggest payloads, ranked by what they cost to carry — not pass/fail.

    Carry cost is `chars x responses that came after`: the same payload read early
    is re-sent with every later request, so position matters as much as size. This
    fires in most sessions, which is exactly why it must rank rather than alarm.
    """
    n_steps = max(1, len(sess.steps))
    rows = []
    for c in sess.calls:
        why = dump_reason(c)
        if not why:
            continue
        remaining = max(0, n_steps - c.step)
        rows.append({
            "tool": c.tool,
            "target": _path_of(c) or _cmd_of(c)[:120] or c.key[:120],
            "chars": c.result_chars,
            "step": c.step,
            "turn": c.turn,
            "responses_after": remaining,
            "carry_cost": c.result_chars * remaining,
            "why": why,
        })

    total_chars = sum(c.result_chars for c in sess.calls) or 1
    dumped = sum(r["chars"] for r in rows)
    rows.sort(key=lambda r: r["carry_cost"], reverse=True)
    return {
        "count": len(rows),
        "calls_total": len(sess.calls),
        "chars": dumped,
        "share_of_tool_bytes": round(dumped / total_chars, 3),
        "top": rows[:top],
    }


# ------------------------------------------------------- 2. partial-use proof

def partial_use(sess: Session) -> list[dict]:
    """Dumps the session later proved it only needed a slice of.

    For each dumped file, look *forward* for a windowed access to the same file: a
    `Read` with limit/offset, or a grep/sed/awk naming it. That later access is
    machine-checkable proof that the whole-file read was unnecessary — which makes
    this the only detector here carrying its own ground truth. Everything else is a
    descriptive statistic with no outcome label, so this is the one to lead with.
    """
    out = []
    for c in sess.calls:
        if not dump_reason(c):
            continue
        path = _path_of(c)
        if not path:
            continue
        base = os.path.basename(path)
        for later in sess.calls:
            if later.step <= c.step:
                continue
            if later.tool in READ_TOOLS and _path_of(later) == path:
                if later.params.get("limit") or later.params.get("offset"):
                    out.append(_proof(c, path, later, f"later Read of the same file used "
                                      f"limit/offset"))
                    break
            elif later.tool == "Bash":
                cmd = _cmd_of(later)
                if base and base in cmd and _WINDOWED_CMD.search(cmd):
                    out.append(_proof(c, path, later, f"later `{cmd.strip()[:70]}` searched it"))
                    break
    out.sort(key=lambda r: r["chars"], reverse=True)
    return out


def _proof(dump: Call, path: str, later: Call, how: str) -> dict:
    return {
        "path": path,
        "chars": dump.result_chars,
        "step": dump.step,
        "turn": dump.turn,
        "proof_step": later.step,
        "proof": how,
    }


# --------------------------------------------- 3. mutation-aware redundant re-reads

def mutation_index(
    sess: Session, exclude: frozenset[int] | set[int] | None = None
) -> tuple[dict[str, list[int]], list[int]]:
    """When each file was (or might have been) changed.

    Deliberately over-inclusive — a `git pull` is treated as touching everything —
    because over-calling mutation only ever *suppresses* a waste finding, and falsely
    accusing someone of waste costs more than missing a case.

    `exclude` holds `id()`s of calls that must not count as mutations. A detector
    asking "did anything change between two runs of X" has to leave X's own runs out,
    or every command becomes its own alibi.
    """
    per_file: dict[str, list[int]] = defaultdict(list)
    repo_wide: list[int] = []

    for c in sess.calls:
        if c.declined or (exclude and id(c) in exclude):
            continue
        if c.tool in EDIT_TOOLS:
            p = _path_of(c)
            if p:
                per_file[os.path.basename(p)].append(c.step)
            continue
        if c.tool != "Bash":
            continue
        cmd = _cmd_of(c)
        if _MUT_REPO.search(cmd):
            repo_wide.append(c.step)
        elif _MUT_CMD.search(cmd):
            for tok in _PATHY.findall(cmd):
                per_file[os.path.basename(tok)].append(c.step)
    return per_file, sorted(repo_wide)


def rereads(sess: Session) -> dict:
    """Re-reads of a file that nothing had changed in between.

    The naive version of this rule — count any repeated Read — overstates waste by
    about two thirds, because most repeats follow an edit and are correct
    re-grounding. Subtracting those is the whole detector.
    """
    per_file, repo_wide = mutation_index(sess)
    by_path: dict[str, list[Call]] = defaultdict(list)
    for c in sess.calls:
        if c.tool in READ_TOOLS and not c.declined and c.ok is not False:
            p = _path_of(c)
            if p:
                by_path[p].append(c)

    rows, wasted, regrounding = [], 0, 0
    for path, calls in by_path.items():
        if len(calls) < 2:
            continue
        muts = sorted(per_file.get(os.path.basename(path), []) + repo_wide)
        clean = 0
        for a, b in zip(calls, calls[1:]):
            if any(a.step <= m <= b.step for m in muts):
                regrounding += 1
            else:
                clean += 1
                wasted += b.result_chars
        if clean:
            rows.append({
                "path": path,
                "reads": len(calls),
                "unchanged_repeats": clean,
                "chars": sum(c.result_chars for c in calls[1:]),
                "steps": [c.step for c in calls],
            })

    rows.sort(key=lambda r: r["chars"], reverse=True)
    total = sum(r["unchanged_repeats"] for r in rows)
    return {
        "repeats_without_change": total,
        "repeats_after_edit": regrounding,   # legitimate; reported so the number is honest
        "chars": wasted,
        "fires": total >= REREAD_MIN,
        "files": rows[:5],
    }


# ------------------------------------------------------------------ 4. batching

def batching(sess: Session) -> dict:
    """How many tool calls the assistant issues per response.

    Not waste on its own — it is the multiplier. Every other finding here costs one
    round trip or several depending on this number, so it is the only figure that
    explains magnitude rather than counting events.
    """
    counts = [len(s.calls) for s in sess.steps if s.calls]
    if not counts:
        return {"responses_with_tools": 0}
    solo = sum(1 for n in counts if n == 1)
    return {
        "responses_with_tools": len(counts),
        "calls": sum(counts),
        "solo_share": round(solo / len(counts), 3),
        "mean": round(statistics.mean(counts), 2),
        "median": statistics.median(counts),
        "max": max(counts),
    }


# --------------------------------------------------------------------- 5. spill

def spill(sess: Session) -> list[dict]:
    """Results the harness judged too big to keep, that were then read back in.

    The harness had already ruled on this payload: it did not fit. Reading the spill
    file undoes that ruling. Rare — one unambiguous case in the corpus this was built
    from, where a 2,091-char kept result was re-ingested as 81,056 chars, a 39x
    amplification and the single largest result measured. Reported as n=1 evidence,
    not as a rate.
    """
    spilled: dict[str, Call] = {}
    for c in sess.calls:
        head = c.result_head or ""
        if "persisted-output" not in head and "saved to" not in head:
            continue
        for m in _SAVED_TO.finditer(head):
            spilled[m.group(1).rstrip(".,)\"'")] = c

    out = []
    for c in sess.calls:
        if c.tool not in READ_TOOLS:
            continue
        path = _path_of(c)
        if not path:
            continue
        origin = spilled.get(path)
        if origin is None and not _SPILL_PATH.search(path):
            continue
        if origin is not None and origin.step >= c.step:
            continue
        kept = origin.result_chars if origin else 0
        out.append({
            "path": path,
            "read_chars": c.result_chars,
            "kept_chars": kept,
            "amplification": round(c.result_chars / kept, 1) if kept else None,
            "step": c.step,
            "turn": c.turn,
        })
    return sorted(out, key=lambda r: r["read_chars"], reverse=True)


# ----------------------------------------------------------------- 6. producers

def producers(sess: Session) -> list[dict]:
    """One expensive command re-run over unchanged input, only to filter it differently.

    Keyed on everything left of the first pipe, so `strings big.bin | grep A` and
    `strings big.bin | grep B` collapse to one producer run twice. The flagship case
    in the corpus ran a `strings` over a 100MB binary fifteen times, differing only
    in the grep pattern — that output should have been computed once.

    Two guards keep the ordinary edit-test loop out of it, and both are load-bearing.
    Without them this fires on `pytest | tail`, `./test.sh`, `./bench.sh` — re-running
    the tests after each edit is the correct thing to do, not waste:

    * **No intervening mutation.** If a file changed between two runs, the second run
      is measuring something new.
    * **The filter actually varies.** Re-running the same pipeline unchanged is a
      repeated measurement; re-running it with a different `grep` is the signature of
      having thrown away output that was already computed.
    """
    groups: dict[str, list[Call]] = defaultdict(list)
    for c in sess.calls:
        if c.tool != "Bash" or c.declined:
            continue
        cmd = _cmd_of(c).strip()
        if "|" not in cmd:
            continue
        head = cmd.split("|")[0].strip()
        if not head or re.match(r"cat\s*(?:>|<<)", head):     # heredoc, not a producer
            continue
        groups[head].append(c)

    rows = []
    for head, calls in groups.items():
        if len(calls) < PRODUCER_MIN:
            continue
        per_file, repo_wide = mutation_index(sess, exclude={id(c) for c in calls})
        mutations = sorted(repo_wide + [s for steps in per_file.values() for s in steps])
        unchanged = sum(
            1 for a, b in zip(calls, calls[1:])
            if not any(a.step <= m <= b.step for m in mutations)
        )
        variants = sorted({_cmd_of(c).split("|", 1)[1].strip()[:60] for c in calls})
        # Three *provably* redundant re-runs, not three runs of which some were
        # redundant. At two, a test script re-run twice between edits qualifies, and
        # re-running tests is the correct thing to do.
        if unchanged < PRODUCER_MIN or len(variants) < 2:
            continue
        rows.append({
            "producer": head[:160],
            "runs": len(calls),
            "reruns_on_unchanged_input": unchanged,
            "chars": sum(c.result_chars for c in calls),
            "steps": [c.step for c in calls],
            "variants": variants[:6],
        })
    return sorted(rows, key=lambda r: r["runs"], reverse=True)


# ---------------------------------------------------------------- 7. CLI probes

def _family(cmd: str) -> str:
    """The command family behind a `--help`, with wrappers stripped."""
    stripped = _WRAPPERS.sub("", cmd.strip())
    m = _HELP.search(stripped)
    if not m:
        return ""
    fam = re.sub(r"\s+", " ", m.group(1).strip())
    return os.path.basename(fam.split()[0]) + (" " + " ".join(fam.split()[1:]) if len(fam.split()) > 1 else "")


def cli_probes(sess: Session, others: list[Session] | None = None) -> dict:
    """Command-line syntax the session had to re-derive by asking for `--help`.

    A family probed in more than one session is the strongest "this should be a
    skill" signal available, but it is also the easiest to fake: forked transcripts
    share history, so an undeduplicated corpus manufactures cross-session repeats
    out of one session counted twice. `others` must already be fork-deduplicated —
    `discover.siblings()` does that — and this function will not count a family as
    cross-session on the strength of a single other log.
    """
    here = Counter()
    for c in sess.calls:
        if c.tool == "Bash" and not c.declined:
            fam = _family(_cmd_of(c))
            if fam:
                here[fam] += 1

    across: dict[str, int] = Counter()
    for other in others or []:
        fams = {_family(_cmd_of(c)) for c in other.calls if c.tool == "Bash"}
        for fam in fams - {""}:
            across[fam] += 1

    return {
        "probes": sum(here.values()),
        "families": [
            {"family": f, "here": n, "other_sessions": across.get(f, 0)}
            for f, n in here.most_common(8)
        ],
        "recurring": sorted(
            (f for f, n in across.items() if n >= 1 and here.get(f)),
            key=lambda f: -(across[f] + here[f]),
        )[:5],
        "sessions_compared": len(others or []),
    }


# ------------------------------------------------------------- 8. grounding decay

def grounding(sess: Session) -> dict | None:
    """Whether the assistant keeps checking reality as the context fills.

    Reported only against the session's own first quartile, never against a fixed
    threshold. The raw version of this number looks dramatic (7.6x by context depth)
    and mostly is not real: re-anchored on human turns it flattens to a
    non-monotonic ~3x, and the independent discipline proxy shows no trend with
    depth at all. It is here so the rot dimension is genuinely measured rather than
    asserted — treat it as weak evidence and say so.
    """
    steps = sess.steps
    if len(steps) < 8:
        return None
    q = len(steps) // 4
    ratios = []
    for i in range(4):
        chunk = steps[i * q: (i + 1) * q] if i < 3 else steps[3 * q:]
        ground = sum(1 for s in chunk for c in s.calls if c.tool in GROUND_TOOLS)
        edits = sum(1 for s in chunk for c in s.calls if c.tool in EDIT_TOOLS)
        ratios.append(round(ground / max(1, edits), 2))
    base = ratios[0] or 1.0
    return {
        "quartile_ground_per_edit": ratios,
        "vs_own_baseline": [round(r / base, 2) for r in ratios],
        "depth_tokens": sess.depth,
        "note": "weak signal; ratio against this session's own first quartile only",
    }


# ------------------------------------------------------------------- failures

def failures(sess: Session) -> dict:
    """A raw count of failed calls — never a scored dimension.

    Repeated-error clustering was measured at one true instance in 1,968 results,
    and the obvious implementation scored 0/2 precision and 0/1 recall: its only
    hits were deliberate existence probes and a test being actively fixed. So this
    counts and stops.
    """
    bad = [c for c in sess.calls if c.ok is False]
    causes = Counter(re.sub(r"\d+|/\S+", "N", (c.error_text or "")[:120]) for c in bad)
    return {
        "failed": len(bad),
        "declined_by_user": sum(1 for c in sess.calls if c.declined),
        "distinct_causes": len(causes),
    }


# --------------------------------------------------- 10. completeness of the record

def continuity(sess: Session) -> dict:
    """Was the whole transcript read, or is every count above computed on a fragment?

    A transcript past the read cap is read from its **tail**, so every count is then
    computed on the remainder while looking exactly like a count over the whole thing.
    That was true from the first version and reported nowhere, which is the worst of
    the three available states: measured, wrong, and confident.

    This is not a detector and cannot be wrong: the condition is `size > cap`, a fact
    this tool creates about its own read. It reports magnitude rather than a boolean
    because "truncated" with no number invites the reader to assume it was marginal.

    A **compaction** clause lived here too, and was cut for lack of evidence rather
    than lack of value — the mechanism is real and the reasoning about it is preserved
    in the roadmap. Nothing detects it today, so nothing claims to.
    """
    dropped_mb = sess.dropped_bytes / (1024 * 1024)
    warnings = []
    if sess.truncated:
        warnings.append(
            f"transcript truncated: the first {dropped_mb:,.1f} MB were never read — "
            f"every count here is a lower bound computed on the remainder"
        )
    return {
        "fired": bool(sess.truncated),
        "truncated": sess.truncated,
        "dropped_bytes": sess.dropped_bytes,
        "warnings": warnings,
        "summary": "; ".join(warnings) or "whole transcript read",
    }


__all__ = [
    "dumps", "dump_reason", "partial_use", "rereads", "mutation_index",
    "batching", "spill", "producers", "cli_probes", "grounding", "failures",
    "continuity",
]
