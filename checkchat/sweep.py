"""The corpus pass — the shipping checks over many transcripts, aggregated once.

Item 23. The rule this plugin is built on is *don't spend tokens on anything a script can
do*, and its own corpus had been measured a dozen times by hand-rolled `find | xargs grep`.
Two of those sweeps returned a plausible wrong number on the first run and were believed:
one re-ran a match against `proof`, which stores `cmd.strip()[:70]`, so real greps failed
the re-check for want of the characters the display had cut — **28 of 37 bad where the truth
was 6 of 48**; the other hand-rolled the tool-call ledger's row format and reported a
blinding invariant as **0 mismatches out of 196** where the shipping function showed 24. So
the one rule this module exists to obey is **call the checks, never model them.**

Which is why there is no per-check knowledge here at all. `run()` walks whatever
`checks.run` returns: a check's `fired` is counted, and every numeric field it happens to
carry is summarised generically. A check registered tomorrow appears in the aggregate with
no edit here — and, more to the point, a check whose meaning changes cannot drift out of
sync with a copy of itself, because there is no copy. The same reason `cli.collect` walks
the registry rather than naming checks.

**The population is the one the tool actually reports on.** `collect()` refuses a session
with no assistant response, and refuses one with no human turn because the judge would be
handed a blank page (item 16). A sweep that counted those would be measuring a tool nobody
runs, so it applies the same two refusals — and *prints* both counts, because a denominator
that narrowed silently is how a share becomes a confident wrong number.

**Forks are collapsed before anything is counted.** In the development corpus ONE forked
pair manufactured 100% of the apparent cross-session CLI-probing signal, and a corpus pass
is where that mistake scales. `discover.collapse_forks` is the function `siblings()` uses.

**`cli_probes` is the one check whose number depends on a sweep parameter**, because it is
the one check that asks about other sessions. Its answer moves with `siblings`, so the
value used is in the output beside it rather than left to be remembered.

**The aggregate is numbers, and item 24 made that a contract instead of a coincidence.**
This is the one output of the project meant to leave the machine that computed it — item 9
needs a base rate from someone else's corpus, and a base rate is a number, so the aggregate
travels where the conversations cannot. What makes it sendable is that every leaf is a
number except the check names, labels, dimensions and tiers the registry already publishes.
That was true on the day it was written and it was true by accident of two filters:
`_numeric` admits only `int`/`float`, and `meta` copies three registry fields. Nothing failed
if someone widened either. `sendable_strings()` is the declaration a test now walks, and it
is the ninth instance of the seam this project has found eight times with the direction
inverted — `cli.TEXT_OMITS` fails when a field reaches **nobody**, this fails when a field
reaches **everybody**, and it is the only one where a miss is a harm rather than a bug.

Numbers stay allowed without qualification, because **a count about a session is not content
from it**. What that does not buy is anonymity at n=1: a one-session sweep is *contentless*,
not anonymous. Every distribution in it is that session's own value — `n 1 min 4 max 4` is
that session's 4 — so it discloses that session's shape precisely, while disclosing nothing
that was said in it.
"""

from __future__ import annotations

import time
from pathlib import Path

from . import checks, detect, discover, transcript


class _Memo:
    """Load each transcript once; answer the needle question once per file.

    A sweep calls `discover.siblings()` per session — the shipping function, because a
    corpus-wide model of it is the mistake this module's header is about — and that
    otherwise reparses the sibling population once per session and rescans every file's raw
    bytes once per session. On this machine that is 319 files and 75 MB, so the naive form
    is 24 GB of scanning and ~3,800 parses to answer a question that needs 319 of each.

    Memoising is safe here and would not be in `collect()`: a sweep is a snapshot of files
    that are not the session it is running in, whereas the *current* session's transcript
    grows while the tool reads it.
    """

    def __init__(self) -> None:
        self.sessions: dict[str, transcript.Session] = {}
        self.hits: dict[tuple[str, bytes], bool] = {}

    def load(self, path: Path) -> transcript.Session:
        key = str(path)
        if key not in self.sessions:
            self.sessions[key] = transcript.load(path)
        return self.sessions[key]

    def contains(self, path: Path, needle: bytes) -> bool:
        key = (str(path), needle)
        if key not in self.hits:
            self.hits[key] = discover.contains_bytes(path, needle)
        return self.hits[key]


