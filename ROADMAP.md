# Roadmap

> Pending work only — finished items move to HISTORY.md.
> This is the durable record of what's outstanding. Read it instead of reconstructing
> the state of play from git history, old conversations, or a sweep of the code.
> Next thing to work on: the first item under the earliest horizon whose **Blocked-by**
> entries are no longer present in this file.

Format: 1
Next ID: R-006

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
as are R-001 and R-002.

**Nothing here is startable by the author.** R-003 waits on a person, and the two items
behind it wait on R-003. That is the honest state rather than an empty file: the work left
in this project needs a corpus that is not Daniel's. If that wait is to be shortened, it is
shortened by asking someone, which is not a task this file can hold. Candidates for
promotion, if the wait proves long, are in `HISTORY.md`'s known-limitations register — the
`__main__`-held needle, the world-readable `${TMPDIR:-/tmp}` excerpt, and `partial_use`'s
quoted-filename miss are all accepted costs today and would be real items if that changed.

---

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
