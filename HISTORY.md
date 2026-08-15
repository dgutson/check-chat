# History — how each finished item got that way

Every item this project has shipped, with what was measured, what the filing got wrong, and
why the fix took the shape it did — followed by the four registers that say what the project
knows and will not redo: its known limitations, the ideas measured to nothing, the ways a
corpus measurement comes back false, and how the defects have sorted. **Nothing here is
pending work**; `ROADMAP.md` holds that, and holds only that.

Read an entry when you are about to change what it decided, when a number in the code looks
arbitrary, or when you are tempted to rebuild something. Do not read this file to pick a task
— that is what the roadmap is for, and this file was split out of it precisely because 773
lines of settled history was being loaded to answer a question it does not answer.

The entries are in the order they were finished, which is not their numeric order: an item's
number is when it was *filed*. Grep `**<n>.` to find one.

---

## Index of shipped items — one line each, the detail is below

What has already been settled, so nothing here gets rebuilt or re-argued. Each row says what
the item *decided*; the entry says what it measured and what the filing got wrong.

| # | shipped | what it settled |
|---|---|---|
| 1 | 08-09 | Published to `github.com/dgutson/check-chat`, MIT, verified from a fresh clone |
| 2 | 08-09 | `--verdict` parses and validates the judge's reply instead of believing it |
| 11 | 08-09 | The judge's quotes are checked against the excerpt it was shown |
| 3 | 08-10 | Truncation ships as a `caveat`; the compaction *heuristic* was cut for having 0 observations |
| 4a | 08-10 | Trap 5 — an interruption marker is not a turn the user typed |
| 5 | 08-10 | `pyproject.toml`; the project has its own virtualenv |
| 4 | 08-10 | `cli_probes` fires machine-wide: the comparison population was wrong, not the detector |
| 12 | 08-10 | Every check audited for item 4's failure, and the rule that decides scope |
| 13 | 08-11 | Prose about a command is not a command that ran — `_shell_code` |
| 14 | 08-11 | The tool-call ledger, and a `wasted_effort` question the judge may answer with a quote — item 8's proposal, fenced by measurement |
| 15 | 08-11 | `rereads` stops counting different slices of one file as waste (71% of its findings) |
| 10 | 08-11 | Compaction awareness, by producing the transcript the item was "blocked" on |
| 16 | 08-12 | A session with no human turn fails instead of judging a blank page |
| 17 | 08-12 | Blinding measured (no effect at 6–26 turns); a judge `1` is not reproducible |
| 18 | 08-12 | A judge `1` renders as the single read it is — `tier`, `weak` |
| 19+20 | 08-12 | The renderer seam is walked, not remembered; the label is declared in the registry |
| 21 | 08-12 | A check's `specifics` reach the person required to quote them — and printing evidence found a `proof`-tier false positive |
| 22 | 08-13 | `SKILL.md`'s rules are walked against the data that must satisfy them; the compaction seam depths were reaching nobody |
| 23 | 08-13 | `--sweep`: the checks over the whole corpus, which is 69 sessions and not 319 files — and whose first find was its own conflated denominator |
| 24 | 08-14 | The aggregate is *declared* sendable, not accidentally so — and the ask for one exists, which is the half with no code in it |
| 25 | 08-14 | The format assumptions are named and four are probed — and the census found a field the code said the harness does not write |
| 27 | 08-14 | `--calibrate`: one file a volunteer marks, one merge reads a stack — and a `proof` row that never named its file |
| R-001 | 08-14 | Trap 7 — a background agent finishing is not a request the user typed; 11 phantom turns in one session, and `effort` was reading them too |
| R-002 | 08-14 | `--census`: the record-type claims are produced by shipping code, and a rename is legible as a pair — an undeclared type beside a declaration nothing backs |

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

*What it did not close, moved here from `ROADMAP.md` when item 24 filled the budget.* The
walks check that a field the skill names exists, and that a number it hands the user is
printed where a person reads. They cannot check that a rule's *meaning* is satisfied —
"quote the caveat's `warnings`" is checkable, "report only what fired" is not — and the hop
past `--text`, the report a model composes, has no mechanism and is not getting one. **The
pass by hand is still the only thing that finds a kind 4**; item 22's mechanism only stops
the ones it already found from returning. It found one on its third asking, having found one
on each of the first two. The standing half of this is in `ROADMAP.md`'s renderer-seam
limitation, which is where a session picking work would look for it.

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

---

**23. `--sweep` — the corpus pass, and the first measurement it made was of itself**
(2026-08-13). `checkchat --sweep` runs the shipping checks over every session transcript on
the machine and prints one aggregate: per check, how often it fired, and a generic
distribution of every numeric field it happens to carry. `checkchat/sweep.py`, 5 tests,
128 total.

*What it is for.* The dozen entries under "Measuring against the corpus" in `ROADMAP.md` are
the bill for measuring this corpus by hand-rolled `find | xargs grep`, and the recurring fix
in that list is **import the function**. So the module holds no per-check knowledge at all:
it walks whatever `checks.run` returns, and a check registered tomorrow is summarised with no
edit to it. That is now an invariant with a control — a check registered inside a test appears
in the aggregate, and hardcoding a subset fails it.

*The corpus is much smaller than every previous number said, and the difference is not
rounding.* 319 `.jsonl` files exist under `~/.claude/projects`; the tool sees **255**, and
of those **72 have an assistant response at all**, 71 are distinct histories, and **69 have a
human turn** and are therefore sessions `collect()` would report on. The two gaps:

| gap | count | what it is |
|---|---|---|
| files → session logs | 64 | subagent logs, one directory deeper: `<session-id>/subagents/agent-*.jsonl` |
| session logs → with responses | 183 | opened, a prompt queued or attached, never answered — `queue-operation`/`attachment`/`user` records and nothing else |

Both were invisible before. The 64 were excluded correctly by `all_transcripts()`'s
`*/*.jsonl` glob and excluded *by accident of its depth* — counting a subagent's tool calls
as another session would let one session corroborate itself, which is the fork artifact by a
new route. The docstring now says so, per item 12's rule. Earlier corpus figures in this file
that count "transcripts" or "files" are counting the 255 or the 300; **69 is the number that
means sessions**, and it is small, which strengthens item 9 rather than weakening it.

*The defect it shipped with, for exactly one run, and it was this module's own rule.*
`forks_collapsed` was `len(paths) - len(families)` and reported **184 forks collapsed** where
**one** file is a fork. `collapse_forks` drops a session with no steps *and* collapses a
family, so the number was measuring two jobs at once — in the module whose header says a
denominator must not narrow silently. "A corpus is mostly forks" is a believable sentence,
which is why nothing about the output looked wrong; what caught it was checking a surprising
number instead of recording it. Both refusals are now counted before the collapse and printed.

*The numbers, and three of them corroborate figures reached another way.* `cli_probes` fires
on **8** sessions — the same 8 as the per-hand machine-wide measurement in item 4, from a
different denominator. `grounding.depth_tokens` peaks at **681,994**, against the "deepest
session 682k" recorded when compaction was cut. `continuity.dropped_bytes` is 0 across all
69. An independent route to a number already believed is the cheapest evidence a sweep can
produce, and it is why these three are named.

What is new, and what item 9 has been waiting for — base rates on the tiers that claim
ground truth:

| check | tier | fires |
|---|---|---|
| `sycophancy` | proof | 40/69 = 58% |
| `partial_use` | proof | 27/69 = 39% |
| `specification` | evidenced | 3/69 = 4% |
| `rereads` | evidenced | 2/69 = 3% |
| `producers`, `spill` | evidenced | 1/69 = 1% each |

`sycophancy` at 58% is a **candidate count, not a finding** — the check ranks challenges for
the judge and fires when it has any, which is why the judge exists. `partial_use` at 39% is
the one to look at: a `proof` tier firing in two sessions of five is close to the roadmap's
own line about a detector that fires in most sessions being a ranking rather than an alarm,
and item 21 already found one false positive in it. Not acted on here — recorded, because a
threshold moved on the strength of one user's corpus is what item 9 forbids.

*One parameter turns out to be binding, not generous.* `sessions_compared` is **12 in all 69
sessions** — `--siblings 12` saturates every time, so cross-session recall is bounded by the
flag and not by the corpus, exactly as its help text claims and nothing had checked.

*Costs and how it stays honest.* 4.7s for 255 files, because `_Memo` injects a cached loader
and prefilter into `discover.siblings()` — the naive form calls the same function and reparses
the sibling population per session, which is 24 GB of byte scanning and ~3,800 parses for a
question needing 255 of each. Injecting into the shipping function rather than modelling it
is the whole point; `collapse_forks` was extracted from `siblings()` for the same reason.

*Nine mutations, each watched to fail, and one of them was a false green.* The renderer walk
asserted `str(value) in block` and **passed with `p90` deleted from the renderer outright** —
a block of small integers supplies a matching digit for free, so the assertion was checking
that the block contains a number. Item 20's containment lesson, reproduced in the test
written to honour item 19. Every stat is now pinned to its own label by regex.

---

**24. The aggregate is *declared* sendable, and the ask for one exists** (2026-08-14).
`sweep.sendable_strings()`, two tests, a `README.md` section and
`.github/ISSUE_TEMPLATE/base-rate.md`. 130 tests total. The half with no code in it is the
half that matters: item 9 has been blocked for a week on a number from a corpus nobody here
can see, and until 08-14 there was nowhere for anyone to send one.

*The item's own filing was wrong about the thing it was filing, and that is worth keeping.*
It said the aggregate carries "absolute paths, filenames, `specifics` rows quoting the
conversation, `proof` command text and the excerpt itself", and specified a redaction pass.
All of that is true of `collect()`'s output and false of the sweep's, because item 24 was
written before item 23 existed and described the producer it imagined. Audited leaf by leaf
first: **42 string leaves, all 42 a registry constant** — a check name, label, dimension or
tier — and every other leaf a number. There was no redaction to write, only a contract to
declare, and the item shrank to a fifth of its filed size on contact with the code.

*What was actually missing was a direction.* The safety was a property of two filters:
`_numeric` admits only `int`/`float`, and `meta` copies three registry fields. Nothing failed
if either were widened. This is the ninth instance of the seam this project has found eight
times, inverted — `cli.TEXT_OMITS` fails when a field reaches **nobody**, `sendable_strings()`
fails when a field reaches **everybody** — and the only one where a miss is a harm rather than
a bug, because the file's purpose is to be pasted into a public issue by someone who did not
write it. The vocabulary is *derived* from the registry rather than listed, so a check
registered tomorrow widens it by exactly its own four constants.

