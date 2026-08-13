# Roadmap

State as of 2026-08-13. Published. Written so a session with no memory of how this got here
can pick it up — **read this file, not `HISTORY.md`.**

*This file is what is not done, plus the rules that stop it being done badly.* Finished items
are one line each under "Shipped"; what they measured and what their filing got wrong is in
`HISTORY.md`, which is read when you are about to change a decision, not when you are picking
one. The split exists because finishing an item used to *lengthen* this file, so the cost of
choosing the next task grew with every task completed. A test keeps this file under its
budget; when it fails, the fix is to move an entry to `HISTORY.md`, never to write the next
one shorter than it deserves.

The plugin is **installed and working end-to-end** on this machine: `/check-chat` runs,
the deterministic pass takes ~280ms (~86ms of it before item 4 made the cross-session
comparison actually load other sessions; `--siblings 0` returns it to ~20ms), the judge
dispatches by `subagent_type`, and the report comes back. `--sweep` runs the same checks over
the whole corpus in 4.7s. 128 tests pass, in the project's **own** virtualenv
(`.venv/bin/pytest` from the repo root). Open work below is ordered by whether it blocks
someone other than the author.

Every item says how you would know it is finished. The rule the project is built on
applies to this list too: **a detector that cannot be shown to fire on real transcripts
does not ship**, and one that fires in most sessions is a ranking, not an alarm. Since
item 19 the rule extends to the tests as well: a test is not evidence until the invariant
it guards has been broken on purpose and the test has been watched to fail.

---

## Shipped — one line each, the detail is in `HISTORY.md`

What has already been settled, so nothing here gets rebuilt or re-argued. Each row says what
the item *decided*; `HISTORY.md` says what it measured and what the filing got wrong. Grep it
for `**<n>.` to find an entry.

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

---

## Now — item 24, with item 23 shipped underneath it

Item 22 closed the last hop a test can reach, and this section then said nothing unblocked
was *found*, with 6, 7 and 9 filed against "transcripts from a different user" — the one
input that cannot be manufactured. That is item 10's misfiling, reproduced. Those items
do not need transcripts: item 9 needs a base rate and a threshold, item 6 one comparison of
two scorers, item 7 a repo's own vocabulary. Those are **numbers**, and the blocker looked
permanent only because they were assumed to arrive inside the conversations holding them.
The conversations cannot travel; the measurement can. Read item 12's rule before touching
these, item 13 before trusting a corpus sweep, 14 before adding anything to the excerpt.

**Item 23 shipped 08-13 and changed the denominator of everything.** `--sweep` runs the
checks over every session transcript on the machine. The corpus is **69 sessions**, not the
"319 transcripts" this entry claimed: 64 of those files are subagent logs and 183 more have
no assistant response at all. It also found its own `forks_collapsed` measuring two things at
once, and it corroborated three numbers reached by hand. `HISTORY.md` has all of it. The
base rates are now available to whoever asks; **`partial_use` fires at 39% on a `proof`
tier**, which is the one worth a second look, and it must not be tuned here — item 9's rule.

**24. Make the sweep's aggregate *declared* safe to send, then ask for one.**
This entry was written before item 23 existed and its premise was wrong, which is worth
leaving on the record: it said the aggregate carries "absolute paths, filenames, `specifics`
rows quoting the conversation, `proof` command text and the excerpt itself". That is true of
`collect()`'s output and false of the sweep's. Audited leaf by leaf: **42 string leaves, all
42 a registry constant** — a check name, label, dimension or tier. Every other leaf is a
number. No path, no command, no prose, because `_numeric` admits only `int`/`float` and the
metadata copied is the registry's. So there is no redaction to write.

What is left is that this safety is a *property of a filter*, not a contract. Nothing fails
when someone widens `meta` or passes a string through, and that is the ninth instance of the
seam this project has found eight times, with the direction inverted: `cli.TEXT_OMITS` fails
when a field reaches **nobody**, and this must fail when a field reaches **everybody** — the
same walk over a producer's keys, default-deny instead of default-render, and the only
instance where a miss is a harm and not a bug.
- *Done when:* a string leaf that is not a registry constant fails a test, demonstrated by
  adding one and watching it fail. Numbers stay allowed — a count about a session is not
  content from it — but say so, and say that a one-session sweep is contentless rather than
  anonymous, since its distributions are that session's own values
