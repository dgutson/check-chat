# Roadmap

> Pending work only — finished items move to HISTORY.md.
> This is the durable record of what's outstanding. Read it instead of reconstructing
> the state of play from git history, old conversations, or a sweep of the code.
> Next thing to work on: the first item under the earliest horizon whose **Blocked-by**
> entries are no longer present in this file.

Format: 1
Next ID: R-012

The rest of what this file used to carry now lives in `HISTORY.md`: the index of shipped
items, the known limitations, the ideas measured to nothing, and the ways a corpus
measurement comes back false. Read those when you are about to change a decision or take a
number; read this one to pick a task. The rule the project is built on governs both:
**a detector that cannot be shown to fire on real transcripts does not ship**, and
**a test is not evidence until the invariant it guards has been broken on purpose and the
test has been watched to fail.**

Items were renumbered when this file adopted the `R-` scheme. `HISTORY.md`, docstrings and
commit messages refer to the old bare numbers, so: R-003 was 9, R-004 was 6, R-005 was 7.
Items 1–5 and 10–27 are shipped and retired to `HISTORY.md` under their original numbers,
as are R-001, R-002 and R-006.

**No check that needs *calibrating* is startable by the author.** R-003 waits on a person,
and the two items behind it wait on R-003: tuning a detector needs a corpus that is not
Daniel's, and that wait is shortened by asking someone, which is not a task this file can
hold. What is startable is everything that is not a threshold — R-009 is a semantics
decision about what counts as a turn and R-011 is one about the judge's own settings, both
measured on this machine because a parser reading the wire format wrong is wrong on
anybody's transcripts; R-010 is which *tree* a number came from, which has to be settled
before a stored number means anything; and R-007 and R-008 are about the store the
measurements land in. Further candidates for promotion, if the
wait proves long, are in `HISTORY.md`'s known-limitations register — the `__main__`-held
needle, the world-readable `${TMPDIR:-/tmp}` excerpt, and `partial_use`'s quoted-filename
miss are all accepted costs today and would be real items if that changed.

The store is `HISTORY.md` and stays there. R-007 and R-008 were filed after a review that
asked whether it should be MLflow, dvc or SQLite and concluded no: the four registers are
epistemics, not metrics. Every row in "do not rebuild these" is a number plus the reason the
number does not mean what it looks like — "right about the number and wrong about the
cause", "the base rate is real but the interpretation inverts" — and a metrics store keeps
the 0-of-51 and drops the clause that is the entire content. These are about reaching the
prose and about what a stored number was taken against; neither relocates anything.

---

## Now

### R-010 — A report must name the tree that produced it

- **Category:** Measurement
- **What:** No output of this tool says which tree produced it, and the machine gives two different answers about what is installed. `claude plugin list` reads `installed_plugins.json`, which names a cache snapshot at `~/.claude/plugins/cache/check-chat-marketplace/check-chat/0.2.0` from 08-14 and reports `0.2.0`; `claude plugin details` reads the manifest and reports `0.3.0`; and the harness puts `/home/daniel/src/check-chat/bin` — the **checkout**, not the cache — on `PATH`, which is the tree that actually executes. So the snapshot is inert bookkeeping and the running tool is whatever is checked out at that moment, including uncommitted edits. Fix it where a reader can see it: the tool reports the directory its own package was imported from, and identifies the tree within it. Provenance from the filesystem, not from git — the package must stay installable standalone, so `__file__`'s resolved root is the fact and a `.git` alongside it is a hint, never a requirement.
- **Why:** The rule is **measure the shipping function, never a model of it**, and the gap it now has to cover is *which* function. A volunteer's calibration file is the sharp case: they clone and run `bin/checkchat`, so their file comes from an arbitrary commit, and `version` — which 0.3.0 does carry — is far too coarse to separate two clones a week apart. It costs a wrong claim to learn this: the first filing of this item asserted the *cache copy* was executing and that R-002's `--census` had never run, which the `PATH` entry and `plugin details` both refute. That error is the item's own evidence — three plausible sources of truth for "what is installed" disagreed, and the one that governs was the one nobody had checked. This is also the honest reading of R-008's provenance: a commit SHA beside an aggregate is worth little when the tree it came from carried uncommitted edits.
- **Outcome:** every report, every `--emit` and every calibration file names the tree it ran from precisely enough to tell two clones apart, the two install answers are reconciled or the useless one is documented as bookkeeping, and the dev loop is written down where a contributor will find it.
- **Blocked-by:** —
- **Enables:** R-008

### R-009 — Decide whether a bare `/skill` invocation is a turn

