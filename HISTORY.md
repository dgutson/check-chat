# History — how each finished item got that way

Every item this project has shipped, with what was measured, what the filing got wrong, and
why the fix took the shape it did. **Nothing here is pending work**; `ROADMAP.md` holds that,
and its index says in one line what each item below settled.

Read an entry when you are about to change what it decided, when a number in the code looks
arbitrary, or when you are tempted to rebuild something. Do not read this file to pick a task
— that is what the roadmap is for, and this file was split out of it precisely because 773
lines of settled history was being loaded to answer a question it does not answer.

The entries are in the order they were finished, which is not their numeric order: an item's
number is when it was *filed*.

---

## Shipped items

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

**17. Blinding measured, and the judge's `1`s found not to be reproducible** (2026-08-12).

`digest.py` claims that a judge who can see "exchange 180 of 200" will report degradation
because long conversations are supposed to look degraded. The blinding *invariant* was
measured long ago — 0 over-disclosing exchanges across 54 sessions — but the **benefit never
was**, so the module's whole reason for existing rested on an assertion. 18 judge dispatches
later it still does, for a reason worth writing down.

**Design, because a sloppier version answers a different question.** Both arms get the same
exchanges from the same `selected()` call, the same 1200/1400 caps and the same ledger:
coverage is held constant so a difference is attributable to blinding and not to how much was
shown. Arm B differs in exactly three ways — true `Exchange n of N` labels, a stated total,
`_scrub` not applied — plus the two anti-position lines removed from the rubric, verified by
`diff` as the only rubric change. Same agent type in both arms, so agent identity is not a
confound either. Five sessions at 26/24/18/11/6 turns, paired so each session is its own
control.

| result | number |
|---|---|
| `should_restart` identical across arms | **5 of 5 pairs** |
| all six dimensions, exact agreement | **27 of 30 cells (90%)** |
| disagreements | 3, all `B > A`, both on the two longest sessions |
| does `should_restart` track length, either arm | **no** — 26t→0, 24t→0, 18t→1, 11t→0, 6t→**1** |

**That looked like a clean null and it was not, which is the actual lesson.** Replicating the
two disputed sessions to n=3 per arm dissolved all three disagreements into run-to-run noise:

| | `self_consistency` | `should_restart` |
|---|---|---|
| 4d46b43d arm A | {0,0,1} | {0,0,0} |
| 4d46b43d arm B | {1,0,1} | {0,**1**,0} |
| b3c7cb10 arm A | {0,0,0} | {0,0,0} |
| b3c7cb10 arm B | {1,0,0} | {0,0,0} |

So `should_restart` — the "identical 5 of 5" headline — **flips 0→1→0 across three runs of one
arm on one excerpt.** The agreement was luck. Arm A wanders on the same dimension, the
distributions overlap, and there is no arm effect to find. A weak variance asymmetry survives
in the counts (arm A unanimous in 11/12 cells, arm B in 8/12) at roughly p≈0.3 on n=3:
**recorded so nobody re-derives it, not to be built on.**

**The finding that outlived the question it came from.** Every observed flip was `0↔1`. Not
one involved a `2` or a `3`. The same excerpt, same rubric, same model returns
`self_consistency: 0` or `1` depending on the run — and the skill's decision table thresholds
at **≥ 2**, so the noise sits below everything that changes what the user is told. The
architecture absorbs it, whether by design or by luck.

**What this leaves open,** and it is narrow rather than nothing: a non-zero score is
*reported* at 1, with quoted evidence, presented exactly like a stable one. In this project's
own vocabulary a single-dispatch `1` is empirically **`weak` tier — "hedge explicitly, never
threshold it"** — while the report gives it `evidenced` framing. That is item 15's shape with
a different cause: telling a user with specifics about a defect that a re-run would score 0.
The cheap fix is to hedge `1`s in the report; the thorough one is to corroborate them, for
which the roadmap already has the pattern.

