# Roadmap

State as of 2026-08-10. Published; see "Done" below. Written so a session with no memory of how this got here can
pick it up.

The plugin is **installed and working end-to-end** on this machine: `/check-chat` runs,
the deterministic pass takes ~280ms (~86ms of it before item 4 made the cross-session
comparison actually load other sessions; `--siblings 0` returns it to ~20ms), the judge
dispatches by `subagent_type`, and the report comes back. 64 tests pass, in the project's
**own** virtualenv (`.venv/bin/pytest` from the repo root). What follows is what is not
done, ordered by whether it blocks someone other than the author.

Every item says how you would know it is finished. The rule the project is built on
applies to this list too: **a detector that cannot be shown to fire on real transcripts
does not ship**, and one that fires in most sessions is a ranking, not an alarm.

---

## Done

**1. Published to `github.com/dgutson/check-chat`** — public, MIT, 2026-08-09.
Verified from a fresh clone: manifests validate, `bin/checkchat` runs with no install
and no environment variable, and the 33 tests of the day passed. The plugin is no longer
tied to one machine.

Still open from that work: the author's own install is still the *local-path* marketplace
(`installLocation: /home/daniel/src/check-chat`), so his edits go live without a
reinstall while everyone else gets the pushed version — convenient, and a good way to
ship a change that was never tested as installed. Use `claude plugin tag` for versioned
releases once the layout settles.

**2. Judge-reply validation** — `checkchat --verdict` (2026-08-09).
The judge's JSON is now parsed and checked by `checkchat/verdict.py` rather than
believed. Tolerant of fences and stray prose (the common recoverable failure, which no
longer costs a retry); strict about the contract. Exit code drives the skill: 0 valid,
1 salvaged, 2 retry once then degrade visibly.

It also turned two honour-system rules into machine checks — a non-zero score with no
evidence is rejected while the other items survive, and an `other_findings` entry with
no quote is dropped before the reporting step can forget to. 8 tests.

The hole it left is closed by item 11.

**3. `truncated` is consumed; `compactions` is gone** — `continuity`,
`evidence="caveat"` (2026-08-10). "Computed and consumed by nothing" has two honest
fixes, and the two halves earned opposite ones:

*Truncation ships.* A transcript over the 24 MB cap is read from its tail, and every
count was then computed on the remainder with nothing saying so. `continuity` now
reports it with its **magnitude** — a bare boolean invites the reader to assume it was
marginal — the `--text` header carries `[PARTIAL]`, and the skill is told the dimension-3
totals are a lower bound on a fragment. This is not a detector and cannot be wrong: the
condition is `size > cap`, a fact the tool creates about its own read. 4 tests, whose
positive control is a real transcript with the cap lowered — same code path, real
records, only the threshold moved.

*Compaction was cut* rather than consumed, and 10 was opened for it. Detail there; the
short version is 0 observations in 4,155 measurements, so by this project's own rule it
was not shippable and the honest fix for "computed and consumed by nothing" was to stop
computing it.

It also added a seventh `evidence` tier, **`caveat`** — a finding that qualifies every
other number rather than adding to them, so the renderer hoists it *above* the counts it
invalidates and the skill reports it before the dimensions. Selected by tier, never by
name, so the next check of that kind needs no edit. A caveat printed underneath the
numbers it invalidates has already failed at its one job.

**4a. Trap 5 — the interruption marker was a turn nobody typed** (2026-08-10).
Found by running `/check-chat` on its own session, which is the only reason it was found:
the judge scored sycophancy 0 having located the one real pushback moment in the excerpt,
while the Python handed it **zero candidates**. That disagreement was the tell.

The harness writes `[Request interrupted by user for tool use]` as a `user` record of its
own — **15 of them across 9 sessions** in the corpus. `clean()` did not strip it, so it
became a turn, and the inflated denominator was the harmless half. The phantom sat
*between* the reply and the objection that followed it, so `sycophancy` discarded the
phantom (a short interjection with no reply after it) and then rejected the genuine
objection for being preceded by an empty reply. **Interrupting a tool call and then
pushing back is the highest-signal sycophancy moment there is, and this returned a
confident zero for it** — the failure mode the README calls worse than having no
detector.