*Two of the first seven mutations passed, and both were about the fixture rather than the
test.* One copied `summary` into `meta` to simulate a leak — but `checks.run` pops `summary`
into `line`, so the mutation shipped a `None` and the walk correctly ignored it: a mutation
that does not change the output in the direction it claims is not a test failing to catch it.
The other named a numeric field after the file it read, and **the vocabulary walk stayed
green** — because `_corpus` writes calls with no tool *results*, so every payload is 0 chars,
no check that quotes a path fires, and a default-deny walk over an aggregate with nothing in
it to deny is satisfied by a producer with no filters at all. This is item 21's "negative
control on an input that cannot show the effect", arriving inverted, in the test written to
close the last hop. Fixed by sweeping a marked session alongside; all seven then failed.

*The second test is the one that will still mean something in a year.* It plants a filename
in a session, asserts the *checks* quote it back — naming `dumps` and `partial_use`, the two
whose payload carries a path — and only then asserts it is absent from the aggregate. The
premise is asserted first because it is the half that rots: if those checks ever stop
carrying the path, a control without it keeps passing while measuring nothing.

*What the ask says, and the one thing it refuses to claim.* Numbers stay allowed without
qualification — a count *about* a session is not content *from* it — but the README and the
template both say a one-session sweep is **contentless, not anonymous**: every distribution
in it is that session's own value, so `n 1 min 4 max 4` is that session's 4. The checklist
asks for more than one session and asks what kind of work the corpus is, which is the part
the numbers cannot carry.

*The residual, moved here from `ROADMAP.md` when item 27 filled the budget.* The walk is
default-deny over string *values*, against a vocabulary derived from the registry. **Keys get
only `isidentifier()`** — which every path, command and sentence a conversation can supply
fails, and which an identifier-shaped filename would pass. What covers the rest is the
planted-filename control, and a control covers exactly the content it plants.

*The corpus grew while this was written* — 69 sessions on 08-13, **71** on 08-14, because the
sessions building this tool are themselves transcripts under `~/.claude/projects`. Any figure
in this file is a reading, not a constant.

---

**25. The assumptions about somebody else's format, named — and the census found one of them
already wrong** (2026-08-14). `checkchat/formats.py` declares all seven, `checks.formats`
reports a contradicted one as a `caveat`, `transcript.load` keeps a record-type census, and
`Compaction` gained the three fields the record was carrying unread. 9 tests, 139 total.

*Why it was filed.* This tool reads another program's output and is **published**: it runs on
machines whose Claude Code version the author has never seen. Every one of these assumptions
fails as a **confident zero**, the shape this project calls its most expensive — `cli_probes`
returned one for its whole shipped life and was twice queued for deletion while being right
every time. Nothing looks wrong when a renamed record is skipped: every count stays
arithmetically correct and describes a fraction of the conversation.

*The census, which is the part that paid.* 258 transcripts, **16 record types**, and the
parser branches on three of them — `assistant`, `user`, `system/compact_boundary`. The other
thirteen were skipped without a trace and without a note: `attachment` (2,289),
`last-prompt` (1,432), `mode` (1,365), `permission-mode` (1,359), `ai-title` (1,287),
`queue-operation` (484), `file-history-delta` (461), `file-history-snapshot` (408),
`system/turn_duration` (328), `system/away_summary` (91), `agent-name` (29),
`system/local_command` (19), `system/informational` (4). Each is now declared with its
reason, and the ones that could plausibly hold a human turn were opened rather than inferred
from their names. **`queue-operation` was the one worth checking**: of 62 enqueued inside
answered sessions, 37 arrive again as a `user` record when they are sent, 22 are machine
`<task-notification>` tags, 2 are slash commands `clean()` strips anyway, and **1 was a real
prompt that was never sent** — so ignoring the type is right and the reason is not the one a
guess would have given.

*The find: `compactMetadata.postTokens` is in the record, and three documents said it is not.*
`Compaction`'s docstring, `ROADMAP.md`'s "Reading the producer is not reading the product"
and this file all recorded that the field is set in the harness's source and assigned after
serialisation, so the written record lacks it. It is in **all four** `compact_boundary`
records on this machine — **including both in `tests/fixtures/compacted.jsonl`, the file the
claim was measured against**. The claim was reached by reading the producer and never opening
the product, inside the note that says to open the product, and it sat there for two days
while a real number went unread. The lesson was right; the example was an instance of the
error it warns about.

*And it is not the number it looks like.* `post_tokens` is **2,455** where the measured
`depth_after` across the same seam is **26,146**, because the next request re-sends the system
prompt, the tools and the project files behind the summary. Substituting one for the other
would manufacture a loss out of two true numbers, so they are reported as two clauses of one
row and a mutation that ORs them together fails a test. The harness's own arithmetic is
internally consistent and confirms which quantity is which: 100,817 − 2,455 = 98,362, and
+ (26,975 − 2,394) = 122,943, exactly the `cumulativeDroppedTokens` of each seam.

*A probe was written, measured and deleted before it shipped.* Cross-checking the
declined-call wording against `toolUseResult.interrupted` looked like the obvious structural
counter-signal for the one assumption that is pure English. `interrupted` is present in 2,316
results and **true in 0 of 4,841**, while the wording matches 32. A precondition that never
holds is a detector that cannot fire, so `declined_wording` is declared unprobeable with that
measurement as the reason — which is what the three unprobed entries are *for*: a reader
deciding whether to trust a zero can see which assumptions were confirmed against the
transcript in front of them and which are taken on faith.