def sendable_strings() -> set[str]:
    """Every string the aggregate is allowed to carry — derived, never listed.

    Derived from the registry because a hand-written list would be a second copy of it, and
    a second copy is the one thing this module refuses to hold. A check registered tomorrow
    widens the vocabulary by exactly its own four constants and by nothing else, which is
    the same property that lets `run()` summarise it with no edit here.
    """
    return {s for chk in checks.REGISTRY.values()
            for s in (chk.name, chk.label, chk.dimension, chk.evidence)}


def _stats(values: list[int | float]) -> dict:
    """A numeric field's distribution, which is what item 9 has been waiting for.

    `nonzero` is here because it is the question a base rate actually asks — "in how many
    sessions is this not zero" — and a median of 0 hides it completely. Percentiles are
    nearest-rank on the sorted values, not interpolated: these are counts, and an
    interpolated 0.5 of a file read is not a thing that happened.
    """
    v = sorted(values)
    at = lambda q: v[min(len(v) - 1, int(q * len(v)))]  # noqa: E731 - nearest-rank
    return {"n": len(v), "nonzero": sum(1 for x in v if x), "min": v[0],
            "median": at(0.5), "p90": at(0.9), "max": v[-1]}


def _numeric(result: dict) -> dict[str, int | float]:
    """The numeric fields of a check's result, generically.

    `bool` is excluded deliberately, and it is not pedantry: `fired` is an `int` to Python,
    and averaging it alongside a byte count would put a share and a magnitude in the same
    column. `fired` is counted separately, where it means something.
    """
    return {k: v for k, v in result.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)}


