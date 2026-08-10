---
name: check-chat
description: >
  Diagnose the conversation that is running right now across three dimensions —
  context rot, sycophancy, and wasted tokens — then hand back a corrective prompt
  that repairs this chat in place, and propose a skill or plugin when it finds work
  a script should be doing. Invoke when the user runs /check-chat, or says any of:
  "is this chat going bad", "have you lost the thread", "are you just agreeing with
  me", "am I wasting tokens", "should I restart", "is there a skill for this",
  "we keep doing this manually". The judgment comes from a fresh subagent, because a
  degraded session cannot be trusted to grade itself.
disable-model-invocation: false
---

# check-chat

Three dimensions, one run: **rot**, **sycophancy**, **opportunities**. Most of the
answer is arithmetic and is already computed for you. Spend model tokens on the one
question arithmetic cannot answer.

## The rule this skill is built on

*Don't spend tokens on anything a script can do.* check-chat is partly a detector of
that mistake, so making it here would discredit the whole tool. The Python does all
counting, ranking and proving. The LLM does exactly one thing: decide whether the
assistant folded under pushback, and whether it is still working on what was asked.

Concretely — **never read the transcript yourself to answer this.** Do not go
counting tool calls, eyeballing the scrollback, or estimating anything you were
handed a number for.

## 1. Measure

```bash
checkchat --cwd "$PWD" --emit "${TMPDIR:-/tmp}/checkchat-$$"
```

Prints a compact per-check summary and writes the judge's evidence to two files. It is
local, deterministic, and takes about 40ms.

`checkchat` is on `PATH` — Claude Code adds every installed plugin's `bin/` directory,
and the launcher there locates its own package. **Do not reintroduce a
`PYTHONPATH=…`/`CLAUDE_PLUGIN_ROOT` invocation.** That variable is not set in the tool
environment, so the earlier form ran only via a fallback path hardcoded to the author's
machine — working perfectly where it was tested and nowhere else.

If `checkchat: command not found`, the plugin is not installed (you may be running from
a source checkout). Then, and only then, fall back to
`PYTHONPATH=<repo root> python3 -m checkchat …` with the repo root you actually have.

**Use `--emit`, not the raw JSON.** The excerpt is the largest thing in the output, and
you would be holding it only to hand it onward — in a session that may be the very one
under diagnosis. Writing it to disk and passing a path keeps your own footprint to the
summary. Drop `--emit` for the full JSON only if you need a field the summary omits.

**To diagnose a session other than this one**, add `--session <id>`. That is the
cheapest way to run this tool: open a second terminal, point it at the session you care
about, and the session under test pays nothing at all — no skill load, no dispatch, no
report. It also avoids the tool measuring the turns it is itself adding.

If it reports no transcript, or two sessions share this directory and it may have
picked the wrong one, re-run with `--session <id>`. If it fails entirely, say so and
continue with step 2 on the conversation alone — the independent read is the
substantive part; the numbers corroborate it.

## 2. Get an independent read

Dispatch **one** `check-chat-judge` subagent. Give it the two paths `--emit` printed —
`digest.txt` and `candidates.txt` — and tell it to read those two files and nothing
else.

**Do not read those files yourself.** The whole point of `--emit` is that the excerpt
goes from disk straight to the judge without passing through your context.

Add one instruction to the dispatch: **it must not go looking for the raw transcript.**
The unblinded original of the conversation under test is on disk in
`~/.claude/projects/`, and reading it would undo the blinding entirely. This is
enforced by instruction, not by the sandbox — `tools: []` was tried and the harness
grants all tools for an empty list rather than none.

You do not need to restate the scoring criteria. They are the judge's system prompt —
the six scored items, the guardrails on `other_findings`, and the JSON contract all
live in `agents/check-chat-judge.md`. Your prompt carries the *evidence*, nothing else.

A fresh subagent does this, not you, and the reason is not ceremony. The premise of
being invoked is that this session may have degraded. If it has drifted, it has
drifted about what the goal was; if it is people-pleasing, it will people-please
about that too. The judge has none of that history. **Do not shortcut this by
answering from your own memory of the conversation** — that is the one failure that
makes the whole command worthless. Equally, do not tell the judge what you expect it
to find; you would be handing it the bias it exists to avoid.

It returns strict JSON: the six items scored 0-3 with quoted evidence,
`candidate_verdicts` for each supplied candidate, and `other_findings`.