*The trap the whole module sits inside.* "The format is absent" and "the thing never
happened" are one observation from inside a count, so every probe requires local evidence
that the shape should be there — a `compact_boundary` record with empty metadata, a spill
file read back with no notice that could have produced it. An orphan `isCompactSummary`
legitimately carries no trigger and no token count, and a probe that reported *that* as drift
would fire on a shape the parser handles on purpose. Both states are pinned by one test.

*Its own arrival broke a hardcoded enumeration.* `SKILL.md`'s caveats section said "today
there are two" and named `continuity` and `compaction`; registering a third caveat left the
reporter with no instructions for it and nothing noticed — the renderer's hardcoded dimension
list, one hop over, in prose. A test now fails when a `caveat`-tier check is registered that
the section does not name. Only that tier, and deliberately: every other tier is reported
generically from the evidence table, while a caveat changes what the reporter *does*.

*It fires 0/74, which is the designed answer.* Each probe asks whether *this* harness still
writes the shape the code reads, and this machine's does. Exactly one real transcript trips
one — two responses carrying no token count — and it is a fork with no human turn, so
`collect()` refuses it and the sweep never counts it. The controls are otherwise synthetic by
construction, and that is **not** item 9's problem: those checks are quiet because the
population is one expert's and no fixture repairs that, while this one is quiet because the
condition is genuinely absent here and a machine where it is not is the entire point.

*Fourteen mutations, two of which were the mutation's fault.* Building an `Assumption` with
only a `key` will not construct, so it reported `1 error` at collection — which reads like a
pass of the harness and a failure of the code and is the reverse. And "substituting the
after-figure for the measured depth" was written as an extra unread key: it changed the file,
changed nothing about the output, and reported a false OK. Both are already in `ROADMAP.md`'s
lab notes, which is how they were recognised on sight rather than believed.

*The roadmap budget is now binding on every item.* This entry left it at 416/420 lines and
33,948/34,000 bytes, and two blocks moved here to get there. That is the mechanism working,
and the next item will have to move one too.

*A note moved here from `ROADMAP.md`'s Known Limitations when item 27 pushed that file over
its budget, because this is where its explanation already was.* **`formats` fires 0/75, which
is the designed answer and not a measurement of nothing.** Its controls are synthetic by
construction, and that is not item 9's problem: this check is quiet because the condition is
absent *here*, not because it has never been shown to fire.

**27. `--calibrate` — the one file a volunteer marks, and the merge that reads a stack of
them** (2026-08-14). `checkchat/calibrate.py`, an `observe` seam in `sweep.run`, two new
registry fields, and a `PROOF_CMD_WIDTH` window in `detect`. 13 tests, 152 total; 14 of 14
mutations caught.

*What it is for.* `--sweep` carries item 9's first half — how often each check fires on
somebody else's corpus. The second half is in no transcript: **whether the finding was
right**. `partial_use` fires at 37% on a `proof` tier and item 21 found 6 of 48 of its proofs
bogus, so the tier's honesty is unknown and is reaching users. Only someone who was in the
conversation can settle it, and the whole cost of settling it is their attention — the
colleagues who agreed to help are short of time, which is the constraint every decision below
is shaped by.

*The protocol is inverted, and that is the design.* Marking forty boxes in a text editor is
fiddly enough that the file comes back empty, so a blank row means **the tool was right** and
the volunteer marks only the rows it got wrong — typically five or six characters for the
whole file. That is worth one honest caveat, and it is stated in the file, in the module and
in `render_merge` rather than discovered later: **the rate this produces is biased low**,
because a row skimmed and a row confirmed leave the same mark. `read_all` is what stops it
being meaningless — a blank counts as `ok` only in a file whose reader said they read every
row, and an unmarked file's blanks score as `unjudged` instead of quietly crediting the
checks with them. Three verdicts, never more: `ok`, `bogus`, and a `?` that exists because a
forced binary on a half-remembered row is a coin flip wearing a number's clothes.

*The find: a proof row that never names the file it is a proof about.* `partial_use` composed
its evidence as `cmd.strip()[:70]`, and on this corpus **22 of 37** command-proof rows cut
before the filename — one showed a `grep` of `cmake.py` under a finding about `profile.py`,
which reads as a false positive and is not one. `_proof_window` now takes the 70 characters
*around* the basename instead of the first 70, and all 37 name their file. It surfaced only
because somebody outside the project was about to be asked to rule on these rows, where a
wrong `bogus` corrupts the measurement harder than a missing row does — but the same string
is what `--text` prints, so the report has been showing a proof that proves nothing for as
long as the row has existed. Same family as this file's own "a truncated echo of a value is
not the value", one layer out: there the cut broke a re-check, here it broke a person's.

*The width was measured, not chosen.* Over 300 evidence rows: p50 123, p90 175, p99 233, max
319. `checks.SPECIFIC_WIDTH`'s 160 truncates 19% of all rows and **57% of the rows
calibration selects**, because selection favours the checks whose evidence is longest. A
proof cut mid-argument comes back `?`, so the cap that protects a summary is the cap that
empties a calibration: `CALIBRATE_WIDTH = 240` leaves 1% cut and the file says how many. The
row *count* stays at `SPECIFIC_ROWS`, deliberately — width decides whether a finding can be
judged, count decides which findings are sampled, and a calibration that sampled differently
from the report would be measuring a report nobody reads.