def run(limit: int = 0, siblings: int = 12, observe=None,
        evidence_width: int = checks.SPECIFIC_WIDTH) -> dict:
    """Every transcript on this machine, through the shipping checks, as one aggregate.

    `limit` caps the files *considered*, newest first, and is reported — a cap that does not
    say so reads as "that was the whole corpus", which is the shape of confident wrong number
    this project keeps finding in its own output.

    There is no `root` parameter: the corpus location is `CLAUDE_CONFIG_DIR`, which is what
    `discover` already reads and what the tests already set. A second way to say where the
    transcripts are is a second thing that can disagree with `collect()`.

    `observe(session, results)` is item 27's seam and it is deliberately the *only* thing
    that leaves this loop besides the aggregate. `--calibrate` needs the same population,
    the same two refusals and the same fork collapse, plus the individual findings; walking
    the corpus a second time to get them would be a second copy of the population logic,
    which is the mistake this module was written to end. It must not touch the aggregate —
    that output is *declared* sendable and a row of evidence in it would be somebody's
    filename in a public issue, so the callback returns nothing and a test asserts the
    aggregate is identical with and without one. `evidence_width` travels with it under the
    same guarantee: it changes only the strings an observer is handed, and the aggregate
    summarises numbers, so widening it cannot move a single figure the sweep sends.
    """
    started = time.time()
    memo = _Memo()
    paths = discover.all_transcripts()
    found = len(paths)
    if limit:
        paths = paths[:limit]

    # Both refusals are counted *here*, before the fork collapse, and the first draft of this
    # got it wrong in the way this module exists to prevent. `collapse_forks` drops a session
    # with no steps as well as collapsing a family, so `len(paths) - len(families)` reported
    # **184 forks collapsed** on this corpus where exactly **one** file is a fork: the other
    # 183 have no assistant response at all. A number that reads as one thing and measures
    # another, inside the module whose docstring says a denominator must not narrow silently.
    reasons: dict[str, int] = {"no_responses": 0, "no_human_turn": 0}
    with_responses = []
    for p in paths:
        sess = memo.load(p)
        if not sess.steps:             # `collect()`'s first refusal
            reasons["no_responses"] += 1
            continue
        with_responses.append(sess)

    # Collapsed before anything is counted, so every number below describes a distinct
    # history rather than a file: a resumed session's prefix would otherwise be counted twice.
    families = discover.collapse_forks(with_responses)
    truncated = 0
    fired: dict[str, int] = {}
    errors: dict[str, int] = {}
    fields: dict[str, dict[str, list]] = {}
    meta: dict[str, dict] = {}
    counted = 0

    for sess in families:
        if not sess.turns:                 # item 16's refusal, applied to the corpus
            reasons["no_human_turn"] += 1
            continue
        truncated += bool(sess.truncated)
        # The first argument is `cwd`, and at the default machine scope `siblings()` does not
        # read it — the session's own directory is passed because something must be, and
        # naming that here is cheaper than the next reader re-deriving it.
        others = discover.siblings(
            Path(sess.path).parent, exclude=Path(sess.path), limit=siblings,
            contains=detect.PROBE_NEEDLE, exclude_forks_of=sess,
            loader=memo.load, prefilter=memo.contains,
        ) if siblings else []
        results = checks.run(checks.Context(session=sess, others=others), evidence_width)
        if observe is not None:
            observe(sess, results)
        counted += 1
        for name, r in results.items():
            meta.setdefault(name, {k: r.get(k) for k in ("dimension", "evidence", "label")})
            fired[name] = fired.get(name, 0) + bool(r.get("fired"))
            errors[name] = errors.get(name, 0) + bool(r.get("error"))
            for key, value in _numeric(r).items():
                fields.setdefault(name, {}).setdefault(key, []).append(value)

    out = {
        "files": {
            "found": found,
            "considered": len(paths),
            "limit": limit,
            "with_responses": len(with_responses),
            "families": len(families),
            "forks_collapsed": len(with_responses) - len(families),
            "refused": reasons,
            "truncated": truncated,
        },
        "sessions": counted,
        "siblings": siblings,
        "checks": {
            name: {
                **meta[name],
                "fired": fired[name],
                "share": round(fired[name] / counted, 3) if counted else 0.0,
                "errors": errors[name],
                "fields": {k: _stats(v) for k, v in sorted(fields.get(name, {}).items())},
            }
            for name in sorted(meta)
        },
    }
    out["elapsed_ms"] = int((time.time() - started) * 1000)
    return out


def render(d: dict) -> str:
    """Everything `run` computes, because nothing a producer computes is rendered by default.

    That rule (item 19) is why this exists at all rather than the caller printing the three
    numbers it happened to want. The seam it guards has leaked eight times, and a new
    producer with no renderer is the ninth waiting to happen. A test walks `run`'s keys
    against this function; there is no omission list, because nothing here is worth omitting.
    """
    f = d["files"]
    refused = ", ".join(f"{k} {v}" for k, v in f["refused"].items())
    lines = [
        f"swept {d['sessions']} sessions | {f['found']} transcripts found, "
        f"{f['considered']} considered"
        + (f" (limit {f['limit']})" if f["limit"] else "")
        + f" | {d['elapsed_ms']}ms",
        f"{f['with_responses']} have responses -> {f['families']} distinct histories "
        f"({f['forks_collapsed']} forks collapsed) | refused: {refused or 'none'}",
        f"truncated {f['truncated']} | siblings {d['siblings']}",
        "",
    ]
    for name, c in d["checks"].items():
        err = f"  [{c['errors']} errored]" if c["errors"] else ""
        lines.append(f"{name:<14} {c['label']:<10} {c['dimension']:<12} [{c['evidence']}]"
                     f"  fired {c['fired']}/{d['sessions']} = {c['share']:.0%}{err}")
        for key, s in c["fields"].items():
            lines.append(f"    {key:<26} nonzero {s['nonzero']:>4}/{s['n']:<4} "
                         f"min {s['min']:>8} median {s['median']:>8} "
                         f"p90 {s['p90']:>8} max {s['max']:>10}")
    return "\n".join(lines)
