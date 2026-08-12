# Roadmap

State as of 2026-08-11. Published; see "Done" below. Written so a session with no memory of how this got here can
pick it up.

The plugin is **installed and working end-to-end** on this machine: `/check-chat` runs,
the deterministic pass takes ~280ms (~86ms of it before item 4 made the cross-session
comparison actually load other sessions; `--siblings 0` returns it to ~20ms), the judge
dispatches by `subagent_type`, and the report comes back. 90 tests pass, in the project's
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

**13. Prose about a command is no longer counted as running it** — `_shell_code`
(2026-08-10). `cli_probes` reported `recurring: ["pip3 install"]` on the session that had
just finished repairing it, and no such command had been run. `_family` scanned the whole
Bash `command` parameter, so text that merely *discusses* a command counted as a probe.
With item 4's cross-project comparison live this was no longer a harmless miscount: it
manufactured a **"this should be a skill" claim for a command nobody invoked**, which is
the loudest thing this detector says.

Two kinds of data carry command-shaped text, and **fixing one was not enough** — the
first attempt stripped heredoc bodies, and the corpus firing count did not move at all
(10 of 18, unchanged), because the same phantom arrived again by a second route:

| route | the text | verdict |
|---|---|---|
| heredoc body | `git commit -F - <<'EOF'` carrying a commit message *about* the `--help` parse bug fixed minutes earlier | data |
| quoted literal | `echo "=== did I actually run 'pip3 install --help' … ==="` — a shell label | data |

So the unit is now "the parts of the command the shell will execute", with both stripped.
Measured before and after: **10 of 18 probing sessions fire → 8 of 18**, and the two lost
firings are exactly the phantom. **No real family is lost** — `claude plugin` 4,
`claude` 4, `claude plugin marketplace` 2, `claude plugin install` 2, unchanged — and
`pip3 install` drops from 2 sessions to 1, the one that genuinely ran it.

Quote stripping is **line-local**, because an unbalanced quote is ordinary in these
commands (an apostrophe in an `echo`, a `sed` expression) and a quote state running to the
end of a multi-line script would swallow every command after it — one stray character
buying a silent zero for the rest of the call. Command substitution is deliberately not
carved out: `$(gron --help)` inside quotes really is a probe, but there are **0 of those
in the corpus** (measured, not assumed) and the carve-out costs a nested parser.

3 tests, and the negative control is the point — a guard that suppressed everything would
pass the phantom test while leaving the detector as dead as items 4 and 12 twice thought
it was. So a probe on a later line, a probe on the same line *after* a quoted label, and a
probe after a heredoc closes are all asserted to survive.

**What this says about measuring against a corpus, and it is the lesson worth keeping.**
Item 4's fix was measured against 234 transcripts and was right about every one of them.
The corpus contained no prose about `--help`, so the hole could not show up in it — and it
appeared within the hour, as soon as the tool was pointed at a session that wrote *about*
commands rather than running them. **A corpus cannot contain the artifact that a new kind
of session will produce**, so a clean sweep is evidence about the past, not a proof of
correctness. Two of this project's checks now exist because it was run on itself; that is
the cheapest source of novel input it has, and it should be run on the session that
changes it, every time.

---

**14. The counting dimension has an open-world escape hatch** — the tool-call ledger
(2026-08-11). Closes item 8.

`other_findings` gave the judge open-world recall over *prose*. The counting dimension had
none at all: the judge saw `[tools: Read x3]` and never what those calls touched, so a
pattern nobody wrote a check for was invisible to the checks (they only find what was
named) *and* to the judge (it could not see targets). `digest.ledger()` adds one row per
call — tool, target, result size, failure flag — and a `wasted_effort` question asks what
the request did not need.

**The ledger lives inside the excerpt, and that placement is the design.** `verdict.check`
already verifies quotations against whatever the excerpt contains, so a finding citing a
tool call is checkable *for free*, by the same machinery, with no second verification path
to drift out of step. `wasted_effort` reuses `_clean_findings` for the same reason.

**Blinding survives by construction — one-directionally.** Rows cover only the exchanges
already in the excerpt and carry the same renumbered `E<n>`, so the ledger never discloses
a count the `[tools: ...]` line did not. Measured against the shipping code on 54 sessions:

| measurement | result |
|---|---|
| exchanges disclosing **more** rows than `[tools: ...]` states (the leak) | **0** |
| rows labelled with a transcript position instead of an excerpt one | **0** |
| exchanges disclosing fewer — all inside a session the row cap truncated | 24 |
| sessions hitting `LEDGER_ROWS = 120` | 7 of 54 |
| calls falling inside digest scope | **89%** |
| cost: ledger chars | median 2,040, p90 8,048 (~2k tokens), max 9,838 |
| ledger as a share of the excerpt | median 30%, p90 67% |

Do not restate that invariant as equality. It is `rows <= tools_line`, and the cap is why.

**What measurement changed about the plan.** Item 8's sketch was "hand the judge a compact
tool-call table and ask what looks wasteful." Measured on the corpus, both readings of that
question come out near-null *and* dangerous:

- *"What looks wasteful?"* — the only thing visible at volume is a repeated `(tool, target)`,
  present in **10 of 54** sessions while `rereads`, `producers` and `partial_use` are all
  correctly quiet. Those repeats are ordinary work: two `Edit`s to one file, a `Read` after
  an `Edit`, a test re-run after a change. The Python checks exclude them deliberately. A
  judge asked the open question reports them, counting worse than Python and manufacturing
  the false positives this plugin exists to avoid. **So the prompt fences repeats off by
  name**, and the skill discards any that arrive anyway.
- *"Claimed but never did?"* — 27 claim-verb-plus-path mentions in digest prose corpus-wide,
  **5** naming a file never `Edit`/`Written`, across **4 of 54** sessions, and those five look
  like prose discussing files. No volume here either.

**Corpus frequency is the wrong test for an escape hatch, and that is the reusable part.**
`other_findings` would score just as null on this corpus and nobody would call it
unvalidated: its justification is structural, not frequentist — it is the only part of the
system that can see outside its own categories. So an escape hatch is judged on three
things instead, all of which this one meets: it is **bounded** (quote-verified, so it cannot
invent work), it is **cheap** (~2k tokens at p90), and the information it carries is
**genuinely absent today** (targets never reached the judge, by construction). Do not
demand a positive rate from the next one either.

**Two bugs found by reading the real output, not by reasoning about it** — both would have
shipped as silent misinformation:
- Three `Read`s of *different slices* of one file rendered as three identical rows, showing
  the judge a repeat that never happened — the ledger manufacturing the exact false
  positive its own prompt fences off. Fixed with a `[lines a-b]` marker.
- Middle-truncating every target cost long Bash commands their head, which is the end that
  identifies a command, while paths are identified by their tail. Now split on whether the
  key contains whitespace.

**A missing `wasted_effort` key is a warning, not an empty list.** `[]` means the ledger was
assessed and was clean; absent means the question went unanswered. Letting those read alike
would put a confident zero on the dimension by omission, which is item 4's failure mode
arriving through the output format. 11 tests.

**15. `rereads` no longer counts different slices of one file as waste** (2026-08-11).

Found by building item 14, not by looking for it: the ledger's first draft rendered three
reads of *different* slices of one file as three identical rows, and fixing that raised the
obvious question of whether the shipped detector made the same mistake. It did — `rereads`
grouped by path and never looked at `offset`/`limit`.

| measurement | before | after |
|---|---|---|
| `repeats_without_change`, corpus-wide | 38 | **11** |
| …excluded as disjoint slices | — | **27 (71%)** |
| sessions where the check fires | 6 of 54 | **1 of 55** |
| on the session that found it | 5 unchanged, 16,792 chars | **1 unchanged, 2,599 chars** |

**Why this one was urgent.** `rereads` is `evidenced` tier, which the skill reports "with
the quoted specifics" — so 71% of the time it was telling a user, with specifics, that they
wasted tokens they never spent. **That is item 4's failure with the sign flipped, and it is
the worse direction: a false zero stays quiet, a false positive argues.** Every check has
now been audited for the false-zero shape (item 12); nothing had been audited for this one.