**Bounded exactly as far as the corpus allows, and no further.** Blinding shows **no
measurable effect at 6–26 turns**. It is *not* established that blinding does nothing: the
longest session on this machine is 26 turns and the claim is about 200, so the case the
mechanism was designed for was never in the sample. Same wall as items 6, 7 and 9 —
one user's corpus — and the asymmetry matters, because a null here is weak evidence for
removing blinding while a positive would have been strong evidence for keeping it. Do not
read this entry as licence to un-blind anything. Both arms were also the same model; a
weaker judge may lean on position more.

**One methodological note, recorded because the transcript shows the trap working.** Between
replicates arriving, the session twice narrated a pattern — first "Arm A is reproducible and
Arm B is not", then that the asymmetry was strengthening — and the final Arm A replicate
falsified it. A decision rule written before the data (which of three outcomes each result
would mean) is what kept it out of the conclusion. Item 13 warns about phantoms in a corpus
sweep; this is the same failure with live results, and the defence is the same one.

**18. A judge score of `1` now reads as the single read it is** — `tier`, `weak`
(2026-08-12). Item 17 measured a single-dispatch `1` as not reproducible while the report
presented it quoted and framed like a stable finding. Hedging it was the cheap option and
corroborating it was the thorough one; **the cheap one is not a compromise here, it is the
only one that can be built honestly.**

*Why corroboration was rejected, and the deciding reason is not the cost.* A second dispatch
needs a rule for disagreement — take the lower score, the higher, the mean, or re-dispatch
until two agree — and **every one of those is a threshold, set against this corpus, which
item 9 forbids.** So the thorough version was not merely twice the price; on the evidence
available it could not be specified. The cost argument is real too and comes second: it
doubles the LLM half of every run to stabilise a number the decision table never reads.

*What made the fix small, and it is the part worth keeping.* The instability is **symmetric**
— a reported `0` may equally have been a `1` on another run — but only a non-zero score turns
into a quoted sentence in front of the user. A `0` produces no prose, so there is nothing to
frame with more confidence than it deserves. **The whole exposed surface is the non-zero half
of an interval the user never acts on**, which is why this cost one field and no dispatches.

Each scored item now carries a `tier` in the same vocabulary the checks use — `weak` at 1,
`clean` at 0, `evidenced` at 2 and above — so the skill's existing row for `weak` ("hedge
explicitly, never threshold it") applies verbatim and no new word was invented. Selected by
tier rather than by score, exactly as `caveat` is selected by tier rather than by name.

**The claim is stated one-directionally, per this list's own rule.** `evidenced` at ≥ 2 is a
*reporting instruction*, not the mirror of the measurement: no `2` or `3` was ever observed to
flip, and that is an absence of evidence about the upper half of the scale rather than
evidence of stability there. Written into the docstring in that direction so nobody later
cites the tier as a reproducibility result.

**The hedge is in the rendered line, not in a legend.** `[weak: one read; a re-run may score
0]` prints beside the score itself, repeated per item, instead of a bare tag explained in
`SKILL.md`. A tag whose meaning lives somewhere else is a tag that gets reported as a finding
by the first reader who missed the explanation — and the reader here is a model reading a
report, which is precisely the failure this project keeps finding in its own output.

*One correction to this item as it was filed.* It said to verify the result in `--text`, and
`--text` renders `collect()`, which contains no judge scores at all — the judge's reply
reaches a human through `verdict.render`, printed by `--verdict`. Item 12's rule survives the
correction and generalises slightly: verify it in **the human-readable renderer for that
data**, which is not always `--text`. Confirmed by hand through `bin/checkchat` on a mixed
reply, where a `1` carries the hedge, a `2` does not, and an unverified quote's mark sits
beside the hedge saying a different thing.

3 tests, and the negative control is the one that matters: hedging *everything* would satisfy
the positive test and communicate nothing, so a `2`, a `3` and an all-zero reply are each
asserted to render unhedged.

**19 + 20. The renderer seam is mechanised, and the label is declared** (2026-08-12).
Done together because they are one seam: 20 decides what 19's test is written against.

*Item 20's answer is **declared**, not derived.* Three checks print under a word the registry
does not use — `cli_probes`→`cli`, `partial_use`→`partial`, `specification`→`spec` — and
deriving them needs a rule that fits all three. "First underscore-separated token" fits two
and not the third, so derivation here is three special cases wearing a rule's clothes. The
label is therefore a registry field, applied in exactly **one** place (`checks.line`), and a
check now returns `summary` — the sentence, without the label. A stale label stopped being a
thing that can exist rather than a thing a test catches. It is also printed beside its name in
`--catalog` and carried in the JSON, which is the other half of item 20: a word a reader sees
in `--text` must be lookupable somewhere.