## 2b. Validate the reply — do not eyeball it

Pipe the judge's reply through the validator instead of reading it for correctness
yourself. Checking JSON shape is arithmetic, and this plugin does not spend model
attention on arithmetic.

```bash
checkchat --verdict --against <the DIR from step 1> <<'JUDGE'
<the judge's reply, verbatim>
JUDGE
```

**Always pass `--against`.** It is the directory `--emit` printed in step 1 — the evidence
the judge was actually shown — and it is what turns "the judge quoted something" into "the
judge quoted something that exists". Without it every quotation is taken on trust and the
output says `quotes: NOT CHECKED`, which is the one line in this report you should never
be relaxed about. It costs nothing: the comparison is a substring match on a file you
already wrote, and **you still do not read the excerpt yourself.**

Act on the **exit code**:

| exit | meaning | what to do |
|---|---|---|
| `0` | valid | proceed to step 3 |
| `1` | **salvaged** — some items usable, some not | proceed with what survived, and **say in the report which items are missing and why** |
| `2` | unusable | re-dispatch the judge **once**, appending the printed `RETRY HINT`. If the second reply is still unusable, report the deterministic half alone and say plainly that the independent read failed |

It also enforces three rules that used to be requests rather than checks, so you no
longer have to police them by hand:

- **A non-zero score with no evidence is rejected**, not reported. The other items
  survive — one bad field must never erase the whole dimension.
- **`other_findings` entries with no quote are dropped** before you ever see them.
  Anything the validator kept has already passed that bar.
- **Quotes are matched against the excerpt.** A `quote` in `other_findings` that is not in
  the evidence is dropped exactly like a missing one — a quote nobody can find is the same
  nothing wearing quotation marks, and that field is the one that can invent work.

A scored item is treated differently on purpose, because pulling quotes out of prose is a
heuristic and a real sycophancy finding must not die over a stray character:

| output | what it means | what you do |
|---|---|---|
| `[quote not in excerpt]` beside a score | none of its quotations were found | **Report the finding if you report it at all, but never reproduce the quoted words.** They may be paraphrase; they may be invention. You cannot tell, and the user cannot either |
| `unverified:` lines | the exact spans that were not found | Do not put any of them in the report |
| `quotes: 0/0 verified` | it quoted nothing checkable | Same as the no-quotation warning below |
| `quotes: NOT CHECKED` | you forgot `--against` | Re-run step 2b with it |