Two things worth keeping:
- **Consecutive pairing was independently wrong.** `A, B, A` is two disjoint pairs, so the
  genuine re-fetch of `A` was missed. Each read is now compared against *every* earlier
  still-valid read, which fixes a recall bug the precision fix would otherwise have hidden.
- **A whole-file read has no span and overlaps everything**, which is correct rather than a
  special case — reading the whole file after a slice does re-fetch that slice.

`repeats_disjoint_slices` is reported beside `repeats_after_edit` for the same reason that
one is: a number is credible next to what it excludes, and both of these were once counted
as waste. `rereads` is now genuinely rare, which makes its `evidenced` tier more accurate
than before, not less. 4 tests.

**10. Compaction awareness ships — and the blocker was an action, not a wait**
(2026-08-11). Item 10 sat under "blocked on input Daniel does not have" for a day. It was
the only blocked item whose input Daniel could *manufacture*, and doing so took about
twenty minutes:

`CLAUDE_CODE_AUTO_COMPACT_WINDOW` is read in tokens and clamped to a floor of `1e5`, so a
throwaway session in a scratch directory, seeded with ~69k tokens of generated notes on
Haiku and then given one more turn, crosses the window and compacts. `trigger: "auto"`.
A following `claude -p -c "/compact"` adds a second seam, `trigger: "manual"`. **Two seams
in one real file**, which is more than the item asked for.

**The premise was wrong, in the most useful direction.** This item recorded "no compaction
marker exists anywhere in the wire format", and that was a statement about the *corpus*
wearing the clothes of a statement about the *format*. The format has an explicit record:

```json
{"type":"system","subtype":"compact_boundary","content":"Conversation compacted",
 "compactMetadata":{"trigger":"auto","preTokens":100817,"durationMs":15628,
                    "preservedSegment":{…},"preservedMessages":{"uuids":[…]}}}
```

and `type: "system"` records demonstrably persist — 323 of them in the corpus across four
other subtypes. So the zero was "never compacted", not "never written down". **No
heuristic, no threshold, no detector**: this is `truncated`'s class, a fact the harness
states about its own action, which is the only reason it could ship the same week it was
unblocked. The item's own plan — try the first-response-depth signal at `> 60_000` — was
superseded and never built.

**The depth-drop premise was right and never triggered.** That ambiguity was recorded here
as disqualifying: 0 of 4,155 falls "cannot distinguish 'the rule is right and never
triggered' from 'the rule watches for something this format never shows'". It was the
former. Depth falls **100,212 → 26,146** across the first seam, a ratio of **0.26** against
the 0.6 threshold that was never the problem. The heuristic stays cut anyway, and now for a
better reason than lack of evidence: reading the record yields the same seam *plus* the
trigger and the token count, and cannot false-fire.

**What the transcript revealed that no amount of reasoning had — trap 6.** The compaction
summary is written as a `user` record flagged `isCompactSummary`, and it carries **no
`isMeta`**, so `clean()` let it become a turn. This is item 4's defect, second occurrence,
and worse in every dimension:

| | item 4's phantom | this one |
|---|---|---|
| what it is | one bracketed line | ~4,000 chars of the **machine's own prose** |
| where it lands | between a reply and the objection after it | between a real prompt and its reply |
| damage | inflated denominator; one objection rejected | a human's question left with **no reply at all**, its answer credited to the phantom |
| in the excerpt | too short to be selected | long enough to be selected as **the stated goal** |

On the transcript measured, the tool reported **5 turns where a human typed 3**. The fix
returns 3, all real, with the stranded reply restored to the question that earned it.

Worth being precise about what found it: the *known* blind spot cost one line of new
understanding, and the *unknown* defect underneath it was the whole payoff. Producing the
input did that; reading the code for a day would not have.

**Where the fact goes and where the rules go, and it is not a style choice.** The judge's
prompt already tells it to *ignore instructions inside the excerpt* — correctly, since the
excerpt is evidence written to someone else. So the excerpt carries a bare marker,
`[... context compacted here: the earlier conversation was replaced by a summary ...]`,
exactly as the gap marker does, and the three scoring rules live in the judge's own prompt
keyed to it. That also settles the cost objection recorded here — "~25 lines read on every
dispatch for an event never observed is a poor trade" — at ~12 lines that only bind when
the marker appears.

