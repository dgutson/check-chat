# check-chat

A Claude Code plugin that diagnoses the conversation it is running inside. Stdlib only, no
SDK and no HTTP; the LLM is reached through Claude Code's own subagent mechanism.

Tests run in the project's **own** virtualenv, from the repo root: `.venv/bin/pytest`
(152 tests). Do not run them against the system Python.

## Roadmap

This repo is governed by ROADMAP.md (pending work) and HISTORY.md (completed work).

- **Start here for context.** ROADMAP.md is the durable record of work that is established
  but unfinished. Read it rather than reconstructing the state of play from git history,
  old conversations, or a sweep of the code.
- Items are grouped **Now / Next / Later**. To choose what to work on, take the first item
  under the earliest horizon whose **Blocked-by** entries are no longer present in the file.
- When you finish an item: delete it from ROADMAP.md, append its entry to the end of
  HISTORY.md's "Shipped items" (this repo files them in the order they were finished, not
  newest-first) with the outcome **actually** achieved and what the filing got wrong, add its
  one-line row to HISTORY.md's index table, and drop its ID from the **Blocked-by** list of
  every item it was blocking.
- When **Now** empties, promote the readiest items from **Next**, so the file keeps
  answering "what should I be doing" rather than going quiet.
- ROADMAP.md holds pending work only. Never mark an item done in place — removal is what
  "done" means here. A test enforces the roadmap's size budget; the fix when it fails is to
  retire an item, never to write the next entry shorter than its evidence deserves.
- Item IDs are `R-001`, `R-002`, … never reused. HISTORY.md, docstrings and commit messages
  from before the `R-` scheme refer to items by bare number (item 9, item 26); those numbers
  are not reused either.

## What HISTORY.md holds besides finished items

Four registers, and reading the relevant one is cheaper than rediscovering it:

- **Known limitations** — accepted and documented, not bugs to fix. Check here before
  "fixing" something that was decided.
- **Do not rebuild these** — ideas measured to nothing, each with its measurement. Every one
  looks plausible, which is why the list exists.
- **Measuring against the corpus** — the ways a corpus measurement comes back false. Read it
  before writing a sweep; each entry cost a full re-run to discover.
- **How the defects have sorted** — the four kinds this project produces, which is what
  predicts the next one.

## The rules the project is built on

- **A detector that cannot be shown to fire on real transcripts does not ship**, and one that
  fires in most sessions is a ranking, not an alarm.
- **A test is not evidence until the invariant it guards has been broken on purpose and the
  test has been watched to fail.** A mutation that errors, or that changes nothing, is not a
  test that passed.
- **Nothing a producer computes is rendered by default.** The renderer seam has leaked eight
  times; when you add a field, name the renderer a person reads it in.
- **Measure the shipping function, never a model of it.** If a sweep cannot import the
  function it is estimating, that is the finding.
- **Before believing a zero**, state what population would have to contain the signal and
  check that is what was searched.
- **Do not tune thresholds against the author's corpus.** It is a negative control; see
  R-003 in ROADMAP.md.
