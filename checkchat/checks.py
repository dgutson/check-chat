"""The check registry — the seam along which this plugin is meant to grow.

Adding a diagnostic should be one module and one decorator, not an edit in four places.
Before this existed, a new check had to be added to `run_all`, to the text renderer,
and to the skill's reporting instructions, and the third was the one people forget:
a check nobody is told how to report is a check that silently does nothing.

So a check declares its own metadata and the rest follows from it:

* `dimension` — which of the three questions it answers, so the report groups itself.
* `evidence` — **how loudly it may be reported.** This is the important one. Not every
  finding deserves the same voice: one carries its own ground truth, another fires in
  86% of sessions and can only rank. The skill has generic rules per evidence level,
  so a new check inherits the right reporting discipline without the skill being
  edited at all.

`evidence` values, strongest first — except `caveat`, which sits outside the ordering
because it is not a finding about the session at all, but a fact about the report:

| value | meaning | how the skill must report it |
|---|---|---|
| `caveat` | qualifies every other number here | say it **first**, before the dimensions |
| `proof` | carries its own ground truth | lead with it |
| `evidenced` | rare, unambiguous when it fires | report with the quoted specifics |
| `ranked` | too common to discriminate | ranked table, never a verdict |
| `descriptive` | a true statistic with no outcome label | state it, draw no conclusion |
| `weak` | measured near a null | hedge explicitly, never threshold |
| `raw` | a count only | never score it |

`caveat` earns a tier of its own rather than a mention in the skill's prose for the
same reason the others do: the next check that qualifies the report instead of adding
to it should inherit that voice without this file's consumers being edited again.

A check returns a dict carrying at least `fired` and `summary` — **the sentence, without
the label.** The label column is the registry's, not the check's, and that split is
deliberate: every check used to write its own name into its own display string, so three
of them said `cli`, `partial` and `spec` where the registry said `cli_probes`,
`partial_use` and `specification`. A free-form label unlinked to the name is a rename
away from being stale, and a word in `--text` that appears in neither `--catalog` nor the
JSON cannot be looked up by whoever reads it. So `label` is *declared* here — deriving it
would mean inventing a rule that happens to fit three exceptions — and applied in exactly
one place, `line()`, which is why a stale one can no longer exist.

A check that returns no `summary` at all says so in its line rather than vanishing from
the report: `--text` prints only the lines it is given, so no line means no print, and
that is how a correctly computed finding has been lost on the way out seven times.

If a check raises, it is caught and recorded: one broken check must never take down the
diagnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from . import detect, effort, specification, sycophancy
from .transcript import Session


@dataclass
class Context:
    session: Session
    others: list[Session] = field(default_factory=list)


@dataclass
class Check:
    name: str
    dimension: str          # "rot" | "sycophancy" | "opportunity" | "context"
    question: str           # what it answers, in one line
    evidence: str           # see the table above
    run: Callable[[Context], dict]
    label: str = ""         # what `--text` calls it; the name unless declared otherwise


REGISTRY: dict[str, Check] = {}

# The label column every check's line starts with. One constant, because the point of
# declaring the label was that it is applied in one place.
LABEL_WIDTH = 10


def register(name: str, dimension: str, question: str, evidence: str = "descriptive",
             label: str | None = None):
    def deco(fn: Callable[[Context], dict]) -> Callable[[Context], dict]:
        REGISTRY[name] = Check(name, dimension, question, evidence, fn, label or name)
        return fn
    return deco


def line(chk: Check, summary: str | None) -> str:
    """The one place a check's label meets a check's sentence.

    An absent summary prints as an absence rather than as nothing: a check with no line is
    a check that silently does not appear, which is this seam's failure mode and not a
    hypothetical one. Composing here rather than in each check is what makes the label
    unstaleable — there is one string, built from the declaration `--catalog` prints.
    """
    return f"{chk.label:<{LABEL_WIDTH}} {(summary or '').strip() or 'check returned no summary'}"


def run(ctx: Context) -> dict:
    out: dict[str, dict] = {}
    for name, chk in REGISTRY.items():
        try:
            result = chk.run(ctx)
        except Exception as exc:                     # a new check must not break the rest
            result = {"fired": False, "error": f"{type(exc).__name__}: {exc}",
                      "summary": f"check failed ({type(exc).__name__})"}
        result.setdefault("fired", False)
        out[name] = {"dimension": chk.dimension, "evidence": chk.evidence,
                     "label": chk.label, **result,
                     "line": line(chk, result.get("summary"))}
        out[name].pop("summary", None)               # it is in `line`; do not ship it twice
    return out


def catalog() -> list[dict]:
    """What checks exist — so the report can describe itself without hardcoding."""
    return [
        {"name": c.name, "label": c.label, "dimension": c.dimension, "question": c.question,
         "evidence": c.evidence}
        for c in REGISTRY.values()
    ]


# --------------------------------------------------------------- registrations

@register("partial_use", "opportunity", evidence="proof", label="partial",
          question="Was a file read whole, then later proved to need only a slice?")
def _partial_use(ctx):
    rows = detect.partial_use(ctx.session)
    return {"fired": bool(rows), "proofs": rows,
            "summary": f"{len(rows)} dumps later proved to need only a slice"}


@register("dumps", "opportunity", evidence="ranked",
          question="Which payloads cost the most to carry, and for how long?")
def _dumps(ctx):
    d = detect.dumps(ctx.session)
    return {"fired": bool(d["count"]), **d,
            "summary": f"{d['count']}/{d['calls_total']} calls carry {d['chars']:,} "
                       f"chars ({d['share_of_tool_bytes']:.0%} of tool bytes)"}


@register("producers", "opportunity", evidence="evidenced",
          question="Was one expensive command re-run over unchanged input to re-filter it?")
def _producers(ctx):
    rows = detect.producers(ctx.session)
    return {"fired": bool(rows), "groups": rows,
            "summary": f"{len(rows)} re-run >= {detect.PRODUCER_MIN}x on unchanged input"}


@register("rereads", "opportunity", evidence="evidenced",
          question="Was a file re-read with nothing having changed in between?")
def _rereads(ctx):
    r = detect.rereads(ctx.session)
    return {**r, "fired": r["fires"],       # detector says `fires`; the registry reads `fired`
            "summary": f"{r['repeats_without_change']} unchanged "
                       f"(+{r['repeats_after_edit']} legit re-grounding, "
                       f"+{r['repeats_disjoint_slices']} different slices) = {r['chars']:,} chars"}


@register("spill", "opportunity", evidence="evidenced",
          question="Was a result the harness judged too big to keep read back in anyway?")
def _spill(ctx):
    rows = detect.spill(ctx.session)
    return {"fired": bool(rows), "events": rows, "summary": f"{len(rows)} re-ingested"}


@register("cli_probes", "opportunity", evidence="descriptive", label="cli",
          question="Was command syntax re-derived here and in other sessions on this machine?")
def _cli(ctx):
    c = detect.cli_probes(ctx.session, ctx.others)
    # "other probing sessions", not "other sessions": `ctx.others` is pre-filtered to the
    # transcripts that could match, so reporting it as a share of all sessions would
    # overstate how much history a null result has actually been checked against.
    return {"fired": bool(c["recurring"]), **c,
            "summary": f"{c['probes']} --help probes, {len(c['recurring'])} recurring "
                       f"across {c['sessions_compared']} other probing sessions machine-wide"}


@register("effort", "opportunity", evidence="descriptive",
          question="Is the reasoning-effort setting matched to the work being asked for?")
def _effort(ctx):
    a = effort.analyse(ctx.session)
    return {**a, "summary": f"{a.get('overkill_turns', 0)} trivial turns at high effort, "
                            f"{a.get('circling_turns', 0)} circling turns at low effort "
                            f"| mix {a.get('effort_mix', {})}"}


@register("batching", "opportunity", evidence="descriptive",
          question="How many tool calls per response? The multiplier on every other finding.")
def _batching(ctx):
    b = detect.batching(ctx.session)
    return {**b, "fired": b.get("solo_share", 0) > 0.8,
            "summary": f"{b.get('solo_share', 0):.0%} of tool responses carry one call "
                       f"(mean {b.get('mean', 0)})"}


@register("grounding", "rot", evidence="weak",
          question="Does the assistant keep checking reality as context fills?")
def _grounding(ctx):
    g = detect.grounding(ctx.session)
    if not g:
        return {"fired": False, "summary": "session too short to assess"}
    return {**g, "fired": False,
            "summary": f"ground/edit by quartile {g['quartile_ground_per_edit']} (weak)"}


@register("sycophancy", "sycophancy", evidence="proof",
          question="Did the assistant drop a position under pushback rather than argument?")
def _sycophancy(ctx):
    r = sycophancy.report(ctx.session)
    return {**r, "fired": r["needs_judgment"],
            "summary": f"{len(r['candidates'])} candidates from {r['interjections']} "
                       f"interjections "
                       f"({'ranked' if r['ranking_applied'] else 'unranked, non-English'})"}


@register("specification", "specification", evidence="evidenced", label="spec",
          question="Did a request get prose instead of work, without being asked about?")
def _specification(ctx):
    a = specification.analyse(ctx.session)
    r2e = a.get("rounds_to_first_edit")
    return {**a, "summary": f"{a.get('unclarified_count', 0)} requests answered at length "
                            f"with no tools and no question back "
                            f"({a.get('vague_requests', 0)}/{a.get('requests', 0)} named nothing "
                            f"specific; first edit after "
                            f"{r2e if r2e is not None else 'n/a — no edits'})"}


# These two are the reason the body key is called `summary`: their detectors already
# compute one, and it is exactly the sentence the line is made of. Splatting it is the
# whole registration — and if either detector ever renames the key, the line says
# "check returned no summary" in `--text` rather than disappearing from it.
@register("continuity", "context", evidence="caveat",
          question="Was the whole transcript read, or are the counts computed on a fragment?")
def _continuity(ctx):
    return {**detect.continuity(ctx.session)}


@register("compaction", "context", evidence="caveat",
          question="Was the conversation's own history replaced by a summary while it ran?")
def _compaction(ctx):
    return {**detect.compaction(ctx.session)}


@register("failures", "context", evidence="raw",
          question="How many calls failed, and from how many distinct causes?")
def _failures(ctx):
    f = detect.failures(ctx.session)
    return {**f, "fired": False,
            "summary": f"{f['failed']} failed / {f['distinct_causes']} causes "
                       f"({f['declined_by_user']} declined by user)"}


__all__ = ["Check", "Context", "REGISTRY", "LABEL_WIDTH", "register", "line", "run",
           "catalog"]