One line in `_STRIP`, two regression tests, and verified on the session that exposed it:
candidates 0 → 1, the promoted one being the real objection. Worth noting how it was
caught, because no unit test would have: the phantom only appears when a human interrupts,
which no fixture did, and the *first* symptom was two independent measurements of the same
session disagreeing.

**5. `pyproject.toml`** (2026-08-10). `pip install -e '.[dev]' && pytest` now works from
a clean checkout, verified from a copy of the tree in an empty venv: bare `pytest` finds
the suite via `testpaths`, and the install puts `checkchat` on `PATH` the same way the
plugin's `bin/` launcher does.

Before this the tests borrowed **rot-metrics'** virtualenv, because the system Python has
no pytest and that neighbouring project had one. check-chat has never had any dependency
on rot-metrics — no import, no shared code — so this was pure machine-local accident
masquerading as a toolchain. `dependencies` is empty and should stay empty.

**11. The judge's quotes are checked against the excerpt** — `--verdict --against DIR`
(2026-08-10). Item 2 made evidence mandatory for a non-zero score, and in doing so
**manufactured this hole rather than uncovering it**: a mandatory field is a field under
pressure, and the cheapest way to satisfy "quote the text that justifies this" when
nothing justifies it is a plausible sentence in quotation marks. The validator then
recorded that as a satisfied contract. The end of that path is a report showing the user a
line nobody said — attributed, in quotation marks, by a tool whose whole selling point is
that it does not guess.

`--against` takes the `--emit` directory, i.e. exactly the two files the judge was shown,
and matches each quotation against them. Normalisation folds only what a faithful quote
may differ by — whitespace, case, curly-vs-straight quotes and dashes, markdown
decoration — and elisions (`…`, `...`, `[...]`) are honoured fragment-by-fragment, in
order, which is what makes the check *improve* quoting instead of merely failing it. The
judge is now told to elide rather than reword.

**Enforcement follows how certain the check is, not how bad the offence is** — the same
principle that let truncation ship while compaction was cut:

| field | certainty | consequence of a miss |
|---|---|---|
| `other_findings.quote` | the whole value is by contract one verbatim quote | **dropped**, exactly as a missing quote already was — and it is the one field that can invent work |
| a scored item's `evidence` | prose that *contains* quotes, so extraction is a heuristic | **flagged, score kept**: the finding may be real, and the skill is forbidden to reproduce the words |

Measured before shipping, against three real emitted digests (32,000 chars): **1,299
faithful quotes across 14 mutation kinds, 0 false fails; 331 fabrications — including
word-swapped and reordered versions of real sentences — 0 false passes.** The first run
showed 147 false fails, all of which were the *harness* splicing sentences across
exchange boundaries; the matcher was right and the measurement was wrong. 9 tests, whose
positive control quotes an excerpt built by `digest.build` rather than a hand-written
string — the thing quotes are matched against in production is whatever it emits.

Not checked, and stated rather than implied: **presence, not attribution.** A quote really
in the excerpt but credited to the wrong speaker passes. Scoping matches to one speaker's
line was considered and rejected — it would false-fail a `self_consistency` quote that
legitimately elides across two exchanges, which is the item where that matters most.

**4. `cli_probes` fires — the comparison population was wrong, not the detector**
(2026-08-10). It was queued for deletion twice under this project's own rule that an
unfired detector does not ship, and deleting it would have been a mistake. `recurring`
was 0 on every real session because `others` was every session **in the same project
directory**, while re-derived CLI syntax is a cross-**project** pattern — you relearn a
command in whatever repo you happen to be sitting in.

The giveaway is worth keeping, because it generalises past this detector: **the payoff is
a skill, and a skill is installed per user, not per directory.** The comparison
population was answering a narrower question than the detector asks. Any future
cross-session check inherits that reasoning — match the population to the scope of the
*remedy*, not to the folder you happen to be in.

| scope | sessions firing |
|---|---|
| per project directory (as shipped) | **0 of 51** |
| machine-wide, same detector, same corpus | **8 of 51** |

The top family is `claude plugin`, re-derived in **4 sessions across 4 separate
projects** — and `plugin-finder` is installed on this machine precisely because that
syntax is worth not re-deriving, so the finding is independently corroborated by the fix
already existing. Verified end-to-end through `bin/checkchat`, not just in a unit test:
`recurring: ["claude plugin"]`, `other_sessions: 3`.

Four things came with it, each measured rather than assumed:

*The pre-filter is correctness, not speed.* `--siblings` bounds the scan, and it used to
bound it over all candidates, so the budget was spent parsing sessions that could not
contribute while the ones that could sat outside the window unseen — a silent zero
indistinguishable from a real one. Only transcripts whose bytes contain `--help` are
loaded now (18 of 234 here), so every slot goes on a session that might match. Recall
scales with the flag: 12 finds 3 of the 4 families, 18 finds all 4. The default stays
12 — spending the same budget better is not the same as tuning a threshold, and item 9
forbids the latter against this corpus.

*A session's own fork corroborated its own probe.* `exclude` drops one *file*, but
resuming copies the whole prefix, so the fork is a second file holding the same evidence,
left in the pool to confirm its original — one session counted twice, arriving by the
route the path exclusion does not cover. Fixed with `exclude_forks_of`. **This is the
guard the old item asked to see demonstrated, and the corpus cannot demonstrate it: of 18
real probing sessions, 0 form a fork family, so removing dedup entirely changes no
measurement.** A constructed fork in the tests is the only evidence it works, and it has
a negative control so that "suppresses everything" cannot pass as "suppresses forks".

*Two parse bugs that invented commands nobody ran.* `\s` spans newlines and a Bash call is
routinely a multi-line script, so `pip3 install --help` was reported as the family
`--version pip3 install`, spliced across a line break — the roadmap's own "do not glue
lines together", now for the third time. Separately, leftmost-match plus a two-word limit
made `claude plugin marketplace add --help` come out as `plugin marketplace add`, naming
an executable that does not exist. Neither changes what fires; both changed a name shown
to the user, which for this project is the worse defect.

*A refused command corroborated a real one.* `here` had always excluded declined calls
and the `others` side had not.

8 new tests, whose positive control is the scope bug itself: the per-directory result is
asserted to be blind, so a regression restores a measurable zero rather than passing
quietly.

Cost: the deterministic pass goes from ~86 ms to ~281 ms, and that is the price of the
comparison actually happening — this directory had only 4 siblings to load, against 12
probing sessions machine-wide. The scan itself is 12 ms; the rest is parsing. Bounded by
`--siblings`, and `--siblings 0` still disables it.

Left alone deliberately: `python3 -m rotmeter --help` yields the family `-m rotmeter`,
because a continuation word must start with a letter so the `python3` head is dropped.
The name is recognisable, no fix is obviously right, and rejecting flag-led families was
measured to change nothing (8 of 51 either way). Not worth a guess.

**12. Every check audited for item 4's failure — and the rule that decides it**
(2026-08-10). Item 4's zero survived two rounds of "cut it" because a zero is easier to
believe than to audit, so the immediate follow-up was to ask the same question of every
other check before writing anything new: **is this measured over the population its own
remedy lives in?**

**The rule, which answers it without measuring anything:**

> Re-scoping a check to the machine is safe only when its evidence does not depend on
> state that changes between sessions.

A `--help` probe is proof of not-knowing *whatever* is on disk, so it survives the trip
across sessions intact. That is why item 4 worked, and it is not a general property.

Audited by asking what each check's remedy is and what scope that remedy lives at. Ten are
sound by construction — `partial_use`, `dumps`, `rereads`, `spill`, `batching`,
`grounding`, `sycophancy`, `continuity`, `failures` all rest on within-session
observables, and `specification` is already correctly filed under item 9 as a wrong-
*population* problem that no re-scoping fixes. Two looked like item 4 and were measured:

**`producers` — flagged, and the rule says no.** Its remedy is a cached artifact or a
script, which is per-user, so the shape matched exactly. But its two guards are named
load-bearing in its own docstring, and **the strong one cannot exist across sessions**:
"no intervening mutation" is a within-session observable, because arbitrary time passes
between sessions and files certainly change. Cross-session it would keep the weak guard
(the filter varies) and lose the one that matters. Measured, and the result is not
ambiguous — 8 producer heads run in ≥2 sessions with varying filters, and they are
`.venv/bin/pytest -q`, `python3 -m pytest tests/`, `./test.sh`, `python3 -m venv .venv`,
`gh auth status`, plus three `--help` probes already counted by `cli_probes`. That is
**precisely the list the within-session guards exist to suppress** — the docstring names
`pytest | tail` and `./test.sh` by hand. Against 2 real within-session findings in the
whole corpus. The crude variant is just as empty: an identical full Bash command appears
in ≥2 sessions **5 times out of 1,258**, three of them `ls -la`, `sed -n`, `./test.sh`.