*The refactor is byte-identical.* `--text` over a fixed transcript, rendered by `HEAD` and by
the working tree, diffs to nothing — every label already sat in an 11-column field, so the
padding constant reproduces all fourteen exactly. Worth doing that way: the whole change is
invisible to a user, which is the only kind of refactor this seam should get.

*What the mechanism is.* Three walks, each enumerating a producer and asserting everything it
computes reaches a renderer a person reads: the registry into `--text`, `collect()`'s keys
(and `session`'s, one level down) into `--text`, and `Verdict`'s dataclass fields into
`verdict.render`. Anything deliberately unprinted goes in `cli.TEXT_OMITS` **with the renderer
that does show it** — an omission has to name a reader, not merely be silent.

*This answers item 19's open question — one mechanism, or one per seam? **One rule, three
walks.*** The rule is shared; the enumeration cannot be, because the producers are a registry,
a dict literal and a dataclass, and each is walked in its own way. A single generic mechanism
over all three would have had to invent a common shape they do not have.

*What it found the moment it existed — four leaks, and not one of them is a check:*

| leak | consequence |
|---|---|
| `capabilities` printed nowhere | the skill *branches* on whether `plugin-finder` is installed, and following its own instruction to use `--emit` it could never see the answer. `SKILL.md` said to read it "in the JSON", which contradicts "never read the raw JSON" three sections earlier — the excerpt rides along with it. Now a summary line, and the list arrives via a shell filter that never enters context |
| `cwd` and `path` on the error path | "no transcript found for this directory" never said **which** directory. Item 16 fixed the `hint` beside them and left these; they are now rendered by walking the dict, so the next key an error carries needs no edit |
| `candidate_verdicts` absent from `verdict.render` | the judge's ruling on each located candidate — the headline of the dimension this plugin is named for — reached `--json` and not the renderer `SKILL.md` tells the skill to read |
| `session.model`, `digest_exchanges`, `digest_gapped`, `path` | the excerpt pair is the one that matters: **a verdict over 8 of 40 exchanges is a different claim from a verdict over all of them**, and nothing told the reader which they had |

*The evidence that the tests work is 14 mutations, each caught* — a leak reintroduced in every
place one has ever occurred: the capabilities line, the error keys, the candidate line, a new
key in `collect()`, a new field on `Verdict`, a new fact in `digest.stats`, the hardcoded
dimension list, a check dropped from the dimension loop, the label column, the label in the
JSON, and both booleans made to stop changing the output. **Two of the fourteen did not fail
the first time**, which is the part worth keeping — see the two new entries under "ways to get
a false answer". 10 tests, 105 total.

*What this does **not** cover, stated because the heading above it has been false every time
it was checkable:* the walk reaches `collect()`'s top level and `session`'s facts. It does not
reach the payload *inside* a check — `proofs`, `groups`, `events`, `recurring` — which is
where the specifics the skill is required to quote actually live. That is item 21, and it was
found by this mechanism rather than by reading this list.

**21. A check's specifics reach the person who has to quote them** — `specifics`
(2026-08-12). The skill is *required* to report an `evidenced` finding "with the specifics
quoted", and the build-this prompt fires only on "the actual command run 15 times, the actual
file dumped and later grepped". Those specifics existed — `partial_use.proofs`,
`producers.groups`, `spill.events` — and the skill was handed one summary line per check and
told, three sections earlier, never to read the raw JSON, because the excerpt rides along with
it. A rule and its evidence on opposite sides of a wall the tool built on purpose.

*Why this was the worst of the four rather than the smallest.* Every other leak cost a reader
a fact. This one left three ways out and all of them are bad: re-run without `--emit` and drag
the excerpt into the session under diagnosis, report vaguely and break the rule, or fill the
gap with plausible specifics — which is precisely the fabrication `verdict.py` exists to catch
on the judge's side, where nothing catches it on the skill's.

*The shape follows item 20's split.* A check returns `specifics`: rows a person can quote,
built by the check because only the check knows its payload. The registry caps them and states
the cut; `--text` prints them under the line they belong to, **only when the check fired**.
No new file: a second artifact is a second thing to forget, and the measurement said this one
travels with the summary for free.

*Measured before it shipped, over the whole corpus — 300 transcript files, 63 of them sessions
with both a response and a human turn* (235 hold no assistant response at all, which is worth
knowing before anyone sizes a sweep by file count again):

| measurement | result |
|---|---|
| chars added to `--text` | median **167**, p95 1,207, max **1,750** (~440 tokens worst case) |
| sessions gaining any row | 44 of 63 (70%) |
| `dumps` fired / rows cut by the cap | 36 / 20 — the cap is load-bearing, and every cut is stated |
| `partial_use` fired / cut | 21 / 4 |
| `producers`, `spill` fired | 1 each, at 2 and 1 rows — the rare, proof-grade findings |

*One thing this item was filed on turned out to be false, and the correction matters more than
the item.* It said the payloads are unbounded and `dumps` "can carry every large call". They
are not: `detect.dumps` takes `top=5`, `specification` slices `[:5]`, `rereads` and
`cli_probes` likewise — **the detectors were already capped upstream and nobody had said so.**
Only `producers`, `spill` and `partial_use` return uncapped lists, and their measured maxima
are 2, 1 and 6. So `SPECIFIC_ROWS = 3` is not protection against an unbounded payload; it is a
choice to show the reader enough to quote and no more, and it is defensible only because the
cut is printed. Written down because the worry that justified the measurement was wrong, and
the measurement is what says so.

*The invariant is keyed on the tier, not on a list of names.* Every `proof` or `evidenced`
check that fires must yield rows, tested through a fixture per check — and the one exception
proves the rule rather than escaping it: `sycophancy` is `proof` tier and its rows deliberately
carry **no** candidate text, saying instead where the judge's copy is and that a candidate is
not a finding. A pre-pass built to over-select must not become a report full of findings nobody
ruled on.

*And then the rows were read, which is the part that paid.* The first real session rendered
with them showed `partial` — the `proof` tier, the finding the report **leads with** — citing
`git commit -F - <<'EOF' hedge the judge's 1s…` as evidence that `SKILL.md` had been read whole
and later only searched. A commit message that names a file is not a search of it. The Bash
branch of `partial_use` matched the **whole command**, so any mention of the basename beside
any `grep` anywhere counted: **6 of 48 proofs on the corpus were a filename appearing in
data.** Item 13 built `_shell_code` for exactly this failure and applied it to `cli_probes`
alone; the identical hole sat in the tier whose whole claim is that it carries its own ground
truth. Fixed by matching shell code, which drops 48 proofs to 42 and keeps every real one, and
the direction is the safe one — a missed proof costs recall, a false proof costs the tier its
word. 1 test, mutation-checked.

*Note what found it.* Not a walk, not the roadmap, and not a review of `detect.py`: **the
evidence was printed next to the number and a person read it.** The count "2 dumps later
proved to need only a slice" was unfalsifiable at a glance and had been shipping for weeks;
one of the two rows underneath it was self-evidently not a proof. That is the strongest
argument for item 21 that exists, and it was not the argument the item was filed on — showing
your evidence is a *correctness* mechanism, not only a reporting nicety, because a number
nobody can check is a number nobody checks.

8 mutations, each watched to fail — 2 only after being corrected, and both corrections are
recorded under "ways to get a false answer". The `None` case was found by the tests rather than
by review: `str(None)` is `"None"`, so a `None` row printed as a line of evidence reading
*None* under a finding. 7 tests, 112 total.

**22. `SKILL.md`'s rules walked against the data that has to satisfy them** — the pass by
hand, then the mechanism, closing kind 4 as far as a test can reach.

*The pass, and what it found.* Rule by rule, asking what datum each needs and whether it
arrives in the artifact the skill is told to read. One defect, and it is item 21 one tier
down. `SKILL.md`'s caveats section says of the compaction seams: "`depth_before`/`depth_after`
say how much context was dropped. **Those numbers are for the user**". Step 1 tells the skill
to read the `--emit` summary and forbids it the raw JSON — and `compaction` returned **no
`specifics` at all**, while its `line` carried the trigger and `pre_tokens` inside the warning
prose and neither depth. Computed on every compacted session since item 10, printed nowhere a
person reads. `compaction` now emits one row per seam with all four numbers, and a seam whose
other side has no response prints "not measured" rather than a zero, because
`detect.compaction` chose `None` there deliberately and a zero would read as "the context
dropped to nothing".

Three rules were checked and found **already satisfied**, which is worth recording because a
pass that only reports finds looks like a pass that only looked at finds: the evidence-tier
table has a row for every tier the registry declares; all six `verdict.ITEMS` are named in the
prose; and `TEXT_OMITS`'s unverified claim that "the `continuity` check's line states
`dropped_bytes` with its magnitude" is **true** — it renders as MB, which is the datum arriving
in the unit a person reads.

*The mechanism, in six walks.* Every identifier-shaped token the skill names in backticks
must resolve to a declared path in a real `collect()` output, or to a **validated** `Verdict`,
or be declared not-data with a reason; every number the skill hands the *user* must appear in
the rendered block a person reads; every literal its two action tables key on — `quotes: NOT
CHECKED`, `RETRY HINT`, the weak hedge — must be a string `verdict.render` really emits, since
a reworded line leaves an instruction that reads as sound and matches nothing; the tier table
must cover every tier a check can declare; every scored item must be named; and every `--flag`
must be one the shipping parser accepts, which is why `parser()` is now a function rather than
a local of `main`. The fixture is the
interesting part: four of the numbers live in `checks.compaction.seams[]`, **empty in a clean
session**, so the walk runs on a merged output built from a session per check — item 21's
"name the state in which the wrong behaviour would be visible" applied to a walk's input
rather than to a control.

*Two design decisions that were forced, and both are recorded as traps in `ROADMAP.md`.* The
tokeniser strips fenced blocks and forbids a newline inside a match, because `` `[^`]+` `` over
the whole file pairs one fence with the next and returns **zero** tokens — the first run of
this walk reported a clean sweep of nothing. And resolution is by *declared path*, never by
bare leaf name: `max` in `SKILL.md` is a reasoning-effort setting and matched
`checks.batching.max`, so a leaf-name walk would have passed for a reason unrelated to the
claim. The reachability half can only be a substring search inside the owning check's own
block, since a `line` is a string the check composed and item 19's flip-the-value probe cannot
reach it.

11 mutations, each watched to fail — 2 only after the harness was corrected, and both
corrections are new entries under "ways to get a false answer". One was a false **green**:
`--against` → `--compare` is length-preserving, so Python reused a `.pyc` whose recorded source
size matched and whose mtime differed by under a second, and a correct test ran against the
unmutated parser. The other was a false **OK**: `"specifics": [] or [...]` changed the file and
changed nothing about the value, so the "did the mutation change anything?" guard passed. The
guard is now "confirm the mutation changed the shipping *output*". 8 tests, 123 total.

*One gap was found in the mechanism by the mechanism's own rule.* `SKILL_VERDICT` — the
declaration of what the skill names from the judge's reply — was written, used to satisfy the
classification walk, and **resolved against nothing**: a declaration that silenced a test while
checking no data, which is precisely the `TEXT_OMITS` failure the same section warns about,
reproduced inside item 22. It now resolves against a validated `Verdict`, because the skill
reads what survived `--verdict` rather than what the judge sent.

---

## How items 19 and 21 changed what this project looks for

Kept because it is the reasoning behind the four-kind taxonomy in `ROADMAP.md`, which is a
summary of it. Moved here when the roadmap was split: this is an account of how two items
turned out, and the roadmap needs only the rule they produced.

**What item 19 established, now that it has been built.** It was filed as the first item that
fixes nothing — a mechanism to stop a seam leaking a fourth time, where every previous item
was a defect found by running the tool. That framing was wrong in the most useful direction:
the mechanism found **four** leaks within an hour of existing, none of them a check, and
pointed at a fifth (item 21). A walk that enumerates a producer is not only a guard against
the next leak; it is a search over the ones already there, and this list had no other way to
run that search. The three notes that failed were not failures of discipline — they were
attempts to hold a list in a head that nobody re-reads at the moment it matters.

This section previously read "no defect is outstanding", and that clause is gone, because it
has been false every time it was checkable. It was written in `dda7bbe` while `rereads` was
miscounting 71% of its findings, again in `ff26380` while item 16 sat in the code that same
commit had just shipped, and it would have been false again on 2026-08-12 with four leaks in
the tree. The claim this heading can support is "nothing *found*", never "nothing there" —
the first is a statement about the search and the second is a statement about the code.

The reason it fails in this specific direction is worth keeping: **this is the one list that
audits the audit tool, and it enumerates the checks rather than the pipeline around them.**
The defects now sort into three kinds, and the list only ever enumerated the first:

1. **A check computed the wrong number** — items 4, 12, 15. What the registry describes.
2. **Every check was right and the *excerpt* was empty** — item 16. Nothing verifies that
   `collect`'s output is fit to hand a judge except `collect` itself.
3. **Everything was right and the *presentation* was wrong** — items 16's `_text` half and
   17/18. A correct number, framed with more confidence than it can carry.

Each kind was found once and each was invisible to the list at the time. That is three
different seams downstream of the checks, and the pattern said the next one would also be
downstream — so when this heading next reads "nothing", the question to ask is not "is any
check wrong" but "does anything verify what happens to a check's output after it is right".

**The prediction held, and a fourth kind arrived with it.** Item 19's walks were built for
kind 3 and found four instances of it in an hour. Item 21 was the fourth kind and fits none of
the three:

4. **Everything was right, was presented correctly, and the *consumer* was never given it** —
   item 21, with `capabilities` the same shape caught an hour earlier. The number is computed,
   the line is printed, and the rule that needs it lives in a document on the other side of a
   wall the tool built on purpose. No renderer is wrong; there is no renderer at all.

Kind 4 is the one a reading never finds, because the defect is in no file you would open — it
is *between* `SKILL.md`'s requirements and `collect()`'s output, and only enumerating one
against the other shows it. **The generalisation is to ask, of every rule the skill is given,
which artifact carries the evidence that rule demands.** Asked twice so far, and a defect both
times, which is why item 22 is to ask it of all of them and then leave a test behind that
keeps asking.

**The four kinds are one shape, and naming it is what this list is for.** In every case a
number was correct and the *distance between where it was computed and where it was needed*
was never checked by anything. Kind 1 is a wrong number and is the only kind the checks
themselves can catch; kinds 2, 3 and 4 are the same defect at increasing distance — excerpt,
renderer, consumer. So the useful question when this heading next reads "nothing" is not "is
any check wrong", and no longer only "does anything verify what happens to a check's output
after it is right", but **"how far does a number travel before someone acts on it, and what
checks each hop?"** Three of those hops now have a walk. The last one ends in prose that a
model reads, and that is where the mechanism runs out.

---

## Item 10 as it was filed, while it was still blocked

Kept verbatim because the reasoning is what survived, and one line of it turned out to be
false in a way worth leaving visible. Moved out of the roadmap's "blocked" section when the
file was split: the item shipped, and 55 lines of how it looked beforehand is history.

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

## The API question, as it was settled

Moved out of `ROADMAP.md` when items 23 and 24 were filed: it is a decision that stopped
being live, and only one sentence of it still bears on open work.

There is **no SDK, no framework, no API client** anywhere in this plugin — no `anthropic`,
no POML, no PydanticAI, no HTTP. Dependencies are stdlib only and the LLM is reached through
Claude Code's own subagent mechanism. That is why the plugin runs only inside Claude Code,
and it is the live half: a corpus pass needs **new code** rather than a runner, which is
item 23.

Items 2 and 11 are what an SDK would have given, bought without the dependency: a schema
check after the reply, and a grounding check on the field a schema cannot reach, both in
`verdict.py`, because there is no API layer in which to pin a response format. **A
structured-output API would still not have caught item 11's failure** — a fabricated quote
is a schema-valid string, and only comparing it to the excerpt catches it.
