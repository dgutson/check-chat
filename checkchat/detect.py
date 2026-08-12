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

# The substring a transcript must contain before it can possibly hold a probe. Used to
# pre-filter the corpus in `discover.siblings`, so a bounded scan budget is spent only on
# sessions that could contribute — see that docstring for why that is correctness, not
# just speed.
PROBE_NEEDLE = "--help"

# `foo bar --help`, plus the wrappers that hide the real command name.
#
# Horizontal whitespace only, never `\s`: a Bash call is routinely a multi-line script,
# and `\s` happily spans the newline, splicing the tail of one line onto the `--help` of
# the next and inventing a command nobody ran. Measured on the corpus: `pip3 install
# --help` was reported as the family `--version pip3 install`, glued across a line break.
# The roadmap has this same class of error twice under "do not glue lines together".
#
# Three trailing words, not two, because the leftmost-match rule punishes a short limit
# in a way that is easy to miss: at two, `claude plugin marketplace add --help` cannot
# match starting at `claude`, so the match slides right and the family comes out as
# `plugin marketplace add` — a name implying a `plugin` executable that does not exist.
_H = r"[^\S\n]"
_HELP = re.compile(rf"([\w./-]+(?:{_H}+[a-z][\w-]*){{0,3}}){_H}+--help")
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
                # Shell code, never the whole command: a commit message naming the file, or
                # an `echo "=== reading SKILL.md ==="`, mentions it without searching it.
                # Item 13 built `_shell_code` for this and applied it to `cli_probes` alone;
                # the identical hole sat here in the *proof* tier, where the consequence is
                # worse — 6 of 48 proofs on the corpus were a file's name appearing in data,
                # reported as machine-checkable evidence of waste. Item 21 printed them, which
                # is how anyone saw it. Losing a quoted filename argument is the acceptable
                # direction: a missed proof costs recall, a false one costs the tier its word.
                code = _shell_code(cmd)
                if base and base in code and _WINDOWED_CMD.search(code):
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


def _span(call: Call) -> tuple[float, float] | None:
    """Which lines a read covered. `None` means the whole file, which covers everything."""
    p = call.params if isinstance(call.params, dict) else {}
    off, lim = p.get("offset"), p.get("limit")
    if not isinstance(off, int) and not isinstance(lim, int):
        return None
    start = off if isinstance(off, int) else 0
    return (start, start + lim if isinstance(lim, int) else float("inf"))


def _overlaps(a, b) -> bool:
    if a is None or b is None:
        return True
    return a[0] < b[1] and b[0] < a[1]


def rereads(sess: Session) -> dict:
    """Re-reads of a file that nothing had changed in between.

    Two things have to be subtracted, and each was measured to be most of the number.

    The naive rule — count any repeated Read — overstates waste by about two thirds,
    because most repeats follow an edit and are correct re-grounding.

    The second is the same mistake one level down, and it shipped: grouping by path alone
    counts **different slices of one file** as a repeat. Reading lines 1-70 and then
    300-405 fetches nothing twice, and on the corpus that was **27 of 38** reported
    repeats — 71% — collapsing the firing rate from 6 of 54 sessions to 1. An
    `evidenced`-tier check telling a user they wasted tokens they did not waste is item
    4's failure with the sign flipped, so spans are compared and only overlapping reads
    count. A whole-file read has no span and overlaps everything, correctly.

    Pairing is against **every** earlier still-valid read rather than the previous one,
    because consecutive pairing gets `A, B, A` wrong: both pairs are disjoint while the
    file's first slice was genuinely fetched twice.
    """
    per_file, repo_wide = mutation_index(sess)
    by_path: dict[str, list[Call]] = defaultdict(list)
    for c in sess.calls:
        if c.tool in READ_TOOLS and not c.declined and c.ok is not False:
            p = _path_of(c)
            if p:
                by_path[p].append(c)

    rows, wasted, regrounding, disjoint = [], 0, 0, 0
    for path, calls in by_path.items():
        if len(calls) < 2:
            continue
        muts = sorted(per_file.get(os.path.basename(path), []) + repo_wide)
        clean = 0
        for i, b in enumerate(calls[1:], start=1):
            sb = _span(b)
            repeat = still_valid = False
            for a in calls[:i]:
                if any(a.step <= m <= b.step for m in muts):
                    continue            # changed since `a`; re-reading it is re-grounding
                still_valid = True
                if _overlaps(_span(a), sb):
                    repeat = True
                    break
            if repeat:
                clean += 1
                wasted += b.result_chars
            elif still_valid:
                disjoint += 1           # a different part of the file: not waste at all
            else:
                regrounding += 1
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
        # Both subtractions are reported, because a number is credible only next to what
        # it excludes — and each of these was once counted as waste.
        "repeats_after_edit": regrounding,
        "repeats_disjoint_slices": disjoint,
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