- **Category:** Checks
- **What:** Trap 8 unwrapped `<command-args>`, so a brief typed after a slash command is a turn again. It left the case where the args are **empty**: the human typed `/handoff:handoff` and nothing else, `clean()` returns `""`, and `load` records no turn — so `__main__` refuses the session with "assistant responses but no human turn". Measured on 684 transcripts after the fix: 19 sessions still refused for exactly this, and the real `syslog-doctor:diagnose` session is one of them, its only human record a bare invocation. Decide it, and the decision is a discriminator, not a switch: keeping `<command-name>` for the whole family adds 195 turns of which **82 are `/effort` (36), `/model` (20), `/reload-plugins` (12), `/plugin` (11) and `/compact` (3)** — harness controls that ask nothing. `:` namespacing separates plugin skills from builtins imperfectly, since `/init` and `/compact` are builtins that do real work and a local unnamespaced skill would be missed. Whatever lands, the `--census` declaration for `system/local_command` and the `queue-operation` prose both name this behaviour and move with it.
- **Why:** A turn with no ask is a defect in **every per-turn check at once** — that is traps 5, 6 and 7's shared lesson, and `/effort` records are that shape exactly: one short answer, no calls, nothing requested. So the cheap fix is the one that reintroduces the phantom by the door trap 8 opened, and the refusal is at least legible. But the refusal is also wrong about a real session: a person who types `/syslog-doctor:diagnose` **has** asked for something, and today the tool tells them to go take a turn first. Both readings are defensible, which is why this is an item and not a patch.
- **Outcome:** either a bare invocation is a turn carrying the command as its ask and 0 of 684 sessions are refused for want of a turn, or it is documented in HISTORY.md's known-limitations register as an accepted cost with the 19 counted — and in both cases the `/effort`-shaped records stay out, shown by a test watched to fail on the over-reaching variant.
- **Blocked-by:** —
- **Enables:** —

### R-011 — Pin the judge's dispatch settings, and decide what they should be

- **Category:** Checks
- **What:** `agents/check-chat-judge.md` has declared `model: sonnet`, `effort: high` since 306b143 and no rationale for either exists in this repo. Two halves. First, a test asserting the frontmatter still names both — the declaration is one line from silently becoming "inherit from the caller", and the caller is by construction a session suspected of being degraded. Second, decide the values against the measurement that is now on record: 9 dispatches on this machine, every one `sonnet-5 / high`, with callers at medium, high, xhigh and max — so in the ordinary case the judge is a **weaker** reader than the session it is grading. Note for whoever does it: subagent traffic lives in `~/.claude/projects/<dir>/<session-id>/subagents/agent-*.jsonl`, one file per dispatch, carrying `effort` per response — a location this project's own loader never reads, since `load` drops `isSidechain`, so the sweep needs its own reader and will not come from `transcript.load`.
- **Why:** The judge exists because a degraded session cannot grade itself, so its independence is the product and its settings are part of that independence, not configuration. That inheritance is the default is not assumed — it is measured: the one dispatch of this role that ran at `max` was a pre-release hand-rolled one, the judge's instructions pasted into a default agent, and it took the caller's effort exactly as the frontmatter now prevents. Deciding the values is the other half and must not be settled by asserting a preference: an opus judge and a sonnet judge on the *same* excerpt is a cheap experiment, and this project's rule is that a change is measured rather than assumed. Note what the test can and cannot buy — it guards the **declaration**; only the wire shows the harness honouring it, which is why the corpus reader above is in scope rather than a nice-to-have.
- **Outcome:** the pin cannot be dropped without a test failing, HISTORY.md carries why the model and the effort are what they are, and if either changes it changes on evidence from the same excerpt judged both ways.
- **Blocked-by:** —
- **Enables:** —

### R-007 — Put the four registers above the item log in HISTORY.md

- **Category:** The project record
- **What:** Move the four registers — known limitations, do-not-rebuild, measuring against the corpus, how the defects have sorted — from lines 1493–1806 to directly under the index table, above `## Shipped items`. Change CLAUDE.md's filing rule with them: it says append a finished entry "to the end of HISTORY.md's Shipped items", which is about to stop meaning the end of the file. Then add the row that keeps it — a test asserting the four register headings precede `## Shipped items`, for the same reason the roadmap's budget is a test and not a note. Do **not** split them into their own file: they cross-reference the item entries throughout, and a register living outside the file the append rule names is a register that goes stale.
- **Why:** CLAUDE.md tells the reader "reading the relevant one is cheaper than rediscovering it", which assumes they can find it. All four are read-*before*-acting and the item log is read-after, yet the index table at line 24 indexes only the items; the header names the registers without pointing at them, so the pointer costs a scroll past 1,440 lines of settled history — the cost that split this file out of the roadmap in the first place. The append rule is the part a hand reorder decays without: every section now sitting between the log and the registers arrived by being appended at the end, which is how the registers ended up underneath it.
- **Outcome:** the consult-first material is the first thing below the index, the filing rule names the section it appends to rather than "the end", and a test fails if the order inverts again.
- **Blocked-by:** —
- **Enables:** —

### R-008 — Persist the sweep aggregate with what it was taken against