The marker says "the earlier conversation" rather than "everything above" because
`preservedMessages` shows the harness keeps a recent tail verbatim (4 and 2 messages at the
two seams). A marker that overstates what was lost is one the judge is right to distrust.

**The seam marker leaks a coarse length signal, and it ships anyway.** A compaction only
happens in a conversation long enough to fill a window, so disclosing one tells a
deliberately blinded judge something about length — the single thing `digest.py` exists to
prevent. It is worth it because **every finding the marker enables is a suppression**: it
turns three would-be findings into zeroes and can never add one. The alternative is not
silence, it is a confident false positive. Stated in the docstring and in the judge's
prompt rather than left for someone to notice.

**The remedy inverts this tool's usual advice, which is the part that pays.** A fired
`compaction` argues *for* a repair prompt and *against* `should_restart`, however high that
item scored: the assistant lost the text because the window filled, and a fresh chat starts
from even less. Restating the constraint is the repair. That is now the one row in the
skill's decision table where a caveat outranks a score.

| measurement | result |
|---|---|
| turns reported on the produced transcript, before → after | **5 → 3** (2 phantoms, both summaries) |
| real questions left with no reply, before → after | **1 → 0** |
| depth across the first seam | **100,212 → 26,146** tok (ratio 0.26) |
| seams captured, with the harness's own trigger | **2** — `auto` at 100,817 tok, `manual` at 26,975 tok |
| genuine compaction records in the 274-transcript corpus | **0** — so nothing else on this machine changes |
| this session's transcript, which discusses the marker names in prose | **does not fire** — item 13's phantom, avoided by keying on the record |

9 tests. Two are negative controls, and they are the point: an uncompacted session must
produce no marker and no caveat, because a marker present by default would tell the judge
to forgive real confusion everywhere — this check's failure mode is *silence*, so it has to
be shown to be silent. The live one is better than the written one: **this session's own
transcript contains 38 lines of prose about `compact_boundary` and `isCompactSummary`**, and
the check correctly ignores all of them.

Shipping on structural justification rather than a rate, per item 14's rule: the corpus
contains zero compactions and always will while Daniel runs a 1M window, so frequency here
measures his settings, not the defect. The defect is *demonstrated* on the only transcript
that can exhibit one. And the audience makes it strategic rather than merely correct —
everyone on a smaller window compacts routinely, so the plugin's largest blind spot was
invisible in the author's corpus and universal for its actual users. `caveat` did its job
again: no consumer of the tier was edited, and the new check hoists above the numbers it
reinterprets on its own.

**16. A session with no human turn fails instead of judging a blank page** (2026-08-12).

Item 10's downstream consequence, and it exists *because* trap 6 was fixed correctly. A fork
or resume of an already-compacted session opens on the summary record; that record is no
longer counted as a turn, so such a transcript holds assistant responses, tool calls and a
seam, and nothing the user typed. `collect` guarded `not sess.steps` and never the mirror
case, so it went straight on: `digest.selected` picks `range(0)` exchanges, `build` returns
`""`, and the judge is dispatched to grade an empty excerpt.

**The failure mode is that it does not look like one.** The checks still run and still fire —
`compaction` and `batching` did, on the reproduction — so the report arrives with numbers in
it and a caveat at the top, reading exactly like a measured session. Not a crash, not a blank
report: a confident one about a conversation that is not in the excerpt. That is the shape
this project treats as worse than a gap, so the guard returns an error and `--emit` writes
nothing at all.

The repair is stated in the error, because it is not the obvious one: **take a turn and
re-run**, or point `--session` at the transcript that holds the conversation. Restarting is
the wrong move here for the same reason item 10 says it is wrong after a compaction.