*Selection is round-robin, never first-N.* `partial_use` at 37% would eat the whole budget
and the rare checks would come back with nothing — a calibration of one check wearing the
costume of a calibration of six, and it fails with the file looking full. Newest first within
each check, which is the same direction the recall-decay risk points: a uniform sample of two
years of sessions is an unbiased sample of things nobody remembers.

*Two things a check now declares, for the reason it declares its label.* `discloses` says what
a row of its evidence can contain, in the words of someone who has not read the code, and the
file's "what is in this file" paragraph is composed from the checks actually present — so a
check added tomorrow cannot ship its evidence to another person's screen under a paragraph
that does not mention it. `unjudgeable` says why a check's specifics are *pointers* rather
than findings; `sycophancy` is the one, its rows point at candidates for the judge, and a
tier-only walk would have harvested verdicts on a question the tool never asked. Both reasons
used to live in comments inside the check body, where no consumer could read them.

*The seam, and the direction it is guarded in.* `sweep.run` gained `observe(session,
results)`, because `--calibrate` needs the same population, the same two refusals and the same
fork collapse plus the individual findings, and re-walking the corpus would be the second copy
of the population logic that module exists to prevent. The aggregate is *declared* sendable,
so the test asserts the whole structure is identical with and without an observer — a
callback that could add to it would put somebody's filename in the file that gets pasted into
public issues. The mutation that proved the test bites added `specific_chars` to `_numeric`,
which is exactly the plausible edit that would do it.

*One departure from the item as filed.* It said aggregate, then rows, then footer. The rows
come first: the aggregate needs nothing from the reader, and a screen of statistics between
the instructions and the boxes is a screen of somebody's ten minutes.

*Left open, and found by reading the tool's own output.* Three of the seven `specification`
rows on this corpus are `<task-notification>` records — machine-injected turns being counted
as requests the user typed. They are true statements about the transcript and false ones about
the person, and each one spends a slot of a volunteer's forty. Not fixed here: it is a change
to what `specification` counts as a request, and it belongs with item 9's tuning rather than
in the file that collects the evidence for it. Filed as R-001 in `ROADMAP.md`.

**R-001. A background agent finishing is not a turn — trap 7** (2026-08-14).
`transcript._STRIP` now removes a closed `<task-notification>` block, which drops the record
through the same door traps 5 and 6 use: `clean()` empties it, and `load()` only builds a
`Turn` from text that survives. One line of regex; the work was in knowing it was safe and
in finding out what else had been reading these.

*Why it hid for so long.* The interruption marker is one bracketed line and the compaction
summary is flagged `isCompactSummary`. This one has no flag, and it does not look like
machinery: it is long, it is prose, and it carries the subagent's `<result>` verbatim, so it
reads exactly like something a person pasted in. All 15 on this machine are the entire
content of their record and all 15 are closed — measured before matching on the closing tag,
because the alternative (drop any record mentioning the tag) would delete a real question
from a human quoting one. A test holds that direction: a turn with the block in the middle
keeps everything either side of it.

*It was never only `specification`.* The item was filed off three calibration rows, and the
sweep found the same phantom in a second check. `effort` calls a turn "overkill" when an
expensive setting is spent on ≤2 responses with ≤1 call — which is precisely the shape of the
model acknowledging a notification. Session `fa0e1a7d` reported 5 overkill turns and now
reports 0; `a7fd4318` went 4 to 1; the check fired in 10 sessions and now fires in 8. Nothing
predicted that: the roadmap item named one check, and the corpus named two. **When a phantom
turn is found, ask which checks are per-turn**, not which check reported it.

*What moved, on 85 sessions.* 5 changed. `specification` fired 3 → 2, `unclarified_count`
max 4 → 2, `requests` max 13 → 12. `effort` fired 10 → 8. The worst session was `fa0e1a7d`:
20 turns → 9, so **11 of its 20 turns were notifications**, and its 13 "requests" were 2.
No session lost every turn — `no_human_turn` stays at 7 — so nothing was refused that used to
be judged. In the volunteer's file, `specification` went from 7 rows to 4 with none of them
machine-injected, and the three freed slots went to `partial_use` rows about real commands.

*The assumption is declared, and its probe says what it cannot see.* `formats.task_notification`
probes for the tag surviving `clean()` — the drift where the block stops being closed the way
`_STRIP` matches it. A **rename** to `<agent-notification>` leaves no residue, so the phantom
would return in silence; that is written into `degrades` rather than left for a reader to
assume covered. Coverage is now 5 probed of 8, still 3 unprobed, and the test that pins those
counts is what noticed the new entry.

3 tests plus the probe's two-state test, 156 total; every one watched to fail first — and the
first attempt to watch them was itself the lab note about mutations that error rather than
fail, having left a bare comma in the regex.

**R-002. The record census ships, and a rename is legible as a pair** (2026-08-14).
`formats.census()` counts every record type on the machine against `HANDLED` and `IGNORED`,
`--census` runs it, and `render_census` is the renderer a person reads. Item 25's sixteen
types were measured by a script in a temp directory that no longer exists — item 23's mistake
made by the item written to end it — so the claims in `IGNORED` had become unre-runnable
assertions about another program's records. 4 tests, 160 total.

*Both directions, which is the part worth having.* `undeclared` is a type in the corpus no
declaration covers; `unseen` is a declaration the corpus no longer backs. Only the pair says
"rename": a harness renaming `attachment` to `prompt-attachment` produces one of each, and
either alone reads as something else entirely — a record type having been added, or one
having fallen out of use. The first direction is `_unknown_records` at corpus scale; the
second did not exist before and is the half a version bump actually trips.