# `<<DELIM`, `<<'DELIM'`, `<<-DELIM` — the start of a heredoc, whose body is data the
# shell feeds to a command rather than commands the shell runs. Requiring a word
# character after the `<<` keeps arithmetic left-shift (`$((1 << 2))`) out.
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][\w-]*)\1")


def _shell_code(cmd: str) -> str:
    """The parts of a Bash command the shell will execute, with *data* removed.

    Found by running `/check-chat` on the session that had just finished repairing this
    detector, which is the only reason it was found: it reported `pip3 install` as syntax
    re-derived here *and* in another session, and no such command had been run. `_family`
    scanned the whole `command` parameter, so text that merely *discusses* a command
    counted as running it.

    Two kinds of data carry command-shaped text, and both had to go — the first attempt
    fixed only one and the corpus said so:

    * **Heredoc bodies.** The phantom came from a `git commit -F - <<'EOF'` body: a commit
      message describing the `--help` parse bug fixed minutes earlier.
    * **Quoted literals.** Stripping heredocs alone left the firing count unchanged at
      10 of 18 sessions, because the same phantom arrived again through
      `echo "=== did I actually run 'pip3 install --help' ... ==="` — a shell label.

    The hole predates the cross-project change, but that change **raised its
    consequence**: a bogus family used to inflate a count inside one session, and can now
    manufacture a cross-session "this should be a skill" claim, which is the loudest thing
    this detector says. Note the shape of the near-miss — the cross-project fix was
    measured against the corpus, the corpus contained no prose about `--help`, and so
    nothing failed until the tool was pointed at a session that wrote *about* commands.
    A corpus cannot contain the artifact a new kind of session will produce.
    """
    return _strip_quoted(_strip_heredocs(cmd))


def _strip_quoted(cmd: str) -> str:
    """Replace quoted literals with a space, one line at a time.

    **Line-local on purpose.** An unbalanced quote is ordinary in these commands — an
    apostrophe in an `echo`, a `sed` expression — and letting the quote state run to the
    end of a multi-line script would swallow every real command after it. Confined to one
    line, a mis-pair costs that line and nothing else.

    Command substitution is deliberately not carved out. `$(gron --help)` inside quotes
    really does run a probe, so stripping it loses a true positive — but there are **0 of
    those on the corpus** and the carve-out costs a nested parser, so it is left undone
    and written down here instead of guessed at.
    """
    out: list[str] = []
    for line in cmd.split("\n"):
        buf: list[str] = []
        quote = ""
        i = 0
        while i < len(line):
            ch = line[i]
            if quote:
                if ch == "\\" and quote == '"':      # \" does not close a double quote
                    i += 2
                    continue
                if ch == quote:
                    quote = ""
                    buf.append(" ")                  # the literal becomes a word boundary
                i += 1
                continue
            if ch in "'\"":
                quote = ch
                i += 1
                continue
            buf.append(ch)
            i += 1
        out.append("".join(buf))
    return "\n".join(out)


def _strip_heredocs(cmd: str) -> str:
    """Drop heredoc bodies, keeping the lines that actually execute."""
    lines = cmd.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        # One line may open several heredocs; their bodies then follow in that order.
        delims = [m.group(2) for m in _HEREDOC.finditer(line)]
        i += 1
        for delim in delims:
            while i < len(lines) and lines[i].strip() != delim:
                i += 1
            i += 1                      # and the terminator line itself
    return "\n".join(out)


def _family(cmd: str) -> str:
    """The command family behind a `--help`, looking only at what the shell would run."""
    stripped = _WRAPPERS.sub("", _shell_code(cmd).strip())
    m = _HELP.search(stripped)
    if not m:
        return ""
    fam = re.sub(r"\s+", " ", m.group(1).strip())
    return os.path.basename(fam.split()[0]) + (" " + " ".join(fam.split()[1:]) if len(fam.split()) > 1 else "")


