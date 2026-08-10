# check-chat

Diagnose the Claude Code conversation you are *currently in*, then repair it in place.

You invoke it manually, mid-session, when something feels off. It answers three
questions:

1. **Has this chat rotted?** Has the assistant drifted off the goal, dropped a
   constraint, started contradicting itself?
2. **Is it just agreeing with me?** Did it abandon a position because you pushed, not
   because you argued?
3. **What is being done by hand that a script should be doing?** Backed by what this
   session actually did — not by guesswork.

Then it gives you a corrective prompt you can apply immediately or paste yourself, and
— only when the evidence is specific and nothing already covers it — a prompt to build
the skill or plugin that would stop the waste recurring.

What is done, what is next, and what was deliberately *not* built and why:
[ROADMAP.md](ROADMAP.md).

## Install

```bash
claude plugin marketplace add dgutson/check-chat
claude plugin install check-chat
```

Then `/check-chat` in any session. Python 3.10+, standard library only, nothing leaves
your machine.

## The rule it is built on

> Don't spend tokens on anything a script can do.

check-chat is partly a detector of that mistake, so it would discredit itself by
making it. Everything countable is counted by deterministic Python in `checkchat/` —
about 40ms, entirely local. The model is asked exactly one question, the only one
arithmetic cannot answer: *did the assistant fold under pushback, and is it still
working on what was asked?*

That judgment comes from a **fresh subagent**, not from the session being judged. If a
session has drifted, it has drifted about what the goal was; if it is people-pleasing,
it will people-please about that too. The subagent sees a **blinded** excerpt —
renumbered from exchange 1, with no indication of how long the conversation is —
because a judge that can see "exchange 180 of 200" stops reading and reports
degradation, which is a fact about length that needed no model at all.

The judge is a **declared agent** (`agents/check-chat-judge.md`), not an inline prompt.
Its criteria live in a system prompt rather than being restated in a user message each
run, and it reads the excerpt from a file the measurement step wrote — so the diagnosing
session never has to hold it.

**Its reply is validated, not believed.** The JSON is parsed tolerantly and then checked
against the contract, and every quotation is matched against the excerpt the judge was
actually shown. Requiring evidence for a non-zero score is what makes that necessary: a
mandatory field is a field under pressure, and the cheapest way to fill it when nothing
fills it is a plausible sentence in quotation marks. A quote that is not in the excerpt
never reaches you as one. What is *not* checked is who said it — presence, not attribution.

**Blinding is enforced by instruction, not by the sandbox.** The intent was `tools: []`,
which would have made a judge that *cannot* go and read the unblinded original sitting
in `~/.claude/projects/`. The harness grants *all* tools for an empty list rather than
none, so that does not work; the agent is declared `tools: ["Read"]` and told to read
only what it is given. Worth knowing when you weigh how much to trust the verdict.

It is deliberately an *agent* rather than a second skill. A skill would sit in the
registry where the **session under test could invoke it on itself** — a degraded
context grading its own work is the exact failure this design exists to prevent.
Agents are dispatched; they cannot self-invoke.

It is asked six scored questions and **one open one**: *is anything else going wrong
that those six did not ask about?* Every check in this plugin is a closed world — each
finds only what someone thought to write a detector for, so the failure modes nobody
anticipated are invisible to all of them at once. The judge already has the excerpt in
front of it, so that question costs nothing, and it is the only part of the design that
can see outside its own categories. Answers must carry a verbatim quote, and an empty
answer is the expected one.

## What it looks for, and why those things

Every detector here was measured against real transcripts before being written, and
several plausible ones were deleted after measuring at chance. The rule was: **a
detector that cannot be shown to fire on real data does not ship.**

| Signal | What it means |
|---|---|
| **Partial-use proof** | A file was read whole, then later only grepped. The later windowed read is machine proof the whole-file read was unnecessary. The only finding carrying its own ground truth — so it leads. |
| **Context-dump ledger** | The biggest payloads ranked by *carry cost* (`chars × responses after`), since a payload read early is re-sent with every later request. Ranked, never pass/fail: it fires in 86% of sessions, so it cannot discriminate. |
| **Redundant re-reads** | Re-reads with *no intervening edit*. Re-reading a file you just changed is correct re-grounding; the naive rule overstates waste by 66%. |
| **Repeated producer** | One expensive command re-run over unchanged input purely to filter it differently — `strings <100MB binary> \| grep …`, fifteen times. |
| **Spill re-ingest** | A result the harness judged too big to keep, read back in anyway. Seen once: 2,091 chars kept, 81,056 re-read. |
| **CLI re-derivation** | Command syntax re-derived via `--help` here *and* in other sessions **anywhere on this machine** — the strongest "this should be a skill" signal, since a skill is installed per user rather than per project. Compared per-directory it measured zero on 51 real sessions; compared machine-wide, 8 of 51. |
| **Batching ratio** | Tool calls per response. Not waste itself; the multiplier that turns every other finding into round trips. |
| **Sycophancy** | Short user challenge → position reversal, agreement opener, or a claim quietly hedged into a non-claim. Located deterministically, judged by the model. |
| **Grounding decay** | Checking reality less as context fills. Reported only against the session's own first quartile, and flagged as weak — because it is. |
| **Effort calibration** | `xhigh`/`max` spent on one-question turns — or the reverse, a turn circling for 50 responses at low effort, where thinking harder once beats flailing twenty times. |