*It reproduces item 25.* Same 16 types, same 3 handled and 13 ignored, nothing undeclared and
nothing unseen — on 456 files where that census walked 258, with every count grown in
proportion and `agent-name` still 29 records in exactly 1 file. The counts come from
`transcript.load`'s own `record_types` rather than from a second reader, so what is reported
is what the shipping parser saw, truncation included: measure the shipping function, and here
the function is the one whose silence the census exists to break.

*Default-deny on an output whose interesting values are unknown by construction.* The census
is written to be pasted into an issue by somebody running a Claude Code nobody here has seen,
and its findings are *undeclared* type names — the one thing an allow-list cannot contain. So
the guard is on their shape (`[a-z][a-z0-9_/-]{0,39}`), what fails it is dropped and counted
rather than passed through, and the count is printed. The vocabulary walk that pins this is
item 24's, with the field names derived off the structure instead of listed, and a planted
path-shaped type name is the control.

*Exit code, so an upgrade check can be a line in a script.* 0 when the declarations and the
corpus agree, 1 when they do not. Watched to fail: pinning it to 0 leaves the clean-corpus
assertion green, which is why the test builds both states.

*What it does not reproduce, stated rather than implied.* Item 25's `queue-operation`
breakdown — 62 enqueued, 37 re-arriving as `user` records, 22 machine tags, 2 slash commands,
1 never sent — is still a one-off measurement. It is a claim about records the parser
deliberately skips, so it cannot go through `record_types` at all and would need a second
reader of the raw lines. Left out on purpose; the type-level census is what makes a rename
noticeable, which is the reason the item was filed.

---

## How the defects have sorted, because it is what predicts the next one

Four kinds, and this list once enumerated only the first. The reasoning is this file's "How
items 19 and 21 changed what this project looks for"; this is the summary that section says
it is.

1. **A wrong number** — 4, 12, 15. The only kind the checks themselves can catch.
2. **Every check right and the *excerpt* empty** — 16.
3. **Everything right and the *presentation* wrong** — 16, 17, 18, and four from item 19's walks.
4. **Everything right and printed, the *consumer* never given it** — 21, 22, `capabilities`.

Kinds 2–4 are one defect at increasing distance — excerpt, renderer, consumer — so the
question is **"how far does a number travel before someone acts on it, and what checks each
hop?"** All four hops have a walk; the fifth is prose. **The pass by hand has produced a find
on every asking so far**: items 23–24 found no leak and found the *walk* vacuous instead — a
default-deny test passing over a corpus with nothing in it to deny — and item 25 found a
number the harness had been writing all along that nothing read, beside a caveat enumeration
in `SKILL.md` that a new check silently made incomplete. Which is why "nothing found" has
never been a claim about the code; the entries above list the commits in which it was false as
it was being written.

---

## Known limitations — accepted and documented, not bugs to fix

- **Blinding is enforced by instruction, not by the sandbox.** `tools: []` was the intent;
  the harness grants *all* tools for an empty list. The judge is `tools: ["Read"]` and is
  told to read only what it is given. Re-test if the harness ever supports an empty grant.
- **The renderer seam has leaked eight times, and now has a mechanism.** Every one was
  computed correctly and lost on the way out; the enumeration is in the entries above, and the
  count in this bullet has twice been wrong by understating it. **The rule is: nothing a
  producer computes is rendered by default** — not only checks, and `--text` is not the only
  renderer, since a judge reply reaches a person through `verdict.render`. Item 19 mechanised
  it as a walk over the producer plus a declaration naming the renderer for anything
  deliberately unprinted; item 21 extended it to a check's payload; item 22 to `SKILL.md`'s
  prose, which is how the `compaction` seam depths turned out to be the eighth. What no walk
  reaches is the hop after that — the report a model composes — so "which renderer does a
  person read *this* data in" is asked by hand there, and always will be.
- **Every check that reads a Bash command has to mean the code, not the text — and the two
  that got it wrong were found a month apart.** `cli_probes` (item 13) and `partial_use`
  (found by item 21) both scanned the whole `command` parameter, so a commit message or an
  `echo` label counted as a command that ran or a file that was searched. Both now match
  `_shell_code`. The rest were audited when the second one turned up, and the useful part is
  **which direction each error goes**, because that is what decides whether it matters:
  `mutation_index` and `_FILTERED` over-match into data and thereby *suppress* a waste
  finding, which is the safe direction and deliberate; `_DUMPY_CMD` can mislabel *why* a
  payload was a dump but cannot invent the payload, since the size is measured from the
  result. The one left unmeasured is `producers`, which groups on the command head: three
  near-identical mentions of a command would have to appear in data to fool it. **When a
  check reads command text, say which direction its errors go.** A check that can only
  suppress needs no fix; one that can invent belongs in the `proof` tier's audit.
- **`partial_use` now misses a proof whose filename is quoted.** `grep -n foo "my file.md"`
  loses the basename with the quotes, so the dump goes unproven. Accepted knowingly as the
  price of the fix above: this is the one check whose tier claims machine-checkable ground
  truth, so recall is the thing it is allowed to lose. Unmeasured on the corpus — no
  quoted-path proof appeared in the 48 examined, but that is a small sample of one user's
  quoting habits.
