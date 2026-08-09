# Roadmap

State as of 2026-08-09. Published; see "Done" below. Written so a session with no memory of how this got here can
pick it up.

The plugin is **installed and working end-to-end** on this machine: `/check-chat` runs,
the deterministic pass takes ~40ms, the judge dispatches by `subagent_type`, and the
report comes back. 33 tests pass. What follows is what is not done, ordered by whether
it blocks someone other than the author.

Every item says how you would know it is finished. The rule the project is built on
applies to this list too: **a detector that cannot be shown to fire on real transcripts
does not ship**, and one that fires in most sessions is a ranking, not an alarm.

---

## Done

**1. Published to `github.com/dgutson/check-chat`** — public, MIT, 2026-08-09.
Verified from a fresh clone: manifests validate, `bin/checkchat` runs with no install
and no environment variable, 33 tests pass. The plugin is no longer tied to one machine.

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

Still open: nothing validates that quoted evidence *actually appears in the excerpt*.
A judge could quote something plausible that was never said, and neither the validator
nor the reporting step would notice.

---

## Now — silent wrongness, in rough order of how quietly it fails

**3. `compactions` and `truncated` are computed and consumed by nothing.**
`transcript.py` detects both. No check reads either, and the report never mentions them.
Consequences today: a **compacted** session's digest silently spans the compaction
boundary as though it were continuous, and a transcript over 24 MB is silently
tail-truncated with every count computed on the remainder. Both produce confidently
wrong numbers with no warning.
- *Done when:* the summary says so, and the judge is told the excerpt may straddle a gap

**4. `cli_probes` has never fired its cross-session path.**
`probes` counts fine (19 across the corpus) but `recurring` is 0 everywhere, so the
actionable half — and the fork-dedup guard protecting it, which the handoff called
mandatory — has never been observed working. By this project's own rule that is
disqualifying for a shipped detector.
- *Done when:* it fires on a real corpus with the guard demonstrably suppressing a fork,
  or it is cut

**5. No `pyproject.toml`.**
Tests currently borrow `rot-metrics`' venv because system Python has no pytest. Fine for
one machine, hostile to a contributor.
- *Done when:* `pip install -e '.[dev]' && pytest` works from a clean checkout

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

## The API question, for whoever revisits item 2

There is **no SDK, no framework, no API client** anywhere in this plugin — no
`anthropic`, no POML, no PydanticAI, no HTTP at all. Dependencies are stdlib only. The
LLM is reached through Claude Code's own subagent mechanism, which is why the plugin
only works inside Claude Code and could not run over transcripts in CI without new code.

That is the right trade for now, but it is exactly why item 2 is open: prompt-instructed
JSON has no validator and no retry behind it.

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