Deliberately **not** built, each measured to nothing: repeated-error clustering
(1 true instance in 1,968 results), semantic drift and terminology mutation (a
within-session shuffle reproduces the whole trend), generic tool-sequence mining
(0 recurring sequences across sessions), and byte-identical re-reads (verified zero).

## Adding a check

A check is one module and one decorator. Nothing else *must* change — the CLI walks
the registry and the skill reports a check from its declared `evidence` level without
being edited.

Two honest caveats, because an earlier version of this paragraph overstated it and the
overstatement survived two real bugs before anyone noticed:

- A check introducing a **new dimension** sorts last in the text renderer until you add
  it to the `order` map in `__main__.py`. It degrades gracefully; it is not dropped.
- The skill's dimension-3 section names specific checks in a "lead with these" order.
  A new check is still reported without touching it, just not in that priority list.

```python
# checkchat/mycheck.py
from .checks import register

@register("my_check", "opportunity", evidence="evidenced",
          question="Did the session do X when it could have done Y?")
def _my_check(ctx):                       # ctx.session; ctx.others = other sessions on
                                          # this machine, fork-deduplicated, pre-filtered
                                          # to those containing `--help` (see ROADMAP)
    hits = [c for c in ctx.session.calls if ...]
    return {"fired": bool(hits), "hits": hits,
            "line": f"my_check   {len(hits)} occurrences"}
```

Import it from `checks.py` and it appears in `--catalog`, in the JSON, and in the
report automatically.

The `evidence` field is the load-bearing part. It tells the skill **how loudly the
finding may be reported** — `proof` leads the report, `ranked` may only produce a
sorted table, `weak` must be hedged, `raw` may never be scored. That is why the skill
does not need editing: a new check inherits the right reporting discipline from its
own declaration. If a check raises, the registry catches it and the other checks still
run.

**Before you add one, measure it.** The rule that produced the table above is that a
detector which cannot be shown to fire on real transcripts does not ship — and one
that fires in most sessions is a ranking, not an alarm. Two predecessor signals were
built on intuition and later measured at chance.

## A note on sycophancy

The corpus this was developed against measures sycophancy at a base rate of **zero**.
That is one experienced engineer who explicitly demands pushback in his prompts — a
negative control, not evidence the behaviour is rare, and deliberately **not** used to
tune thresholds. The people who most need this check are the ones who will never think
to demand pushback, and who therefore cannot notice when they stop getting it.

**The pre-pass is structural, not lexical, and that was learned the hard way.** An
earlier build matched English phrases — "are you sure", "I think you're wrong". Run
against realistic inputs it returned **zero candidates** for the same exchange in
Spanish, in Portuguese, or in English profanity, and reported a clean bill of health
rather than "not measured". A silent zero is worse than no detector: it spends the
user's trust while measuring nothing.

The gate now keys on shape — a **short** user turn following a **substantive** reply is
an interjection in any language. It over-selects on purpose; discarding non-challenges
is what the judge is for, and over-selecting fails loudly where the phrase lists failed
silently. English phrases survive only to *rank* candidates, never to select them, and
when the session doesn't look like English the output says so instead of printing a
zero. Those cases are permanent regressions in the test suite.

## Usage outside the skill

```bash
checkchat --text                     # human-readable summary
checkchat --emit DIR                 # summary + evidence to disk (what the skill uses)
checkchat --catalog                  # list registered checks
checkchat --session <id>             # diagnose a session other than the newest
checkchat                            # full JSON
```

`checkchat` lands on `PATH` when the plugin is installed — Claude Code adds every
plugin's `bin/` directory, and the launcher resolves its own location. From a source
checkout without installing, use `PYTHONPATH=. python3 -m checkchat` instead.

## Tests

```bash
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
```

No runtime dependencies — `pytest` is the only dev extra, and `dependencies` in
`pyproject.toml` is empty on purpose: this has to run inside whatever environment the
session under test already has.

They cover the five wire-format traps that silently corrupt every count if mishandled
(one response spanning several records; tool results wearing a `user` role; subagent
sidechains; a user-declined call flagged as an error; an interruption marker becoming a
turn nobody typed), plus a positive control for sycophancy — which the development
corpus measures at zero, so a detector never observed to fire would be
indistinguishable from a broken one.

## License

MIT