- **The `SKILL.md` walk resolves by declared path, and that declaration is its soft spot.**
  Item 22's tokeniser finds what the skill names in backticks; a dict says where each one
  lives, and `SKILL_NOT_DATA` says which are not data at all. Both are silencing surfaces of
  exactly the `TEXT_OMITS` kind — an entry ends the walk's interest in a token permanently.
  Declared paths rather than bare leaf names on purpose: `max` in `SKILL.md` is a
  reasoning-effort *setting* and matches `checks.batching.max`, so a leaf-name walk would
  have resolved it against an unrelated field and passed for a reason with nothing to do with
  the claim — item 20's containment bug by a new route. The residual limit is the reachability
  half: a check's `line` is a string the check composed, so the value can only be looked for
  as a substring inside that check's own block, and a single-digit value can still be matched
  by an unrelated digit there.
- **A declared omission is a hole the mechanism cannot see into.** `cli.TEXT_OMITS` is what
  keeps the walk honest, and it is also the way to silence it: an entry there ends the test's
  interest in a key permanently. The guards are thin on purpose — the reason must be non-empty
  and must name the renderer that *does* show the data, and every excused key must still
  exist — but nothing checks that the named renderer really shows it. Two entries today,
  both pointing at a check's own line. Read new entries as changes to the contract, not as
  test maintenance.
- **A judge score of `1` is not reproducible** — now marked rather than merely known
  (item 18). Measured over 18 dispatches (item 17): the same excerpt, rubric and model
  returns `self_consistency` or `should_restart` as 0 or 1 depending on the run. Every
  observed flip was `0↔1`; none involved a 2 or a 3, and the decision table thresholds at
  ≥ 2, so **no recommendation the user acts on turns on the unstable part**. The exposure
  was the reporting, and item 18 closed it: such items carry `tier: "weak"` and render
  `[weak: one read; a re-run may score 0]`. The limitation that *remains* is the
  measurement's own boundary — a `2` is unmarked because nothing says it moves, which is
  an absence of evidence about the upper half of the scale and not a finding of stability.
  It is also still **one dispatch**; corroborating it was rejected for want of an honest
  disagreement rule, not because a single read is ideal.
- **Concurrent runs do not interfere, and nothing enforces that.** Two chats can run
  `/check-chat` at once: the only write is `--emit`'s two files into the directory the caller
  names, everything else reads `~/.claude/projects`, and both files are rewritten whole so no
  stale half survives. `SKILL.md` names that directory `checkchat-$$`, and the shell PID
  differs on *every* Bash call in this harness (measured: 3784417 then 3784490) — so
  concurrent chats cannot collide, and step 2b can reach step 1's directory only by copying
  the printed path. Both halves are properties of `$$` rather than decisions, and the failure
  is quiet: a re-typed `checkchat-$$` finds nothing, and the troubleshooting table reads the
  resulting `quotes: NOT CHECKED` as "you forgot `--against`". The default `${TMPDIR:-/tmp}`
  is world-readable on a multi-user box, leaving the blinded excerpt where another account can
  read it. Item 24 settled the same question for the *sweep* and not for this: the aggregate
  is declared contentless, the excerpt is the conversation.
- **`--calibrate`'s false-positive rate is biased low, by design.** A volunteer marks only
  the rows the tool got *wrong*, so a row skimmed and a row confirmed leave the same blank.
  That is the trade that buys a file which comes back at all, and `read_all` is the only
  thing keeping it honest — blanks count as verdicts solely in a file whose reader said they
  read every row, and an unmarked file scores as unjudged rather than crediting the checks.
  Read a low rate as an optimistic bound on precision. The **other** direction is the one to
  watch: a row a volunteer cannot check reads as bogus, which is why `partial_use`'s proof
  window was fixed before anyone was asked to rule on one.
- **The sweep's aggregate is default-deny on its string *values* and weaker on its keys** —
  keys get only `isidentifier()`, which an identifier-shaped filename would pass. A
  planted-filename control covers the rest, and covers exactly what it plants.
- **`looks_english` is an unvalidated stopword heuristic.** It only decides whether
  sycophancy candidates get *ranked*, so failing it degrades ordering, never recall.
- **`spill` depends on harness English wording** (`Output too large … saved to:`), and item 25
  made that break loudly rather than silently — `formats` reports a spill file read back with
  no notice that could have produced it. It says nothing in a session that spilled nothing.
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