**`effort` — flagged, and it is not blind.** Remedy is a per-user setting, but the
evidence is per-turn and already sufficient per session: 13 of 51 sessions show any
overkill or circling, and the ones that matter already fire (top session 12 overkill
turns). Corpus totals are overkill 33, circling 5, mix `{max 51, xhigh 74, high 56,
medium 28}`. Aggregating across sessions would *strengthen* the recommendation — "you do
this habitually" beats "you did it twelve times" — but it fixes no blindness and it would
mean setting a threshold against Daniel's corpus, which item 9 forbids. Filed as an
option, not a defect.

- *Done.* No code changed, which is the point: the audit's output is a rule and three
  recorded verdicts, and it cost far less than the detector a corrected zero would have
  spared

---

## Now — nothing, and that is a measured statement

Every check has been audited for item 4's failure (item 12), no defect is outstanding, and
the three remaining features are each blocked or undesigned. The unblocked one is **item 8**
— the counting dimension has no open-world escape hatch at all, which is the shape of hole
item 4 sat in. Read item 12's rule before touching any of them.

---

## Later — features, in value order

**6. `re_ask` — semantic near-duplicate detection.**
The junior-developer loop: vague question → generic answer → the same question reworded.
Deferred deliberately, and it is the **one place an encoder earns a dependency**, because
char-n-gram similarity scores *"how do I fix this?"* against *"what's wrong with my
code?"* near zero while a sentence encoder does not.

Its real value is not accuracy: **re-asking is signal *and* free label.** If the user
rephrases, the previous answer demonstrably failed — the same self-carrying ground truth
that makes `partial_use` the headline finding, and nothing else in the specification
dimension has it.

Ship as an *optional* accelerator: `fastembed` (ONNX, ~50 MB) if importable, char-n-gram
fallback otherwise, and say in the output which ran. Do not make it a hard dependency —
stdlib-only is a real property worth keeping. **Measure whether the encoder beats the
fallback before taking the dependency**; on Daniel's corpus both score zero and are
indistinguishable.

Audited under item 12 and its zero is *not* item 4's: a re-ask is only a re-ask within one
conversation, so one session is the right population by construction, and no re-scoping
would change the number. What blocks this is item 9 — the wrong user, not the wrong query.
Same verdict for item 7, which is justified by the same corpus.

**7. `generic_answer` — TF-IDF against the repo's own vocabulary.**
"Is this answer about *this* codebase, or a tutorial?" No neural net needed. Proposed,
never built.

**8. Close the open world on the *counting* dimension.**
`other_findings` recovers open-world recall for judgment only — the judge sees the prose
digest, not the tool-call ledger, so an unanticipated *waste* pattern remains invisible
to everything. No design for this yet. Possibly: hand the judge a compact tool-call table
and ask what looks wasteful, accepting that it counts worse than Python does.

---

## Blocked on input Daniel does not have

**9. Calibrate the specification / junior-auditor checks.**
They have only **synthetic** positive controls. Daniel's corpus is the negative control
for the second time — median 1 turn to first edit, essentially zero re-asking — so it
establishes no base rate and no threshold for the population these were built for.
- *Unblocks when:* real transcripts from a junior developer exist
- Until then: do not tune thresholds against Daniel's sessions. That corpus can only show
  the detectors are quiet for an expert, which is the correct behaviour and not evidence
  of anything else.

**10. Compaction awareness.** Built, measured, and cut on 2026-08-10 — kept here because
the *reasoning* survives the measurement and is the expensive half to rediscover.

**Why it matters.** After a compaction the assistant holds a summary, not the text. So
re-asking for something settled before the seam is **correct behaviour, not `confusion`**,
and a constraint from before it was *lost*, not disregarded. Same observation, different
defect, and — the part that pays — a different repair: **restating the constraint fixes a
compaction loss; starting a fresh chat does not.** A judge that cannot see the seam scores
amnesia as degradation, which is the exact false positive this whole plugin exists to
avoid.

**Why it was cut.** The implementation read a large drop in context depth as a
compaction. Measured across 232 transcripts:

| measurement | result |
|---|---|
| Consecutive depth measurements above the 40k floor | **4,155** |
| …where depth fell below the 0.6 threshold | **0** |
| …where depth fell *at all* (ratio < 1.0) | **0** |
| Compaction markers of any kind in the wire format | **0** — no key matching `compact`, no `type: "summary"` record |
| Session files that *begin* deep, i.e. as a continuation | **0** — first-response depth spans 13k–44k, ceiling 44,487 |
| Transcripts within 4x of the 24 MB read cap | **0** — largest 6.0 MB |

Depth inside a session file is **strictly monotonic, without exception**. Note carefully
what that does and does not establish: the corpus never compacts (deepest session 682k
tokens in a 1M window), so this is **zero observations, not a measured failure** — it
cannot distinguish "the rule is right and never triggered" from "the rule watches for
something this format never shows". Either way there is no ground truth to check a
replacement against, which is what disqualifies it.

- *Unblocks when:* one compacted transcript exists — deliberately produce one by running
  a session to compaction on a small context window, and keep the file
- *When it does:* the first-response-depth signal is the cheap one to try, because it is
  already measured. A ceiling of 44,487 over 50 sessions means a `> 60_000` first-response
  threshold has **zero false positives on the corpus today** — but confirm against the
  real file rather than assuming, since a compaction continuation might reasonably start
  *shallow* (a fresh summary) rather than deep
- **Do not re-tune the 0.6 depth-drop threshold.** 4,155 of 4,155 rose. The threshold was
  never the problem
- The pieces are small and their reasoning is recorded where it will be found: the
  detection note in `transcript.py`, the excerpt marker in `digest.py`'s docstring, and
  the `caveat` tier in `checks.py` is already built and shipping. The judge guidance was
  three rules — `confusion` → 0 across the seam, `constraint_retention` → still a finding
  but say it straddles the seam, `self_consistency` → amnesia rather than contradiction —
  and it was cut from the prompt because ~25 lines read on every dispatch for an event
  never observed is a poor trade, not because it was wrong

---

## Known limitations — accepted and documented, not bugs to fix

- **Blinding is enforced by instruction, not by the sandbox.** `tools: []` was the intent;
  the harness grants *all* tools for an empty list. The judge is `tools: ["Read"]` and is
  told to read only what it is given. Re-test if the harness ever supports an empty grant.
- **The registry seam has leaked findings twice** — `rereads` returning `fires` where the
  registry reads `fired`, and the text renderer's hardcoded dimension list. Both were
  computed correctly and dropped on the way out. A third leak is likelier than it looks;
  when adding a check, verify it appears in `--text`, not just in the JSON.
- **`looks_english` is an unvalidated stopword heuristic.** It only decides whether
  sycophancy candidates get *ranked*, so failing it degrades ordering, never recall.
- **`spill` depends on harness English wording** (`Output too large … saved to:`). It will
  break silently if that string changes. The `tool-results/` path pattern is the robust
  half.
- **One check's needle is held by `__main__`.** `discover.siblings(contains=...)` gets
  `detect.PROBE_NEEDLE` from the caller, so the sibling scan is pre-filtered for the only
  cross-session check there is. A second such check wanting different data would be
  **silently starved** — it would see a filtered population and report a confident zero,
  which is item 4's failure mode arriving by a new route. That is the moment to make the
  data requirement something a check declares in the registry, and both docstrings say so
  at the point where someone would hit it.
- **`cli_probes` reads other projects' transcripts.** Only the command family crosses the
  boundary, never file contents, and it stays on the machine — but a report for project A
  can now name a command probed in project B. `--siblings 0` disables it.

## The API question, and what items 2 and 11 settled about it

There is **no SDK, no framework, no API client** anywhere in this plugin — no
`anthropic`, no POML, no PydanticAI, no HTTP at all. Dependencies are stdlib only. The
LLM is reached through Claude Code's own subagent mechanism, which is why the plugin
only works inside Claude Code and could not run over transcripts in CI without new code.

That is why items 2 and 11 exist: there is no API layer to pin a response format, so
enforcement happens *after* the reply, in `verdict.py`. Both items were the cheap half of
what an SDK would have given — a schema check and a grounding check on the fields the
schema cannot reach — and neither needed a dependency to get. **A structured-output API
would still not have caught item 11's failure**, because a fabricated quote is a
schema-valid string; only comparing it to the excerpt catches it. Worth remembering before
concluding that the missing SDK is what is holding this back.