- **Category:** Measurement
- **What:** `--sweep` appends its aggregate to `measurements/sweep.jsonl`, one row per run, wrapped in the provenance the aggregate cannot carry itself: commit and wall-clock time. Nothing else — session count, corpus size, `limit` and `siblings` are already in `run()`'s output, and copying them beside it would be the second copy this module exists to refuse. The wrapper is a wrapper and not two new keys inside the aggregate, because a test walks `sweep.run()` default-deny against `sendable_strings()`: a commit SHA is not a registry constant, and the fix for that failure is not to widen the vocabulary. JSONL, not CSV, for the same no-second-copy reason — `run()` summarises every numeric field a check happens to carry, so a column set would be the registry again. The file is committed, which is the point: item 24 declared this aggregate sendable and this is that declaration being used.
- **Why:** Two hand-rolled sweeps "returned a plausible wrong number on the first run and were believed" — 28 of 37 where the truth was 6 of 48, 0 of 196 where the shipping function showed 24 — and the rule that came out of it is **call the checks, never model them**. A number that has to be re-derived from memory before it can be cited again is being modelled. What this does *not* buy is a before/after diff, and the item is scoped to say so: the corpus contains the measuring session and grows between runs (R-001 saw `batching` 49→50 and `responses_with_tools` median 35→37 from a change that only removes turns, all of it the live session), and that register's conclusion was **diff per session, not per aggregate**. A stored aggregate row would have named the corpus size, but it still cannot say which member moved; R-006 is the other half, where an unmoved aggregate was not evidence the change was inert. So prose stays primary and the JSONL is what prose points at. The per-session rows that *would* settle an R-001 stay a live `observe` run and out of the committed file, because a per-session row is contentless but not anonymous at n=1.
- **Outcome:** a sweep number quoted in prose or a docstring can be re-fetched with the commit and the corpus it was taken against, instead of re-run against a corpus that has changed underneath it — and the row says what it cannot answer.
- **Blocked-by:** R-010 — a row stamped with a commit but not with the tree it ran in is the provenance bug this item exists to close, written down in a committed file.
- **Enables:** —

## Next

### R-003 — Calibrate the specification / junior-auditor checks

- **Category:** Calibration
- **What:** Get `checkchat --calibrate` run by at least one person who is not the author, and merge the returned file. This waits on a person, not on code: the corpus pass (`--sweep`), the declared-safe aggregate, the public ask and the single command a volunteer runs are all shipped. Treat the first returned file as a test of the file itself — if the boxes come back mostly `?`, the rows were not judgeable cold and the fix is the row, not the volunteer.
- **Why:** The `specification` and junior-auditor checks have only **synthetic** positive controls. Daniel's corpus is their negative control for the second time — median 1 turn to first edit, essentially zero re-asking — so it establishes no base rate and no threshold for the population these checks were built for. Until a marked file comes back, thresholds must not be tuned against the author's sessions: that corpus can only show the detectors are quiet for an expert, which is correct behaviour and evidence of nothing else. Not "when real junior transcripts exist" — that filing was item 10's mistake, and a blocker that names an artifact is a task rather than a wait.
- **Outcome:** At least one marked calibration file from a non-author is merged, giving these checks a base rate and a threshold drawn from the population they target — or, if the rows prove unjudgeable cold, a rewritten row set and a second ask.
- **Blocked-by:** —
- **Enables:** R-004, R-005

## Later

### R-004 — `re_ask`: semantic near-duplicate detection

- **Category:** Checks
- **What:** Detect the junior-developer loop — vague question, generic answer, the same question reworded. Ship the encoder as an *optional* accelerator: `fastembed` (ONNX, ~50 MB) when importable, char-n-gram fallback otherwise, with the output saying which ran. Report both scorers' numbers and their agreement on a corpus that does re-ask, and take the dependency only if the encoder beats the fallback.
- **Why:** Re-asking is signal and free label at once — if the user rephrases, the previous answer demonstrably failed. That self-carrying ground truth is what makes `partial_use` the headline finding, and nothing else in the specification dimension has it. It is also the one place an encoder earns a dependency, since char-n-gram similarity scores "how do I fix this?" against "what's wrong with my code?" near zero while a sentence encoder does not. Both scorers are zero on the author's corpus, and that zero is *not* item 4's: a re-ask is only a re-ask within one conversation, so one session is the right population by construction and no re-scoping would change the number. The wrong user, not the wrong query.
- **Outcome:** `re_ask` ships measured against a corpus that re-asks, stdlib-only installs still work, and the report names the scorer that produced the number.
- **Blocked-by:** R-003
- **Enables:** —

### R-005 — `generic_answer`: TF-IDF against the repo's own vocabulary

- **Category:** Checks
- **What:** Score an answer for whether it is about *this* codebase or is a tutorial, by TF-IDF against the repository's own vocabulary. No neural dependency required.
- **Why:** Proposed and never built. It is the other half of the specification dimension and is blocked by the same thing as `re_ask` — the author's corpus cannot show it firing, so there is nothing to set it against.
- **Outcome:** `generic_answer` ships with a threshold set from a corpus that contains generic answers, and its evidence tier states what the score can and cannot claim.
- **Blocked-by:** R-003
- **Enables:** —