def cli_probes(sess: Session, others: list[Session] | None = None) -> dict:
    """Command-line syntax the session had to re-derive by asking for `--help`.

    A family probed in more than one session is the strongest "this should be a skill"
    signal available, but it is also the easiest to fake: forked transcripts share
    history, so an undeduplicated corpus manufactures cross-session repeats out of one
    session counted twice. `others` must already be fork-deduplicated —
    `discover.siblings()` does that.

    **What `others` must contain, and the bug that lived here.** For two years of
    roadmap this function's cross-session half returned zero on every real session, and
    it was nearly cut for it. The cause was not this code: `others` was every session
    *in the same project directory*, and re-derived CLI syntax is inherently a
    cross-*project* pattern — you relearn `claude plugin` syntax in whatever repo you
    happen to be sitting in. Note the giveaway, because it is the general lesson: the
    payoff is a **skill**, and a skill is installed per user, not per directory, so the
    comparison population was answering a narrower question than the detector asks.
    Given machine-wide `others` it fires on the same corpus that measured zero — 8 of 51
    sessions, `claude plugin` re-derived in 4 sessions across 4 separate projects.

    A prior docstring here claimed this "will not count a family as cross-session on the
    strength of a single other log", i.e. a threshold of two. The code has always said
    one, so the claim was a guard that did not exist — removed rather than implemented,
    because the fork protection it was describing is really delivered by the dedup in
    `siblings()`, and a second unmeasured threshold on top of that is how you get a
    detector that cannot fire.
    """
    here = Counter()
    for c in sess.calls:
        if c.tool == "Bash" and not c.declined:
            fam = _family(_cmd_of(c))
            if fam:
                here[fam] += 1

    across: dict[str, int] = Counter()
    for other in others or []:
        # `declined` excluded on both sides: a command the user refused was never run,
        # so its syntax was never re-derived. `here` has always filtered it; this side
        # did not, which let a refused probe in another session corroborate this one.
        fams = {_family(_cmd_of(c)) for c in other.calls
                if c.tool == "Bash" and not c.declined}
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

def compaction(sess: Session) -> dict:
    """Did the harness replace the conversation's own history with a summary?

    Like `continuity`, this is not a detector and cannot be wrong: the condition is a
    `compact_boundary` record the harness wrote about its own action. That is why it can
    ship where the thing it replaces could not — a depth-drop heuristic was built for this
    and cut, and the drop turns out to be real (100,212 -> 26,146 tokens across the first
    seam measured, ratio 0.26 against the 0.6 threshold it used) but reading a marker beats
    inferring one, so the heuristic stays cut rather than being restored alongside.

    **Why it is a caveat and not a finding.** Everything above a seam is available to the
    assistant only as a summary, which changes what three of the judge's items *mean*
    rather than adding to them: re-asking for something settled above the seam is correct
    behaviour rather than `confusion`, a constraint stated above it was lost rather than
    disregarded, and a mismatch with earlier material is amnesia rather than contradiction.
    A judge that cannot see the seam scores all three as degradation, which is the exact
    false positive this plugin exists to avoid.

    And it pays: the two readings imply **opposite repairs**. Restating the constraint
    fixes a compaction loss; starting a fresh chat does not — it is the one degradation-
    shaped complaint where "start a new conversation" is precisely the wrong advice.
    """
    rows = []
    for c in sess.compactions:
        # `None`, not 0, when there is no response on one side of the seam — a manual
        # `/compact` as the last thing that happened has nothing after it, and a zero there
        # reads as "the context dropped to nothing" rather than "this was not measured".
        before = sess.steps[c.step - 1].depth if 0 < c.step <= len(sess.steps) else None
        after = sess.steps[c.step].depth if c.step < len(sess.steps) else None
        rows.append({
            "trigger": c.trigger,
            "pre_tokens": c.pre_tokens,
            "depth_before": before,
            "depth_after": after,
            "summary_chars": c.summary_chars,
            "preserved_messages": c.preserved,
            "turn": c.turn,
        })

    warnings = []
    if rows:
        where = ", ".join(f"{r['trigger']} at {r['pre_tokens']:,} tok" for r in rows)
        warnings.append(
            f"the conversation was compacted {len(rows)}x ({where}): above each seam the "
            f"assistant holds a summary, not the text. Re-asking for something settled "
            f"above a seam is correct behaviour rather than confusion, and a constraint "
            f"stated above one was lost rather than ignored — restating it repairs that, "
            f"and starting a fresh chat does not"
        )
    return {
        "fired": bool(rows),
        "count": len(rows),
        "seams": rows,
        "warnings": warnings,
        "summary": "; ".join(warnings) or "no compaction",
    }


def continuity(sess: Session) -> dict:
    """Was the whole transcript read, or is every count above computed on a fragment?

    A transcript past the read cap is read from its **tail**, so every count is then
    computed on the remainder while looking exactly like a count over the whole thing.
    That was true from the first version and reported nowhere, which is the worst of
    the three available states: measured, wrong, and confident.

    This is not a detector and cannot be wrong: the condition is `size > cap`, a fact
    this tool creates about its own read. It reports magnitude rather than a boolean
    because "truncated" with no number invites the reader to assume it was marginal.

    A **compaction** clause lived here too and was cut for lack of evidence. It now has
    its own check next door, on the same reasoning that let this one ship: a compacted
    transcript was deliberately produced, and the seam turned out to be a record the
    harness writes rather than something to infer. Both are facts about a read, not
    judgements about a session; keeping them separate keeps their remedies separate.
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
    "continuity", "compaction",
]