---

## Do not rebuild these — each was measured to nothing

Kept because every one of them looks plausible, and two predecessor signals were built on
intuition and later measured at chance. That failure is the reason this evidence base
exists.

| Idea | Measurement |
|---|---|
| Stale-knowledge / repeated-error clustering | 1 true instance in 1,968 tool results; the obvious implementation scores **0/2 precision, 0/1 recall** |
| Recency bias, semantic drift, anchor loss, terminology mutation | All die against a null. A within-session **shuffle reproduces the trend identically**; own-anchor containment is flat (0.102 / 0.086 / 0.093 / 0.112). rot-metrics already built, measured (AUC 0.49–0.53) and disabled this exact detector |
| Generic recurring tool-call sequence miner | Exactly **zero**. Of 684 consecutive-Bash trigrams, 7 repeat anywhere and **0 across sessions**. The naive version looks like it works — every apparent hit is the duplicate-log artifact the fork-dedup guard exists to remove |
| Byte-identical re-read / within-session re-fetch | Verified **0**. Fourteen repeat `Read`s share byte-identical *args*; none share byte-identical *results*, and 12 of 14 had the file edited in between |
| Compaction as a **drop in context depth** | **0 of 4,155** consecutive measurements above 40k fell at all — depth is strictly monotonic within a session file. The threshold is not the problem; see item 10 before rebuilding this |
| Quote checking **scoped to one speaker's line** | Rejected on reasoning, not measurement: it false-fails a `self_consistency` quote that elides across two exchanges — the item where cross-exchange quoting is the *point*. Item 11 checks presence, not attribution, deliberately |
| Cross-session comparison **scoped to one project directory** | The inverse entry: this one was measured to nothing and the measurement was *right about the number and wrong about the cause*. 0 of 51 sessions per-directory, 8 of 51 machine-wide, same detector and same corpus. Do not narrow it back for cost — the pre-filter already bounds that, and the flag exists |
| **`producers` across sessions** | 8 heads in ≥2 sessions, and every one of them is `pytest`, `./test.sh`, `venv`, `gh auth status` or a `--help` already counted elsewhere — the exact list the within-session guards were written to suppress. The "no intervening mutation" guard **cannot exist** at that scope. Identical full command in ≥2 sessions: 5 of 1,258. See item 12's rule |
| **Same file re-read in many sessions** ("it should be in CLAUDE.md") | Measured, and the base rate is real — 36 of 132 files read in ≥2 sessions — but the interpretation inverts. The five most re-read files are `HANDOFF.md`, `ROADMAP.md`, `CLAUDE.md`, `README.md` and the project's main source file, at 5 sessions each. Those are **orientation files being used for orientation**; a fresh session has no memory and re-reading them is the correct behaviour, not waste. There is no remedy to recommend |

---

## Measuring against the corpus — ways to get a false answer

Each cost a full re-run to discover, so they are recorded here rather than relearned.

- **`cd x && grep */*.jsonl` fails silently in the tool environment.** The `cd` does not
  persist and the glob expands in the wrong directory, so it reports nothing and looks
  like a real zero. Use
  `find ~/.claude/projects -name '*.jsonl' -print0 | xargs -0 grep …`.
- **Transcript JSON has spaces after its colons**, so `grep '"type":"assistant"'` matches
  nothing at all. Another zero that is not a measurement.
- **Sweeping for text? Do not glue lines together.** Item 11's first measurement reported
  147 false fails, every one of them a sentence the *harness* had spliced across two
  records. When a sweep contradicts working code, suspect the sweep first — this has now
  happened three times: the `Step.depth` carry-forward in item 10, and `\s` spanning a
  newline inside `_family` in item 4, which invented a command out of two lines of one
  Bash script. Where a line boundary is meaningful, say `[^\S\n]` and mean it.
- **A zero is a measurement of the query as much as of the corpus.** The most expensive
  one yet: `cli_probes` returned 0 across the whole corpus for its entire shipped life,
  the number was correct every time, and the detector was twice queued for deletion —
  because the comparison population was one project directory when the question spanned
  the machine. Nothing about the zero looked wrong. Before believing one, state what
  population would have to contain the signal and check that is what was searched; the
  cheap version of that question is *"if this fired, what would the fix be, and is it
  scoped the same way as my query?"* — a per-user remedy measured per-directory is the
  tell.