A second defect came out of the same file, and it is the more valuable half. `_text` rendered
`d["error"]` and dropped `d["hint"]` — so the *actionable* half of every error has been
silently truncated for the human-readable renderer's whole life, including `no transcript
found`, whose hint says `pass --session <id>` and is the fix for the commonest failure this
tool has. **That is the Known Limitations leak for the third time**, and the note there
predicted it: computed correctly, dropped on the way out. It said a third was likelier than
it looks. It was already there.

Also corrected while in `transcript.py`: the removed depth-heuristic's comment still ended
"no compaction marker exists anywhere in the wire format", fifty lines above the code that
now reads that marker. Item 10 flagged that sentence as a fact about the corpus wearing the
clothes of a fact about the format, then left the copy in the source saying it.

3 tests. The guard's asserts the defect first — empty `build`, checks firing — so the test
fails if someone removes the guard *or* if the empty excerpt ever stops being reachable for
a different reason. The renderer's is pinned on the oldest hint rather than the new one.

---

## Now — nothing, and that is a measured statement

Every check has been audited for item 4's failure (item 12), item 8 shipped as item 14, and
item 10 shipped by manufacturing the input it was waiting for. What remains is items 6, 7
and 9, blocked on transcripts from a *different user* — which is the one kind of input that
cannot be manufactured, and worth contrasting with item 10, whose blocker was misfiled as a
wait for a year's worth of luck when it was twenty minutes of work. Read item 12's rule
before touching any of them, item 13 before trusting a corpus sweep, and item 14 before
adding anything else to the excerpt.

This section previously read "no defect is outstanding", and that clause is now gone, because
it has been false every time it was checkable. It was written in `dda7bbe` while `rereads`
was miscounting 71% of its findings, and again in `ff26380` while item 16 sat in the code
that same commit had just shipped. Both were real defects in shipping checks, both were found
within a day, and neither was found by looking at this list. The claim this heading can
support is "nothing *found*", never "nothing there" — the difference being that the first is
a statement about the search and the second is a statement about the code.

The reason it fails in this specific direction is worth keeping: **this is the one list that
audits the audit tool, and it enumerates the checks rather than the pipeline around them.**
Items 4, 12 and 15 are all "a check computed the wrong number"; item 16 is the first where
every check was right and the *excerpt* was empty. Nothing verifies that `collect`'s output is
fit to hand a judge except `collect` itself, so a fourth of item 16's shape would be just as
invisible.

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

**8. Close the open world on the *counting* dimension.** — **done, see item 14.**
Shipped as a tool-call ledger inside the excerpt plus a `wasted_effort` question. The
sketch here said "ask what looks wasteful"; measurement said that framing is a false-
positive engine and the question had to be fenced. Item 14 has the numbers.

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

**10. Compaction awareness** — **done, see the Done section.** Shipped 2026-08-11 by
producing the transcript this section said it was waiting for. Everything below is the
state it was cut in on 2026-08-10, kept because the reasoning is what survived and one
line of it turned out to be false in a way worth leaving visible: *"no compaction marker
exists anywhere in the wire format"* was a fact about the corpus, written as a fact about
the format. The format has an explicit `compact_boundary` record, and the whole item
collapsed to reading it.

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

- *Unblocked exactly this way,* and the recipe is worth keeping because it cost twenty
  minutes: `CLAUDE_CODE_AUTO_COMPACT_WINDOW` is in tokens with a `1e5` floor, so seed a
  throwaway session with ~69k tokens on a cheap model, take one more turn, and it compacts
  itself. `/compact` in print mode adds a second seam with `trigger: "manual"`
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
- **The renderer seam has now leaked three times** — `rereads` returning `fires` where the
  registry reads `fired`, the text renderer's hardcoded dimension list, and `_text` dropping
  the `hint` on every error it printed (item 16). All three were computed correctly and lost
  on the way out. This bullet used to say "a third leak is likelier than it looks"; it was
  already in the code when that was written, and the third was not a *check* at all, which is
  why "verify a new check appears in `--text`" did not catch it. **The rule is wider than it
  was stated: nothing that `collect` returns is rendered by default.** Verify it appears in
  `--text`, not just in the JSON — for anything, not only checks.
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
- **The compaction marker discloses a coarse length signal to a blinded judge.** A
  compaction only happens in a conversation long enough to fill a window, so the marker
  tells the judge something `digest.py` exists to withhold. Accepted, because every finding
  the marker enables is a **suppression** — it can only turn three would-be findings into
  zeroes, never add one — and the alternative is not silence but a confident false positive.
  The judge's prompt says this outright, so the leak cannot be re-derived as a hint.
- **A seam in the excerpt's omitted middle is disclosed without its position.** The marker
  is printed beside the gap that swallowed it, which says a compaction happened *somewhere*
  in the cut material and not where. That is deliberate — a constraint in Exchange 1 can
  have been lost to a seam the excerpt never shows — but it means the judge cannot tell
  which side of the seam a given omitted exchange fell on, and it should not try.
- **The tool-call ledger cannot see the omitted middle.** It covers the excerpt's exchanges
  only — 89% of calls on the corpus, and the 11% it misses sit in the gap the digest already
  cut. This is deliberate: widening it to the whole session would disclose length and turn
  the judge into a prior, which costs more than the recall is worth. `LEDGER_ROWS = 120`
  truncates a further 7 of 54 sessions, and that cut is stated in the table rather than
  silent. So a `wasted_effort` null means "nothing in what you were shown", never "nothing
  happened" — the same distinction `sessions_compared` draws for `cli_probes`.

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
| Compaction as a **drop in context depth** | The entry that got *resolved* rather than confirmed, and it argues for keeping these rows. 0 of 4,155 falls, and the recorded worry was that this could not distinguish "right and never triggered" from "watching for something the format never shows". A produced compacted transcript settled it: **the rule was right** — depth falls 100,212 → 26,146, ratio 0.26 against its 0.6 threshold. It stays deleted regardless, because the harness writes a `compact_boundary` record and reading a marker beats inferring one. Do not rebuild the heuristic; do not read this row as the idea having been wrong |
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
- **A clean sweep is evidence about the past, not a proof.** Item 4's parse fix was
  measured against 234 transcripts and was right about all of them; the corpus simply
  contained no prose *about* `--help`, so item 13's phantom could not appear in it, and did
  appear within the hour on a session that wrote commit messages about commands. Ask what
  kind of session the corpus does not contain — and run this tool on the session that
  changes it, which is how two of its checks were found.
- **Measure the shipping function, never a model of it.** Item 14's first sweep hand-rolled
  its own row format to estimate the ledger, and reported the blinding invariant as **0
  mismatches out of 196**. Re-run against the real `digest.ledger()`, the same invariant
  showed **24** — every one the row cap under-disclosing, which is harmless, but the clean
  number had already been written into a docstring as equality and was wrong there. Import
  the function. If a sweep cannot call it, that is the finding.
- **Reading the producer is not reading the product.** Item 10's format was recovered from
  the harness binary before a compacted transcript existed, and its construction site sets
  `compactMetadata.postTokens`. The record the harness actually *writes* has no
  `postTokens` — it is assigned after serialisation. Two lines of code had already been
  written against it. This is "measure the shipping function, never a model of it" pointed
  at **someone else's** code, where it is easier to fall for: the source is not a model of
  the format, it looks like the format itself. Read the producer to find out what to look
  for; read a real record to find out what is there.
- **A blocker that names an artifact is a task, not a wait.** Item 10 was filed under
  "blocked on input Daniel does not have" beside item 9, and the two are nothing alike:
  item 9 needs *another person's* transcripts, and item 10 needed a file that any session
  can produce on purpose in twenty minutes with one environment variable. It sat for a day
  because both were written in the passive voice of waiting. When filing a blocker, say who
  or what would have to act — if the answer is "this project, deliberately", it is the next
  task.
- **State an invariant in the direction that can hurt you.** The same 24 mismatches were
  invisible as a problem *and* as a non-problem until the check was rewritten as `rows <=
  tools_line` rather than `==`. An equality that is false for a benign reason gets relaxed
  or deleted; a one-directional bound survives, and it is the one that means anything.
- **A zero is a measurement of the query as much as of the corpus.** The most expensive
  one yet: `cli_probes` returned 0 across the whole corpus for its entire shipped life,
  the number was correct every time, and the detector was twice queued for deletion —
  because the comparison population was one project directory when the question spanned
  the machine. Nothing about the zero looked wrong. Before believing one, state what
  population would have to contain the signal and check that is what was searched; the
  cheap version of that question is *"if this fired, what would the fix be, and is it
  scoped the same way as my query?"* — a per-user remedy measured per-directory is the
  tell.