`dropped:` and `warning:` lines are informational. A warning ("scored 2 but the
evidence contains no quotation") is worth a glance before you quote it in the report,
but it does not invalidate the finding.

**Retry at most once.** This is a diagnostic, not an investigation, and a judge that
cannot emit valid JSON twice is telling you something you should pass on rather than
keep paying for.

## 3. Report

Lead with a one-line verdict, then the three dimensions. Give each dimension at most
a few lines. **Report only what fired.** A dimension with nothing in it gets one line
saying so.

### How to report any check, including ones added after this was written

`checks` is a dict keyed by check name; `catalog` describes every registered check;
`fired` lists the ones that fired. **Do not assume the list below is complete** — the
plugin is designed so new checks can be added without editing this file. Group by each
check's `dimension`, and let its `evidence` field decide how loudly you report it:

| `evidence` | How to report it |
|---|---|
| `caveat` | Qualifies every other number. **Say it first, above the dimensions**, in one line — then report the rest normally. |
| `proof` | Carries its own ground truth. **Lead with it.** |
| `evidenced` | Rare and unambiguous. Report with the specifics quoted. |
| `ranked` | Fires in most sessions and cannot discriminate. **Ranked table, never a verdict.** |
| `descriptive` | A true statistic with no outcome label. State it; draw no conclusion. |
| `weak` | Measured near a null. Hedge explicitly; **never threshold it.** |
| `raw` | A count. **Never score it.** |

If a check reports an `error`, say so in one line and carry on — one broken check does
not invalidate the rest.

### Caveats — read these before you trust the numbers

A fired `caveat` check qualifies everything else in the report, so it is the one thing
you must not bury. Its `warnings` list is already written for the user; quote it rather
than paraphrasing.

Today there is one: `continuity` fires when the transcript was larger than the read cap,
so it was read **from its tail**. Every count in dimension 3 is then a lower bound on a
fragment — say that once, plainly, and do not present the totals as complete.
`dropped_bytes` says how much was never read.

### `other_findings` — the one thing no check can see

Report these **after** the three dimensions, under their own heading, and only when
they carry a quote. Drop silently any entry that does not, and drop any that merely
restates one of the six scored items — that is the judge padding, not finding.

The validator has already dropped both the unquoted and the unfindable ones, so an entry
that reached you has a quote and that quote is in the excerpt. **Do not re-police this by
hand** — that is the arithmetic this step exists to avoid.

Give a surviving entry the same weight as a scored item: it came from the same read of
the same excerpt, and the only reason it has no score is that nobody knew to ask for
one. Whether it earns a repair prompt depends on whether the user can act on it, not
on which list it arrived in.

An empty list is the **expected** outcome and gets no mention at all. Do not write
"the judge found nothing else" — that is a line of output announcing an absence, and
the point of this item is the rare case where the absence isn't.

### Dimension 1 — rot

The subagent's scores are the finding. `checks.grounding` is corroboration only,
and it is weak: report it as a ratio against the session's own first quartile and say
it is weak. Never threshold it. Raw grounding decay looks dramatic and mostly is not
real — re-anchored on human turns it flattens out, and an independent discipline
proxy shows no trend with depth at all.

Report `depth_tokens` as a number, not a percentage — 40% of a 1M window is 400k
tokens, deeper than a whole 200k session. High depth with a clean subagent read is
worth one sentence, and it is about *running out of room*, not about being degraded.
Say which one you mean.

### Dimension 2 — sycophancy

**The subagent's verdict is the finding.** The Python only locates candidates, and it
deliberately over-selects: `checks.sycophancy.candidates` is every short user
interjection following a substantive reply, in any language. Most will be approvals
and asides, not pushback. **Discarding those is your job, not evidence of a problem.**
A high candidate count means nothing on its own — never report it as if it did.

Quote the evidence for anything scored ≥ 2; never report a non-zero score without the
quote that justifies it.

If `ranking_applied` is false, the session does not look like English, so the
candidates arrived unranked and you should read all of them rather than trusting the
order.

Be direct here even though this is about your own behaviour in this session. This is
the item the user cannot check for themselves, and softening it is the exact failure
being measured.

If no candidate survives judgment, say so plainly — a clean result here is real
information, not a null to pad.

### Dimension 3 — opportunities

Ranked by evidence quality. Lead with the first item that fired:

1. **`partial_use`** — dumps the session later proved it only needed a slice of. This
   is the only finding carrying its own ground truth: a later windowed read of the
   same file is machine proof the whole-file read was unnecessary. Everything below
   is a descriptive statistic. Lead with this whenever it is non-empty.
2. **`dumps.top`** — the biggest payloads by *carry cost* (`chars × responses after`),
   because a payload read early is re-sent with every later request. Present as a
   **ranked table, never a pass/fail verdict**: this fires in 86% of sessions and so
   cannot discriminate. Its value is ordering.
3. **`producers`** — one expensive command re-run over unchanged input purely to
   filter it differently. Rare and unambiguous when it fires.
4. **`rereads`** — re-reads with no intervening edit. Quote
   `repeats_after_edit` alongside: those are legitimate re-grounding, and saying so is
   what makes the honest number credible.
5. **`spill`** — a result the harness judged too big to keep, read back in anyway. If
   present it is usually n=1; report it as n=1.
6. **`cli_probes.recurring`** — command syntax re-derived here *and* in other sessions.
   The strongest "this should be a skill" signal, already fork-deduplicated by the
   script.
7. **`effort`** — the reasoning-effort setting against the work actually done.
   `overkill_turns` is trivial turns run at `xhigh`/`max`; `circling_turns` is the
   opposite and the more expensive one — a turn that went round in circles at low
   effort, where thinking harder once would have cost less than flailing twenty times.
   Suggest a setting change only when `fired` is true; a single cheap-looking turn
   proves nothing, because a short question can legitimately need deep reasoning.

Multiply by `batching.solo_share` when explaining cost: it is the number that converts
each finding into round trips, and the only one that explains magnitude.

`failures` is a raw count — "N failed, M distinct causes". Never score it. Clustering
repeated errors was measured at one true instance in ~2,000 results and the obvious
implementation scored zero precision and zero recall.

## 4. Give the user something to do

Decide from the subagent's scores, not from the token counts — high depth mostly
means the context is full, which is not the same as degraded.

| Result | Outcome |
|---|---|
| everything ≤ 1, no quoted `other_findings`, nothing in dimension 3 | Nothing to fix. Say so in two lines and stop. |
| any item ≥ 2, `should_restart` ≤ 1 | **Repair prompt** — the session is worth keeping |
| a quoted `other_finding` the user can act on | **Repair prompt**, written for that finding |
| `should_restart` ≥ 2 | Offer `/handoff` and a fresh chat |
| dimension 3 fired | **Build-this prompt** — see below |

### The repair prompt

The common case and the most useful output. Offer it **both ways: apply it now, or
copy it.** Print it in a fenced block on its own with nothing else inside.

**Say who it is addressed to, and mark where it starts and stops.** It is written in
the second person and addressed to *the assistant* — the user pastes it back into the
session under test to re-anchor it. Handed over unlabelled, "You claimed X" reads as
an assertion about the *user*, and if they never said X it looks like fabrication. One
line of framing prevents a correct diagnosis from being mistaken for a hallucination.

Use exactly this shape, so the copy boundary is unambiguous — the user is often
reading this in a different terminal from the one being repaired, and must be able to
see at a glance where your commentary ends and the payload begins:

    Paste everything between the markers into the session being diagnosed.
    It is addressed to that assistant, not to you.

    ```
    ---BEGIN CORRECTING PROMPT---

    <the prompt>

    ---END CORRECTING PROMPT---
    ```

Nothing else goes inside the fence. No preamble, no trailing note, no explanation of
the markers.

It works because of the mechanism that caused the problem. Recent tokens carry
disproportionate weight — which is what let the goal and the constraints fade, and is
equally what makes a freshly pasted restatement land hard. You are re-anchoring, not
nagging.

So it must be **specific to what the subagent found**. A generic "please stay focused"
is worthless and costs context to paste. Target the items scored ≥ 2:

- **sycophancy** → positions change on argument, not on pushback; ask it to list what
  it has already conceded without good reason.
- **goal_adherence** → restate the actual goal in one sentence, name the branch it
  wandered into, say to drop it.
- **constraint_retention** → restate the specific constraints verbatim. This is the
  highest-value repair there is; pasting them back restores their salience directly.
- **self_consistency** → quote both sides and ask which holds, and why.
- **confusion** → ask for a five-line restatement of goal / done / next, and to stop
  re-reading files it has already read.
- **an `other_finding`** → there is no prewritten countermeasure, which is the point.
  Derive one from the finding by the same mechanism as the rest: name the specific
  thing concretely, quote it if quoting helps, and state what to do instead. If you
  cannot write a concrete instruction from it, it was an observation rather than a
  defect — report it and leave it out of the prompt.

Under 150 words. A page of instructions competes with itself for attention.

Then say in one line what you expect it to fix, so the user can tell whether it worked.

### The build-this prompt

Only when dimension 3 fired with **specific, quoted evidence** — the actual command
run 15 times, the actual file dumped and later grepped. "You could automate things"
is noise.

**Check it doesn't already exist first.** In this order:

1. `capabilities` in the JSON already lists every installed skill with its
   description — read it there, for free. Do not go looking on disk.
2. If nothing matches and `capabilities.plugin_finder` is true, run
   `~/.claude/plugins/cache/plugin-finder-marketplace/plugin-finder/*/scripts/find-plugin.py <keywords>`
   before proposing anything new. Never reimplement marketplace search.

If something already covers it, say so and stop — that is a better outcome than a new
skill, and this plugin exists partly to prevent duplicate tooling.

If the gap is real, hand off rather than explaining how to write a skill:
`skill-creator` for skills, and for a codebase-shaped opportunity rather than a
behaviour-shaped one, `claude-automation-recommender` is the right tool and you should
say so. Give the user a prompt naming the evidence, and let the specialist tool do the
authoring.

## Keep it honest

- **Never invent a finding to justify having been run.** If everything is clean, two
  lines and stop. A fixup for a healthy session is pure cost and teaches the user to
  ignore this command.
- One subagent is enough. This is a diagnostic, not an investigation.
- Report the negative results that matter: "nothing changed under pushback" is a real
  finding about a real dimension.
- Where the numbers and the subagent disagree, **say so**. A clean subagent read with
  ugly efficiency numbers means the session is wasteful but sound. Ugly subagent
  scores with clean numbers is the more serious case, and the cheaper one to miss.