- *Then, and it is the part with no code in it:* a README section and an issue template that
  say *run `--sweep`, paste the JSON*. Without the ask this produces nothing and item 9 stays
  where it is — that is who has to act, named as item 10's rule requires

**What item 22 did not close.** The walks check that a field the skill names exists, and that
a number it hands the user is printed where a person reads. They cannot check that a rule's
*meaning* is satisfied — "quote the caveat's `warnings`" is checkable, "report only what
fired" is not — and the hop past `--text`, the report a model composes, has no mechanism and
is not getting one. **The pass by hand is still the only thing that finds a kind 4**; item
22's mechanism only stops the ones it already found from returning. It found one on its third
asking, having found one on each of the first two.

**How the defects have sorted, because it is what predicts the next one.** Four kinds, and
this list once enumerated only the first. The reasoning is `HISTORY.md`'s "How items 19 and 21
changed what this project looks for"; this is the summary that section says it is.

1. **A wrong number** — 4, 12, 15. The only kind the checks themselves can catch.
2. **Every check right and the *excerpt* empty** — 16.
3. **Everything right and the *presentation* wrong** — 16, 17, 18, and four from item 19's walks.
4. **Everything right and printed, the *consumer* never given it** — 21, 22, `capabilities`.

Kinds 2–4 are one defect at increasing distance — excerpt, renderer, consumer — so the
question is **"how far does a number travel before someone acts on it, and what checks each
hop?"** All four hops have a walk; the fifth is prose. Kind 4 has been found three times for
three askings, and **items 23 and 24 are the fifth asking**: does a number reach a consumer
who is not on this machine. Which is why "nothing found" was never a claim about the code —
it was false in `dda7bbe` (`rereads` miscounting 71% of its findings), false in `ff26380`
(item 16 sitting in the commit that shipped it), and false again on 08-12 with four leaks in
the tree.

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
indistinguishable. Item 23 is how that comparison runs on a corpus that *does* re-ask,
without the corpus moving: ship both scorers, report both numbers and their agreement.

Audited under item 12 and its zero is *not* item 4's: a re-ask is only a re-ask within one
conversation, so one session is the right population by construction, and no re-scoping
would change the number. What blocks this is item 9 — the wrong user, not the wrong query.
Same verdict for item 7, which is justified by the same corpus.

**7. `generic_answer` — TF-IDF against the repo's own vocabulary.**
"Is this answer about *this* codebase, or a tutorial?" No neural net needed. Proposed,
never built.

---

## Blocked on another person acting — and items 23 and 24 are what would let them

**9. Calibrate the specification / junior-auditor checks.**
They have only **synthetic** positive controls. Daniel's corpus is the negative control
for the second time — median 1 turn to first edit, essentially zero re-asking — so it
establishes no base rate and no threshold for the population these were built for.
- *Unblocks when:* one other person runs item 23 and sends item 24's file. Not "when real
  junior transcripts exist" — that filing is item 10's, and it sat for a day because the
  passive voice hid the fact that a base rate is a *number* and numbers can be sent
- Until then: do not tune thresholds against Daniel's sessions. That corpus can only show
  the detectors are quiet for an expert, which is the correct behaviour and not evidence
  of anything else.

## Known limitations — accepted and documented, not bugs to fix

- **Blinding is enforced by instruction, not by the sandbox.** `tools: []` was the intent;
  the harness grants *all* tools for an empty list. The judge is `tools: ["Read"]` and is
  told to read only what it is given. Re-test if the harness ever supports an empty grant.
- **The renderer seam has leaked eight times, and now has a mechanism.** Every one was
  computed correctly and lost on the way out; the enumeration is in `HISTORY.md`, and the
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
  read it — item 24's question about the same data.
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

**The API question is settled and is not what holds this back** — no SDK, no framework, no
HTTP, stdlib only, the LLM reached through Claude Code's own subagent mechanism. What that
costs and what items 2 and 11 bought without the dependency is in `HISTORY.md`; the live
half of it is item 23's, since it is why a corpus pass needs new code rather than a runner.

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
  *visible*, and build that.
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