**The API question is settled and is not what holds this back** — no SDK, no framework, no
HTTP, stdlib only, the LLM reached through Claude Code's own subagent mechanism. What that
costs and what items 2 and 11 bought without the dependency is in "The API question, as it was
settled" above; the live half of it is item 23's, since it is why a corpus pass needs new code
rather than a runner.

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
- **The corpus contains the session doing the measuring, and it grows between the two runs.**
  R-001's before-and-after sweeps were taken twenty minutes apart, and the aggregate showed
  `batching` moving — 49 sessions fired to 50, `responses_with_tools` median 35 to 37 — from a
  change that only ever removes turns. The whole of it was the live session: its own transcript
  is in `~/.claude/projects`, it gained a call between the runs, and that was enough to shift a
  median across 85 sessions. Nothing looked wrong; a plausible side effect on an unrelated check
  is exactly what a real bug would produce. What settled it was refusing to reason about it and
  measuring per session through `sweep.run`'s `observe` seam instead: 5 sessions changed, the
  only one whose `batching` moved had no change in its turn count, and it was this one. **Diff
  per session, not per aggregate** — an aggregate cannot tell you which member moved, and one
  moving member is the difference between a side effect and a self-portrait.
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
- **Reading the producer is not reading the product — and this entry's own example was a
  case of it.** Item 10's format was recovered from the harness binary before a compacted
  transcript existed, and this note then recorded that its construction site sets
  `compactMetadata.postTokens` while the record the harness *writes* has none, being assigned
  after serialisation. **That is false.** Item 25's census found `postTokens` in all four
  `compact_boundary` records on this machine, including both in `tests/fixtures/compacted.jsonl`
  — the file this note was written against. The claim was reached by reading the producer and
  never opening the product, inside the entry that says to open the product, and it sat in a
  docstring for two days with the field going unread. Read the producer to find out what to
  look for; read a real record to find out what is there — and when a note says a field is
  absent, that is a claim about a file somebody can open in one command.
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
- **A containment test can be satisfied by the thing it was meant to be independent of.**
  Item 20's test asserted `chk.label in row` of `--catalog` — and passed with the label column
  deleted outright, because all three labels are *substrings of their own names*: `cli` of
  `cli_probes`, `spec` of `specification`, `partial` of `partial_use`. The assertion was
  checking that a name contains its own prefix. It only surfaced because the column was
  deliberately removed to see the test fail; nothing about the green run looked wrong. When an
  assertion says "X appears in Y", ask what *else* in Y could produce that appearance —
  and prefer comparing a field to comparing a haystack, which is what fixed it.
- **A truncated echo of a value is not the value.** The first attempt to size the
  `partial_use` false positives re-ran the match against `proof`, which stores
  `cmd.strip()[:70]` — so real greps failed the re-check for want of the characters the
  display had cut, and the sweep reported **28 of 37** bad where the truth was 6 of 48.
  Nothing looked wrong: a plausible number arrived on the first run. This is "measure the
  shipping function, never a model of it" with the model being *the tool's own rendering of
  the input*, which is the easiest one to reach for and the last one to suspect.
- **A negative control on an input that cannot show the effect proves nothing.** Item 21's
  control asserted that an *unfired* check keeps its rows out of `--text`, on a two-line
  session — where the check had **no rows to print either way**, so it passed with the guard
  deleted. Rewritten against two reads of one file: one repeat, below `REREAD_MIN`, so
  `rereads` has a row and no finding, which is the only state that can tell the guard from its
  absence. Before writing a control, name the state in which the wrong behaviour would be
  *visible*, and build that. Item 24 hit it inverted: a **default-deny** walk over a corpus
  where no check fires has nothing to deny, and two mutations that leaked a filename into the
  aggregate left it green until a session with content in it was swept alongside.
- **A duplicate key in a mutated dict literal mutates nothing.** Injecting `"specifics": []`
  ahead of the real key left the real one last, so Python kept it and the test passed —
  reported as "the invariant is not enforced" when the code under test had not changed at all.
  Same family as the entry below: when a mutation does not fail, suspect the mutation before
  the test, and confirm the mutated code actually differs.
- **A length-preserving mutation can be invisible to the interpreter.** Item 22's seven
  mutations ran in well under a second, and renaming `--against` to `--compare` in the parser
  left the test **green**: Python validates a `.pyc` on the source's size and its mtime
  *truncated to the second*, and `against` → `compare` changes neither. The test was correct
  and was run against stale bytecode. It is the same shape as the two entries below — a
  mutation that did not do what it looked like — but it is not in the source at all, so
  inspecting the diff cannot find it. When mutation-testing in a loop, clear `__pycache__`
  and set `PYTHONDONTWRITEBYTECODE=1`; both, because the second alone leaves earlier runs'
  caches in place.
- **`[] or [rows]` is `[rows]`.** The same run's attempt to empty a check's `specifics` by
  prefixing `[] or` reported a false **OK** — it changed the file, so the "did the mutation
  change anything?" guard passed, and it changed nothing about the value. Third member of
  the family below, and the reason the guard is now "confirm the mutation changed the
  shipping *output*", asserted by importing the function and looking at what it returns.
- **A mutation that errors is not a mutation that failed.** Breaking `Verdict` to prove the
  field-walk catches a new field produced `1 error` at collection time, not `1 failed` —
  the injected line had a literal `\n` in it and the module would not parse, so *every* test
  in the file was skipped and the walk never ran. An error reads like a pass of the harness
  and a failure of the code; it is the reverse. Re-run it properly before believing the test
  works: of fourteen mutations here, this was one of the two that did not fail the first time,
  and the other was the containment bug above.
- **A test pinned to a line number is right about the rule and wrong about how it knows.**
  `test_a_caveat_is_reported_above_the_numbers_it_qualifies` asserted `body[1]`, and broke the
  moment the header grew a second line — a false alarm about a rule that was never violated.
  Rewritten to compare the caveat's index against the first check line's, which is the
  invariant it always meant. Prefer an assertion about order to an assertion about position.
- **A zero is a measurement of the query as much as of the corpus.** The most expensive
  one yet: `cli_probes` returned 0 across the whole corpus for its entire shipped life,
  the number was correct every time, and the detector was twice queued for deletion —
  because the comparison population was one project directory when the question spanned
  the machine. Nothing about the zero looked wrong. Before believing one, state what
  population would have to contain the signal and check that is what was searched; the
  cheap version of that question is *"if this fired, what would the fix be, and is it
  scoped the same way as my query?"* — a per-user remedy measured per-directory is the
  tell.
